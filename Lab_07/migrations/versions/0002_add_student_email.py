"""add email to students (variant 1 migration)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite cannot ALTER a constraint in place; batch mode rebuilds the table with the new definition.
    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("email", sa.String(length=120), nullable=True))
        batch.create_unique_constraint("uq_students_email", ["email"])


def downgrade() -> None:
    with op.batch_alter_table("students") as batch:
        batch.drop_constraint("uq_students_email", type_="unique")
        batch.drop_column("email")
