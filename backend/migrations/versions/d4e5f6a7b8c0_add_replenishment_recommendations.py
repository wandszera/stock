"""add replenishment recommendations

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c0"
down_revision = "c3d4e5f6a7b9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "replenishment_recommendations",
        sa.Column("id", sa.UUID(), nullable=False), sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=False), sa.Column("forecast_quantity", sa.Numeric(14, 2), nullable=False),
        sa.Column("forecast_model", sa.String(80), nullable=False), sa.Column("lead_time_weeks", sa.Integer(), nullable=False),
        sa.Column("minimum_stock", sa.Integer(), nullable=False), sa.Column("current_quantity", sa.Integer(), nullable=False),
        sa.Column("baseline_quantity", sa.Integer(), nullable=False), sa.Column("simple_rule_quantity", sa.Integer(), nullable=False),
        sa.Column("recommended_quantity", sa.Integer(), nullable=False), sa.Column("approved_quantity", sa.Integer(), nullable=True),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False), sa.Column("planned_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("budget_limit", sa.Numeric(14, 2), nullable=True), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("explanation", sa.String(700), nullable=False), sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("decided_by", sa.UUID(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]), sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_replenishment_recommendations_store_id", "replenishment_recommendations", ["store_id"])
    op.create_index("ix_replenishment_recommendations_variant_id", "replenishment_recommendations", ["variant_id"])
    op.create_index("ix_replenishment_recommendations_created_at", "replenishment_recommendations", ["created_at"])


def downgrade():
    op.drop_table("replenishment_recommendations")
