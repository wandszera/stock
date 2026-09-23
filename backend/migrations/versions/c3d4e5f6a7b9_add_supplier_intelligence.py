"""add supplier intelligence

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b9"
down_revision = "b2c3d4e5f6a8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "supplier_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("supplier_reference", sa.String(160), nullable=False),
        sa.Column("document_reference", sa.String(120), nullable=True),
        sa.Column("ordered_at", sa.Date(), nullable=False),
        sa.Column("expected_at", sa.Date(), nullable=False),
        sa.Column("delivered_at", sa.Date(), nullable=False),
        sa.Column("ordered_quantity", sa.Integer(), nullable=False),
        sa.Column("received_quantity", sa.Integer(), nullable=False),
        sa.Column("defective_quantity", sa.Integer(), nullable=False),
        sa.Column("purchase_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_deliveries_store_id", "supplier_deliveries", ["store_id"])
    op.create_index("ix_supplier_deliveries_supplier_reference", "supplier_deliveries", ["supplier_reference"])
    op.create_table(
        "supplier_risk_scores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("supplier_reference", sa.String(160), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.String(500), nullable=False),
        sa.Column("delivery_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_risk_scores_store_id", "supplier_risk_scores", ["store_id"])
    op.create_index("ix_supplier_risk_scores_supplier_reference", "supplier_risk_scores", ["supplier_reference"])
    op.create_index("ix_supplier_risk_scores_created_at", "supplier_risk_scores", ["created_at"])


def downgrade():
    op.drop_table("supplier_risk_scores")
    op.drop_table("supplier_deliveries")
