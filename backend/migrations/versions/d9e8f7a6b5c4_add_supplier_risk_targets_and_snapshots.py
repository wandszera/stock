"""add supplier risk targets and snapshots

Revision ID: d9e8f7a6b5c4
Revises: c6d7e8f9a0b1
Create Date: 2026-04-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d9e8f7a6b5c4"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_supplier_risk_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_reference", sa.String(length=160), nullable=False),
        sa.Column("target_hours", sa.Integer(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "supplier_reference", name="uq_supplier_risk_target_store_supplier"),
    )
    op.create_table(
        "inventory_supplier_risk_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_reference", sa.String(length=160), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("target_hours", sa.Integer(), nullable=False),
        sa.Column("open_critical_count", sa.Integer(), nullable=False),
        sa.Column("resolved_estimate_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "supplier_reference", "snapshot_date", name="uq_supplier_risk_snapshot"),
    )


def downgrade() -> None:
    op.drop_table("inventory_supplier_risk_snapshots")
    op.drop_table("inventory_supplier_risk_targets")
