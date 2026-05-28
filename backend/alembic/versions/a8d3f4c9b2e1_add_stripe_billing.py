"""add stripe billing

Revision ID: a8d3f4c9b2e1
Revises: 70a3882e97c9
Create Date: 2026-05-28 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a8d3f4c9b2e1"
down_revision: Union[str, None] = "70a3882e97c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(table_name: str) -> bool:
        return table_name in inspector.get_table_names()

    def has_column(table_name: str, column_name: str) -> bool:
        return column_name in {col["name"] for col in inspector.get_columns(table_name)}

    def has_index(table_name: str, index_name: str) -> bool:
        return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}

    if has_table("subscriptions"):
        if not has_column("subscriptions", "stripe_customer_id"):
            op.add_column("subscriptions", sa.Column("stripe_customer_id", sa.String(), nullable=True))
        if not has_column("subscriptions", "stripe_subscription_id"):
            op.add_column("subscriptions", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
        if not has_index("subscriptions", "ix_subscriptions_stripe_customer_id"):
            op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"], unique=False)
        if not has_index("subscriptions", "ix_subscriptions_stripe_subscription_id"):
            op.create_index(
                "ix_subscriptions_stripe_subscription_id",
                "subscriptions",
                ["stripe_subscription_id"],
                unique=True,
            )

    if has_table("payments"):
        if not has_column("payments", "stripe_payment_id"):
            op.add_column("payments", sa.Column("stripe_payment_id", sa.String(), nullable=True))
        if not has_column("payments", "stripe_checkout_session_id"):
            op.add_column("payments", sa.Column("stripe_checkout_session_id", sa.String(), nullable=True))
        if not has_column("payments", "stripe_invoice_id"):
            op.add_column("payments", sa.Column("stripe_invoice_id", sa.String(), nullable=True))
        if not has_index("payments", "ix_payments_stripe_payment_id"):
            op.create_index("ix_payments_stripe_payment_id", "payments", ["stripe_payment_id"], unique=True)
        if not has_index("payments", "ix_payments_stripe_checkout_session_id"):
            op.create_index(
                "ix_payments_stripe_checkout_session_id",
                "payments",
                ["stripe_checkout_session_id"],
                unique=True,
            )
        if not has_index("payments", "ix_payments_stripe_invoice_id"):
            op.create_index("ix_payments_stripe_invoice_id", "payments", ["stripe_invoice_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def has_table(table_name: str) -> bool:
        return table_name in inspector.get_table_names()

    def has_column(table_name: str, column_name: str) -> bool:
        return column_name in {col["name"] for col in inspector.get_columns(table_name)}

    def has_index(table_name: str, index_name: str) -> bool:
        return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}

    if has_table("payments"):
        if has_index("payments", "ix_payments_stripe_invoice_id"):
            op.drop_index("ix_payments_stripe_invoice_id", table_name="payments")
        if has_index("payments", "ix_payments_stripe_checkout_session_id"):
            op.drop_index("ix_payments_stripe_checkout_session_id", table_name="payments")
        if has_index("payments", "ix_payments_stripe_payment_id"):
            op.drop_index("ix_payments_stripe_payment_id", table_name="payments")
        if has_column("payments", "stripe_invoice_id"):
            op.drop_column("payments", "stripe_invoice_id")
        if has_column("payments", "stripe_checkout_session_id"):
            op.drop_column("payments", "stripe_checkout_session_id")
        if has_column("payments", "stripe_payment_id"):
            op.drop_column("payments", "stripe_payment_id")

    if has_table("subscriptions"):
        if has_index("subscriptions", "ix_subscriptions_stripe_subscription_id"):
            op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
        if has_index("subscriptions", "ix_subscriptions_stripe_customer_id"):
            op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
        if has_column("subscriptions", "stripe_subscription_id"):
            op.drop_column("subscriptions", "stripe_subscription_id")
        if has_column("subscriptions", "stripe_customer_id"):
            op.drop_column("subscriptions", "stripe_customer_id")
