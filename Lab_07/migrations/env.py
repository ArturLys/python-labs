"""Alembic environment: points the migration context at the ORM metadata and the configured SQLite file."""

from __future__ import annotations

import logging
import os

from alembic import context
from sqlalchemy import create_engine, pool

from student_manager.db.orm import Base

config = context.config
url = os.environ.get("STUDENT_MANAGER_DB_URL") or config.get_main_option("sqlalchemy.url") or ""
target_metadata = Base.metadata
logging.getLogger("alembic").setLevel(logging.INFO)


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it (alembic upgrade head --sql)."""
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
