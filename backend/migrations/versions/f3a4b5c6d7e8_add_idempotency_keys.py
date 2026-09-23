"""add idempotency keys

Revision ID: f3a4b5c6d7e8
Revises: d9e8f7a6b5c4
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "d9e8f7a6b5c4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sales") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=120), nullable=True))
        batch_op.create_unique_constraint(
            "uq_sale_store_idempotency_key", ["store_id", "idempotency_key"]
        )

    with op.batch_alter_table("inventory_receipts") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=120), nullable=True))
        batch_op.create_unique_constraint(
            "uq_receipt_store_idempotency_key", ["store_id", "idempotency_key"]
        )


def downgrade():
    with op.batch_alter_table("inventory_receipts") as batch_op:
        batch_op.drop_constraint("uq_receipt_store_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")

    with op.batch_alter_table("sales") as batch_op:
        batch_op.drop_constraint("uq_sale_store_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
