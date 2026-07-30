"""add upload and AI usage entitlements

Revision ID: c4a2f7e9d1b3
Revises: a8d3f4c9b2e1
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c4a2f7e9d1b3"
down_revision: Union[str, None] = "a8d3f4c9b2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        added_usage_column = "free_uploads_used" not in user_columns
        if "free_upload_limit" not in user_columns:
            op.add_column(
                "users",
                sa.Column("free_upload_limit", sa.Integer(), server_default="2", nullable=False),
            )
        if added_usage_column:
            op.add_column(
                "users",
                sa.Column("free_uploads_used", sa.Integer(), server_default="0", nullable=False),
            )
        if added_usage_column and "v2_documents" in tables:
            op.execute(
                """
                UPDATE users
                SET free_uploads_used = LEAST(
                    free_upload_limit,
                    (SELECT COUNT(*) FROM v2_documents WHERE v2_documents.user_id = users.id)
                )
                """
            )

    if "ai_usage_periods" not in tables:
        op.create_table(
            "ai_usage_periods",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("period_key", sa.String(length=80), nullable=False),
            sa.Column("period_start", sa.DateTime(), nullable=False),
            sa.Column("period_end", sa.DateTime(), nullable=True),
            sa.Column("messages_used", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "period_key", name="uq_ai_usage_user_period"),
        )
        op.create_index("ix_ai_usage_periods_id", "ai_usage_periods", ["id"], unique=False)
        op.create_index("ix_ai_usage_periods_user_id", "ai_usage_periods", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "ai_usage_periods" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("ai_usage_periods")}
        if "ix_ai_usage_periods_user_id" in indexes:
            op.drop_index("ix_ai_usage_periods_user_id", table_name="ai_usage_periods")
        if "ix_ai_usage_periods_id" in indexes:
            op.drop_index("ix_ai_usage_periods_id", table_name="ai_usage_periods")
        op.drop_table("ai_usage_periods")

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "free_uploads_used" in user_columns:
            op.drop_column("users", "free_uploads_used")
        if "free_upload_limit" in user_columns:
            op.drop_column("users", "free_upload_limit")
