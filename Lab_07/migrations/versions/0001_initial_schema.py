"""initial schema: groups and students

Revision ID: 0001
Revises:
Create Date: 2026-09-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("code", name="uq_groups_code"),
    )
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(length=64), nullable=False),
        sa.Column("last_name", sa.String(length=64), nullable=False),
        sa.Column("average_grade", sa.Float(), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.CheckConstraint("average_grade >= 0 AND average_grade <= 100", name="ck_students_grade_range"),
    )
    op.create_index("ix_students_last_name", "students", ["last_name"])
    op.create_index("ix_students_group_id", "students", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_students_group_id", table_name="students")
    op.drop_index("ix_students_last_name", table_name="students")
    op.drop_table("students")
    op.drop_table("groups")
