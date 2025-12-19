"""Chat service for handling chat completion business logic."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models import (
    Platform,
    Visitor,
    VisitorServiceStatus,
    VisitorWaitingQueue,
    VisitorAssignmentRule,
    QueueSource,
    WaitingStatus,
)
import app.services.visitor_service as visitor_service
from app.tasks.process_waiting_queue import trigger_process_entry
from app.services.wukongim_client import wukongim_client
from app.utils.encoding import build_project_staff_channel_id
from app.utils.const import CHANNEL_TYPE_PROJECT_STAFF

logger = get_logger("services.chat")


async def get_or_create_visitor(
    db: Session,
    platform: Platform,
    platform_open_id: str,
    nickname: Optional[str] = None,
) -> Visitor:
    """
    获取或创建访客。
    
    如果访客存在且状态为 CLOSED，自动重置为 NEW。
    
    Args:
        db: 数据库会话
        platform: 平台对象
        platform_open_id: 平台用户ID
        nickname: 昵称（可选）
        
    Returns:
        Visitor: 访客对象
    """
    visitor = (
        db.query(Visitor)
        .filter(
            Visitor.platform_id == platform.id,
            Visitor.platform_open_id == platform_open_id,
            Visitor.deleted_at.is_(None),
        )
        .first()
    )
    
    if not visitor:
        # 创建新访客
        visitor = await visitor_service.create_visitor_with_channel(
            db=db,
            platform=platform,
            platform_open_id=platform_open_id,
            nickname=nickname or platform_open_id,
        )
    else:
        # 重置已关闭的访客状态
        if visitor.service_status == VisitorServiceStatus.CLOSED.value:
            visitor.service_status = VisitorServiceStatus.NEW.value
            visitor.updated_at = datetime.utcnow()
            db.commit()
            logger.debug(f"Reset visitor {visitor.id} status from CLOSED to NEW")
    
    return visitor


class AddToQueueResult:
    """访客加入队列的结果。"""
    
    def __init__(
        self,
        success: bool,
        queue_position: int = 0,
        queue_entry_id: Optional[UUID] = None,
        already_in_queue: bool = False,
        cannot_enter: bool = False,
        current_status: Optional[str] = None,
    ):
        self.success = success
        self.queue_position = queue_position
        self.queue_entry_id = queue_entry_id
        self.already_in_queue = already_in_queue
        self.cannot_enter = cannot_enter
        self.current_status = current_status


async def add_visitor_to_waiting_queue(
    db: Session,
    visitor: Visitor,
    project_id: UUID,
    message: str,
    channel_id: str,
    channel_type: int,
    reason: str = "Redirecting to human service",
    trigger_processing: bool = True,
) -> AddToQueueResult:
    """
    将访客加入等待队列。
    
    Args:
        db: 数据库会话
        visitor: 访客对象
        project_id: 项目ID
        message: 访客消息
        channel_id: 频道ID
        channel_type: 频道类型
        reason: 入队原因
        trigger_processing: 是否触发队列处理
        
    Returns:
        AddToQueueResult: 入队结果
    """
    # 检查访客是否可以入队
    if not visitor.is_unassigned:
        return AddToQueueResult(
            success=False,
            cannot_enter=True,
            current_status=visitor.service_status,
        )
    
    # 检查是否已在队列中
    existing_queue = db.query(VisitorWaitingQueue).filter(
        VisitorWaitingQueue.visitor_id == visitor.id,
        VisitorWaitingQueue.project_id == project_id,
        VisitorWaitingQueue.status == WaitingStatus.WAITING.value,
    ).first()
    
    if existing_queue:
        return AddToQueueResult(
            success=True,
            queue_position=existing_queue.position,
            queue_entry_id=existing_queue.id,
            already_in_queue=True,
        )
    
    # 计算队列位置
    current_queue_count = db.query(VisitorWaitingQueue).filter(
        VisitorWaitingQueue.project_id == project_id,
        VisitorWaitingQueue.status == WaitingStatus.WAITING.value,
    ).count()
    queue_position = current_queue_count + 1
    
    # 获取项目的分配规则以确定超时时间
    assignment_rule = db.query(VisitorAssignmentRule).filter(
        VisitorAssignmentRule.project_id == project_id,
    ).first()
    
    timeout_minutes = settings.QUEUE_DEFAULT_TIMEOUT_MINUTES
    if assignment_rule and assignment_rule.queue_wait_timeout_minutes:
        timeout_minutes = assignment_rule.queue_wait_timeout_minutes
    expired_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
    
    # 创建队列条目
    queue_entry = VisitorWaitingQueue(
        project_id=project_id,
        visitor_id=visitor.id,
        source=QueueSource.SYSTEM.value,
        urgency="normal",
        priority=1,
        position=queue_position,
        status=WaitingStatus.WAITING.value,
        visitor_message=message,
        reason=reason,
        channel_id=channel_id,
        channel_type=channel_type,
        expired_at=expired_at,
    )
    db.add(queue_entry)
    
    # 更新访客状态
    visitor.set_status_queued()
    
    db.commit()
    db.refresh(queue_entry)
    
    logger.info(
        f"Added visitor {visitor.id} to waiting queue at position {queue_position}",
        extra={
            "visitor_id": str(visitor.id),
            "queue_entry_id": str(queue_entry.id),
            "position": queue_position,
        }
    )
    
    # 发送队列更新事件到项目坐席频道
    try:
        staff_channel_id = build_project_staff_channel_id(project_id)
        await wukongim_client.send_queue_updated_event(
            channel_id=staff_channel_id,
            channel_type=CHANNEL_TYPE_PROJECT_STAFF,
            project_id=str(project_id),
            waiting_count=queue_position,
        )
    except Exception as e:
        logger.error(f"Failed to send queue updated event: {e}")
        # Don't fail the operation if event sending fails
    
    # 触发队列处理
    if trigger_processing:
        await trigger_process_entry(queue_entry.id)
    
    return AddToQueueResult(
        success=True,
        queue_position=queue_position,
        queue_entry_id=queue_entry.id,
        already_in_queue=False,
    )
