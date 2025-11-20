"""
Tool model for the MCP Tool Marketplace.

This module defines the Tool model which represents both MCP server tools
and custom webhook tools in the unified tools table.
"""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship



from .base import BaseModel
from .enums import (
    CustomExecutionType, ToolSourceType, ToolStatus,
    WebhookAuthType, WebhookMethod, TransportType
)


class Tool(BaseModel):
    """
    Tool model representing both MCP server tools and custom webhook tools.
    
    This unified model supports tools from two sources:
    1. MCP server tools - discovered from registered MCP servers
    2. Custom tools - webhook-based tools created by project owners
    """
    
    __tablename__ = "tools"
    
    # Source identification
    tool_source_type: Mapped[ToolSourceType] = mapped_column(
        nullable=False,
        default=ToolSourceType.MCP_SERVER,
        index=True,
        doc="Source type of the tool"
    )
    
    # MCP server connection info (denormalized)
    mcp_transport_type: Mapped[Optional[TransportType]] = mapped_column(
        nullable=True,
        doc="Transport type for MCP server tools"
    )

    mcp_endpoint: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="Endpoint URL for MCP server tools"
    )
    
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
        doc="Project ID (for custom tools)"
    )

    # Basic tool information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Tool name"
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable display name for the tool (falls back to name if not set)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Tool description"
    )
    
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
        doc="Tool version"
    )
    
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Tool category"
    )
    
    tags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        doc="Tool tags for categorization"
    )
    
    status: Mapped[ToolStatus] = mapped_column(
        nullable=False,
        default=ToolStatus.ACTIVE,
        index=True,
        doc="Current tool status"
    )
    
    # Input/Output Schema
    input_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="JSON Schema defining tool input parameters"
    )
    
    output_schema: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="JSON Schema defining tool output format"
    )
    
    # Custom tool specific fields (webhook execution)
    execution_type: Mapped[Optional[CustomExecutionType]] = mapped_column(
        nullable=True,
        doc="Execution method for custom tools (webhook only)"
    )
    
    webhook_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="HTTP endpoint URL for webhook-based custom tools"
    )
    
    webhook_method: Mapped[Optional[WebhookMethod]] = mapped_column(
        nullable=True,
        default=WebhookMethod.POST,
        doc="HTTP method for webhook calls"
    )
    
    webhook_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="HTTP headers to include in webhook requests"
    )
    
    webhook_auth_type: Mapped[Optional[WebhookAuthType]] = mapped_column(
        nullable=True,
        doc="Authentication type for webhook requests"
    )
    
    webhook_auth_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Authentication configuration for webhook requests"
    )
    
    # Execution configuration
    timeout_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30000,
        doc="Execution timeout in milliseconds"
    )
    
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        doc="Maximum number of retry attempts"
    )
    
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        doc="Rate limit per minute"
    )
    
    # Validation and constraints
    max_input_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1048576,  # 1MB
        doc="Maximum input size in bytes"
    )
    
    allowed_domains: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        doc="Allowed domains for webhook tools"
    )
    
    # Sharing and visibility
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether custom tool can be shared across projects"
    )
    
    # Metadata
    meta_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Additional tool metadata"
    )
    
    # Relationships

    
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="tools",
        primaryjoin="Tool.project_id == Project.id",
        foreign_keys=[project_id],
        doc="Project that owns this custom tool (no DB-level FK)"
    )

    project_tools: Mapped[List["ProjectTool"]] = relationship(
        "ProjectTool",
        back_populates="tool",
        cascade="all, delete-orphan",
        doc="Project installations of this tool"
    )
    
    tool_executions: Mapped[List["ToolExecution"]] = relationship(
        "ToolExecution",
        back_populates="tool",
        cascade="all, delete-orphan",
        doc="Executions of this tool"
    )
    
    # Table constraints
    __table_args__ = (
        # Source consistency constraints
        CheckConstraint(
            """
            (tool_source_type = 'MCP_SERVER' AND mcp_transport_type IS NOT NULL AND mcp_endpoint IS NOT NULL
             AND project_id IS NULL AND execution_type IS NULL) OR
            (tool_source_type = 'CUSTOM' AND mcp_transport_type IS NULL AND mcp_endpoint IS NULL
             AND project_id IS NOT NULL AND execution_type IS NOT NULL)
            """,
            name="tools_source_consistency"
        ),
        
        # Webhook consistency constraint
        CheckConstraint(
            """
            (execution_type != 'WEBHOOK') OR
            (execution_type = 'WEBHOOK' AND webhook_url IS NOT NULL)
            """,
            name="tools_webhook_consistency"
        ),
        
        # Validation constraints
        CheckConstraint("timeout_ms > 0", name="tools_timeout_positive"),
        CheckConstraint("max_retries >= 0", name="tools_max_retries_non_negative"),
        CheckConstraint("rate_limit_per_minute > 0", name="tools_rate_limit_positive"),
        CheckConstraint("max_input_size_bytes > 0", name="tools_max_input_size_positive"),
        
        # Unique constraints

        UniqueConstraint("project_id", "name", "version", name="uq_project_tool_name_version"),
    )
    
    def __repr__(self) -> str:
        """String representation of the tool."""
        return f"Tool(id={self.id}, name='{self.name}', source='{self.tool_source_type}')"
    
    @property
    def is_mcp_server_tool(self) -> bool:
        """Check if this is an MCP server tool."""
        return self.tool_source_type == ToolSourceType.MCP_SERVER
    
    @property
    def is_custom_tool(self) -> bool:
        """Check if this is a custom tool."""
        return self.tool_source_type == ToolSourceType.CUSTOM
    
    @property
    def is_webhook_tool(self) -> bool:
        """Check if this is a webhook-based custom tool."""
        return (self.is_custom_tool and 
                self.execution_type == CustomExecutionType.WEBHOOK)
    
    @property
    def is_active(self) -> bool:
        """Check if the tool is active."""
        return self.status == ToolStatus.ACTIVE

    @property
    def display_title(self) -> str:
        """Get the display title, falling back to name if title is not set."""
        return self.title if self.title and self.title.strip() else self.name

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value."""
        return self.meta_data.get(key, default) if self.meta_data else default

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        if self.meta_data is None:
            self.meta_data = {}
        self.meta_data[key] = value
