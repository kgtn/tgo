"""
Logistics UI Template.

Defines the schema for rendering logistics/shipping information as a rich UI component.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.ui_templates.schema import UITemplate, UITemplateType, ActionButton
from app.ui_templates.registry import UITemplateRegistry


class LogisticsStatus(str, Enum):
    """Logistics status enumeration."""

    PENDING = "pending"  # 待揽收
    PICKED_UP = "picked_up"  # 已揽收
    IN_TRANSIT = "in_transit"  # 运输中
    OUT_FOR_DELIVERY = "out_for_delivery"  # 派送中
    DELIVERED = "delivered"  # 已签收
    EXCEPTION = "exception"  # 异常
    RETURNED = "returned"  # 已退回


class LogisticsEvent(BaseModel):
    """Single logistics tracking event."""

    time: str = Field(..., description="事件时间")
    status: Optional[LogisticsStatus] = Field(default=None, description="状态")
    description: str = Field(..., description="事件描述")
    location: Optional[str] = Field(default=None, description="地点")
    operator: Optional[str] = Field(default=None, description="操作员/快递员")
    phone: Optional[str] = Field(default=None, description="联系电话")


@UITemplateRegistry.register("logistics")
class LogisticsTemplate(UITemplate):
    """
    物流追踪信息模板。

    用于展示物流配送的完整信息，包括快递单号、
    当前状态、配送时间线等。
    """

    type: Literal[UITemplateType.LOGISTICS] = Field(
        default=UITemplateType.LOGISTICS,
        description="模板类型",
    )

    # 物流基本信息
    tracking_number: str = Field(..., description="物流单号")
    carrier: str = Field(..., description="物流公司")
    carrier_logo: Optional[str] = Field(default=None, description="物流公司logo URL")
    carrier_phone: Optional[str] = Field(default=None, description="物流公司客服电话")

    # 当前状态
    status: LogisticsStatus = Field(..., description="当前物流状态")
    status_text: Optional[str] = Field(default=None, description="状态描述文本")

    # 预计送达
    estimated_delivery: Optional[str] = Field(default=None, description="预计送达时间")

    # 收发信息
    sender: Optional[str] = Field(default=None, description="发件人/地址")
    receiver: Optional[str] = Field(default=None, description="收件人")
    receiver_address: Optional[str] = Field(default=None, description="收件地址")
    receiver_phone: Optional[str] = Field(default=None, description="收件人电话")

    # 配送员信息
    courier_name: Optional[str] = Field(default=None, description="配送员姓名")
    courier_phone: Optional[str] = Field(default=None, description="配送员电话")

    # 物流时间线
    timeline: List[LogisticsEvent] = Field(..., description="物流追踪时间线")

    # 关联订单
    order_id: Optional[str] = Field(default=None, description="关联订单号")

    # 操作按钮
    actions: Optional[List[ActionButton]] = Field(
        default=None,
        description="操作按钮",
    )

    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """Get an example logistics template."""
        return {
            "type": "logistics",
            "tracking_number": "SF1234567890123",
            "carrier": "顺丰速运",
            "carrier_phone": "95338",
            "status": "in_transit",
            "status_text": "您的包裹正在运输中",
            "estimated_delivery": "2024-12-05 18:00前",
            "receiver": "张三",
            "receiver_address": "北京市朝阳区xxx街道xxx号",
            "receiver_phone": "138****1234",
            "courier_name": "李师傅",
            "courier_phone": "139****5678",
            "timeline": [
                {
                    "time": "2024-12-04 14:30:00",
                    "status": "in_transit",
                    "description": "快件已到达【北京朝阳转运中心】",
                    "location": "北京市朝阳区",
                },
                {
                    "time": "2024-12-03 20:15:00",
                    "status": "in_transit",
                    "description": "快件已从【上海转运中心】发出，正发往【北京朝阳转运中心】",
                    "location": "上海市",
                },
                {
                    "time": "2024-12-03 10:30:00",
                    "status": "picked_up",
                    "description": "快件已被【上海浦东营业点】揽收",
                    "location": "上海市浦东新区",
                    "operator": "王师傅",
                    "phone": "137****9999",
                },
                {
                    "time": "2024-12-02 18:00:00",
                    "status": "pending",
                    "description": "商家已发货，等待快递揽收",
                },
            ],
            "order_id": "ORD-2024-001234",
            "actions": [
                {
                    "label": "查看详情",
                    "action": "url://https://www.sf-express.com/cn/sc/dynamic_function/waybill/#search/bill-number/SF1234567890123",
                    "style": "primary",
                },
                {
                    "label": "复制单号",
                    "action": "copy://SF1234567890123",
                    "style": "link",
                },
                {
                    "label": "联系客服",
                    "action": "msg://我想咨询物流单号 SF1234567890123 的配送问题",
                    "style": "default",
                },
            ],
        }

    @classmethod
    def get_description(cls) -> str:
        """Get template description."""
        return "物流追踪信息展示，包含物流状态、配送时间线、快递员信息等"


@UITemplateRegistry.register("price_comparison")
class PriceComparisonTemplate(UITemplate):
    """
    价格对比表格模板。

    用于展示多个商品或不同渠道的价格对比信息。
    """

    type: Literal[UITemplateType.PRICE_COMPARISON] = Field(
        default=UITemplateType.PRICE_COMPARISON,
        description="模板类型",
    )

    # 标题
    title: Optional[str] = Field(default=None, description="对比标题")

    # 对比项目
    items: List[Dict[str, Any]] = Field(..., description="对比项目列表")

    # 对比维度
    columns: List[str] = Field(..., description="对比列（如：价格、发货时间等）")

    # 推荐项
    recommended_index: Optional[int] = Field(
        default=None,
        description="推荐项的索引",
    )
    recommendation_reason: Optional[str] = Field(
        default=None,
        description="推荐理由",
    )

    # 操作按钮
    actions: Optional[List[ActionButton]] = Field(
        default=None,
        description="操作按钮",
    )

    @classmethod
    def get_example(cls) -> Dict[str, Any]:
        """Get an example price comparison template."""
        return {
            "type": "price_comparison",
            "title": "iPhone 15 Pro Max 价格对比",
            "columns": ["渠道", "价格", "发货时间", "保障"],
            "items": [
                {
                    "渠道": "官方旗舰店",
                    "价格": "¥9999",
                    "发货时间": "24小时内",
                    "保障": "官方正品",
                },
                {
                    "渠道": "京东自营",
                    "价格": "¥9899",
                    "发货时间": "当日达",
                    "保障": "7天无理由",
                },
                {
                    "渠道": "拼多多百亿补贴",
                    "价格": "¥9599",
                    "发货时间": "2-3天",
                    "保障": "假一赔十",
                },
            ],
            "recommended_index": 1,
            "recommendation_reason": "综合价格和配送速度，京东自营是最佳选择",
            "actions": [
                {
                    "label": "去京东购买",
                    "action": "url://https://item.jd.com/123456.html",
                    "style": "primary",
                },
                {
                    "label": "查看更多渠道",
                    "action": "msg://帮我查看更多购买渠道",
                    "style": "link",
                },
            ],
        }

    @classmethod
    def get_description(cls) -> str:
        """Get template description."""
        return "价格对比表格，展示多渠道或多商品的价格对比"
