"""Visitor Assignment Rule model for LLM-based visitor distribution."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Default system prompt for visitor assignment
DEFAULT_ASSIGNMENT_PROMPT = """你是一个智能客服分配助手。根据访客的问题和需求，分析并选择最合适的客服人员来处理。

请根据以下信息进行分析：
1. 访客的问题内容和意图
2. 各客服人员的专业领域和描述
3. 客服人员当前的在线状态
"""


class VisitorAssignmentRule(Base):
    """Configuration for LLM-based visitor assignment per project.

    This table stores the settings for how visitors should be automatically
    assigned to staff members using LLM analysis.
    """

    __tablename__ = "api_visitor_assignment_rules"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("api_projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="Associated project ID (one rule per project)",
    )
    ai_provider_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("api_ai_providers.id", ondelete="SET NULL"),
        nullable=True,
        comment="AI provider to use for assignment analysis",
    )

    # Configuration fields
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Specific model to use (e.g., gpt-4, qwen-turbo). If null, uses provider's default",
    )
    prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Custom prompt for assignment analysis. If null, uses system default",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether LLM-based assignment is enabled for this project",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        comment="Creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="visitor_assignment_rule",
        lazy="select",
    )
    ai_provider: Mapped[Optional["AIProvider"]] = relationship(
        "AIProvider",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<VisitorAssignmentRule(id={self.id}, project_id={self.project_id}, is_enabled={self.is_enabled})>"

    @property
    def effective_prompt(self) -> str:
        """Return the effective prompt (custom or default)."""
        return self.prompt if self.prompt else DEFAULT_ASSIGNMENT_PROMPT
