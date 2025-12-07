"""Add visitor assignment rule, history tables and staff description/name fields.

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_assignment_rule"
down_revision: Union[str, None] = "0005_add_permissions_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add visitor_assignment_rules, visitor_assignment_history tables and staff.description/name columns."""
    
    # Add name column to api_staff table
    op.add_column(
        "api_staff",
        sa.Column(
            "name",
            sa.String(100),
            nullable=True,
            comment="Staff real name",
        ),
    )
    
    # Add description column to api_staff table
    op.add_column(
        "api_staff",
        sa.Column(
            "description",
            sa.String(500),
            nullable=True,
            comment="Staff description for LLM assignment prompts",
        ),
    )
    
    # Create visitor_assignment_rules table
    op.create_table(
        "api_visitor_assignment_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            comment="Associated project ID (one rule per project)",
        ),
        sa.Column(
            "ai_provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_ai_providers.id", ondelete="SET NULL"),
            nullable=True,
            comment="AI provider to use for assignment analysis",
        ),
        sa.Column(
            "model",
            sa.String(100),
            nullable=True,
            comment="Specific model to use. If null, uses provider's default",
        ),
        sa.Column(
            "prompt",
            sa.Text,
            nullable=True,
            comment="Custom prompt for assignment analysis. If null, uses system default",
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean,
            nullable=False,
            default=True,
            comment="Whether LLM-based assignment is enabled for this project",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            comment="Creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            comment="Last update timestamp",
        ),
    )
    
    # Create index on project_id for faster lookups
    op.create_index(
        "ix_api_visitor_assignment_rules_project_id",
        "api_visitor_assignment_rules",
        ["project_id"],
        unique=True,
    )
    
    # Create index on ai_provider_id
    op.create_index(
        "ix_api_visitor_assignment_rules_ai_provider_id",
        "api_visitor_assignment_rules",
        ["ai_provider_id"],
    )
    
    # Create visitor_assignment_history table
    op.create_table(
        "api_visitor_assignment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_projects.id", ondelete="CASCADE"),
            nullable=False,
            comment="Associated project ID",
        ),
        sa.Column(
            "visitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_visitors.id", ondelete="CASCADE"),
            nullable=False,
            comment="Visitor being assigned",
        ),
        sa.Column(
            "assigned_staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_staff.id", ondelete="SET NULL"),
            nullable=True,
            comment="Staff member assigned to handle the visitor",
        ),
        sa.Column(
            "previous_staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_staff.id", ondelete="SET NULL"),
            nullable=True,
            comment="Previous staff member (for transfers)",
        ),
        sa.Column(
            "assigned_by_staff_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_staff.id", ondelete="SET NULL"),
            nullable=True,
            comment="Staff who initiated the assignment (for manual assignments)",
        ),
        sa.Column(
            "assignment_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_visitor_assignment_rules.id", ondelete="SET NULL"),
            nullable=True,
            comment="Assignment rule used (for LLM assignments)",
        ),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            default="llm",
            comment="Source of assignment: llm, manual, rule, transfer",
        ),
        sa.Column(
            "model_used",
            sa.String(100),
            nullable=True,
            comment="LLM model used for this assignment",
        ),
        sa.Column(
            "prompt_used",
            sa.Text,
            nullable=True,
            comment="Prompt sent to LLM",
        ),
        sa.Column(
            "llm_response",
            sa.Text,
            nullable=True,
            comment="Full LLM response",
        ),
        sa.Column(
            "reasoning",
            sa.Text,
            nullable=True,
            comment="LLM reasoning for the assignment decision",
        ),
        sa.Column(
            "visitor_message",
            sa.Text,
            nullable=True,
            comment="Visitor's message/question at assignment time",
        ),
        sa.Column(
            "visitor_context",
            postgresql.JSONB,
            nullable=True,
            comment="Additional visitor context (intent, sentiment, etc.)",
        ),
        sa.Column(
            "candidate_staff_ids",
            postgresql.JSONB,
            nullable=True,
            comment="List of staff IDs considered for assignment",
        ),
        sa.Column(
            "candidate_scores",
            postgresql.JSONB,
            nullable=True,
            comment="Scores/rankings for each candidate",
        ),
        sa.Column(
            "response_time_ms",
            sa.Integer,
            nullable=True,
            comment="LLM response time in milliseconds",
        ),
        sa.Column(
            "token_usage",
            postgresql.JSONB,
            nullable=True,
            comment="Token usage statistics",
        ),
        sa.Column(
            "notes",
            sa.Text,
            nullable=True,
            comment="Additional notes or comments",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            comment="Assignment timestamp",
        ),
    )
    
    # Create indexes for assignment history
    op.create_index(
        "ix_api_visitor_assignment_history_project_id",
        "api_visitor_assignment_history",
        ["project_id"],
    )
    op.create_index(
        "ix_api_visitor_assignment_history_visitor_id",
        "api_visitor_assignment_history",
        ["visitor_id"],
    )
    op.create_index(
        "ix_api_visitor_assignment_history_assigned_staff_id",
        "api_visitor_assignment_history",
        ["assigned_staff_id"],
    )
    op.create_index(
        "ix_api_visitor_assignment_history_created_at",
        "api_visitor_assignment_history",
        ["created_at"],
    )
    op.create_index(
        "ix_api_visitor_assignment_history_source",
        "api_visitor_assignment_history",
        ["source"],
    )


def downgrade() -> None:
    """Remove visitor_assignment_rules, visitor_assignment_history tables and staff.description/name columns."""
    
    # Drop assignment history indexes
    op.drop_index("ix_api_visitor_assignment_history_source", table_name="api_visitor_assignment_history")
    op.drop_index("ix_api_visitor_assignment_history_created_at", table_name="api_visitor_assignment_history")
    op.drop_index("ix_api_visitor_assignment_history_assigned_staff_id", table_name="api_visitor_assignment_history")
    op.drop_index("ix_api_visitor_assignment_history_visitor_id", table_name="api_visitor_assignment_history")
    op.drop_index("ix_api_visitor_assignment_history_project_id", table_name="api_visitor_assignment_history")
    
    # Drop assignment history table
    op.drop_table("api_visitor_assignment_history")
    
    # Drop assignment rules indexes
    op.drop_index("ix_api_visitor_assignment_rules_ai_provider_id", table_name="api_visitor_assignment_rules")
    op.drop_index("ix_api_visitor_assignment_rules_project_id", table_name="api_visitor_assignment_rules")
    
    # Drop assignment rules table
    op.drop_table("api_visitor_assignment_rules")
    
    # Drop description and name columns from api_staff
    op.drop_column("api_staff", "description")
    op.drop_column("api_staff", "name")
