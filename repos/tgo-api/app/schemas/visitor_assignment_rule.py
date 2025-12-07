"""Visitor Assignment Rule schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class VisitorAssignmentRuleBase(BaseSchema):
    """Base schema for visitor assignment rule."""
    
    ai_provider_id: Optional[UUID] = Field(
        None,
        description="AI provider ID for assignment analysis"
    )
    model: Optional[str] = Field(
        None,
        max_length=100,
        description="Specific model to use (e.g., gpt-4, qwen-turbo). If null, uses provider's default"
    )
    prompt: Optional[str] = Field(
        None,
        max_length=1000,
        description="Custom prompt for assignment analysis (max 1000 chars). If null, uses system default"
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether LLM-based assignment is enabled"
    )


class VisitorAssignmentRuleCreate(VisitorAssignmentRuleBase):
    """Schema for creating a visitor assignment rule."""
    pass


class VisitorAssignmentRuleUpdate(BaseSchema):
    """Schema for updating a visitor assignment rule."""
    
    ai_provider_id: Optional[UUID] = Field(
        None,
        description="Updated AI provider ID"
    )
    model: Optional[str] = Field(
        None,
        max_length=100,
        description="Updated model name"
    )
    prompt: Optional[str] = Field(
        None,
        max_length=1000,
        description="Updated prompt for assignment analysis (max 1000 chars)"
    )
    is_enabled: Optional[bool] = Field(
        None,
        description="Updated enabled status"
    )


class VisitorAssignmentRuleResponse(BaseSchema):
    """Schema for visitor assignment rule response."""
    
    id: UUID = Field(..., description="Rule ID")
    project_id: UUID = Field(..., description="Associated project ID")
    ai_provider_id: Optional[UUID] = Field(None, description="AI provider ID")
    model: Optional[str] = Field(None, description="Model name")
    prompt: Optional[str] = Field(None, description="Custom prompt")
    effective_prompt: str = Field(..., description="Effective prompt (custom or default)")
    is_enabled: bool = Field(..., description="Whether enabled")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
