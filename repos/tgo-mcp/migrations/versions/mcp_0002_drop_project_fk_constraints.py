"""Drop FK constraints from project_id to projects.id on tools, project_tools, tool_executions.

This migration removes database-level foreign keys linking project_id to the
projects table so that project_id may be any UUID without requiring a projects
row to exist. ORM relationships remain via explicit joins in the models.
"""
from __future__ import annotations

from typing import List

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "mcp_0002_drop_fk"
down_revision = "mcp_0001_baseline"
branch_labels = None
depends_on = None


def _drop_fk_to_projects(table: str, column: str = "project_id") -> List[str]:
    """Drop all FK constraints on `table.column` that reference projects.id.

    Returns the list of dropped constraint names (for logging/diagnostics).
    Safe to run if no such constraints exist.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dropped: List[str] = []

    for fk in inspector.get_foreign_keys(table):
        # fk has keys: name, constrained_columns, referred_table, referred_columns, referred_schema, etc.
        if fk.get("referred_table") == "projects" and column in (fk.get("constrained_columns") or []):
            name = fk.get("name")
            if name:
                op.drop_constraint(name, table_name=table, type_="foreignkey")
                dropped.append(name)
    return dropped


def upgrade() -> None:
    # Drop FKs to projects on project_id from known tables
    _drop_fk_to_projects("tools", "project_id")
    _drop_fk_to_projects("project_tools", "project_id")
    _drop_fk_to_projects("tool_executions", "project_id")


def downgrade() -> None:
    # Recreate FKs to projects.id (best-effort) to reverse the upgrade.
    # Names chosen deterministically; may differ from original names.
    op.create_foreign_key(
        "fk_tools_project_id_projects_id",
        source_table="tools",
        referent_table="projects",
        local_cols=["project_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_project_tools_project_id_projects_id",
        source_table="project_tools",
        referent_table="projects",
        local_cols=["project_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_tool_executions_project_id_projects_id",
        source_table="tool_executions",
        referent_table="projects",
        local_cols=["project_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )

