"""
Alembic environment configuration for MCP Tool Marketplace.

This module configures Alembic for database migrations, including
support for async operations and proper model imports.
"""

import asyncio
import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models to ensure they are registered with SQLAlchemy
from mcp_marketplace.models.base import Base
from mcp_marketplace.models import *  # noqa: F401,F403

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Limit autogenerate scope to MCP tables only
_MCP_TABLES = {"projects", "tools", "project_tools", "tool_executions", "mcp_servers"}

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in _MCP_TABLES or name.startswith("mcp_")
    return True


def include_name(name, type_, parent_names):
    if type_ == "table":
        return name in _MCP_TABLES or name.startswith("mcp_")
    return True

# Prune autogenerate ops that try to touch non-MCP tables
try:
    from alembic.operations import ops as _alembic_ops
except Exception:  # pragma: no cover
    _alembic_ops = None


def process_revision_directives(context, revision, directives):
    if not getattr(context.config, "cmd_opts", None):
        return
    if not getattr(context.config.cmd_opts, "autogenerate", False):
        return
    if not directives:
        return
    script = directives[0]
    if not hasattr(script, "upgrade_ops"):
        return
    if _alembic_ops is None:
        return

    def _keep(op):
        try:
            if isinstance(op, _alembic_ops.DropTableOp):
                return op.table_name in _MCP_TABLES or op.table_name.startswith("mcp_")
            if isinstance(op, _alembic_ops.DropIndexOp):
                tname = getattr(op, "table_name", None)
                return not tname or tname in _MCP_TABLES or tname.startswith("mcp_")
        except Exception:
            return True
        return True

    try:
        script.upgrade_ops.ops = [op for op in script.upgrade_ops.ops if _keep(op)]
    except Exception:
        pass


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use environment variable for database URL if available
    url = os.environ.get("DATABASE__URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        version_table="mcp_alembic_version",
        include_object=include_object,
        include_name=include_name,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        version_table="mcp_alembic_version",
        include_object=include_object,
        include_name=include_name,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section, {})

    # Use environment variable for database URL if available
    database_url = os.environ.get("DATABASE__URL")
    if database_url:
        configuration["sqlalchemy.url"] = database_url
    else:
        # Fallback to config file URL and convert to async format if needed
        database_url = configuration.get("sqlalchemy.url", "")
        if database_url.startswith("postgresql://"):
            configuration["sqlalchemy.url"] = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif database_url.startswith("postgres://"):
            configuration["sqlalchemy.url"] = database_url.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
