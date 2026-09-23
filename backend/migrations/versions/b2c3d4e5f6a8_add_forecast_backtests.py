"""add forecast backtests

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "forecast_backtest_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("minimum_train_periods", sa.Integer(), nullable=False),
        sa.Column("winner_model", sa.String(length=80), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_backtest_runs_store_id", "forecast_backtest_runs", ["store_id"])
    op.create_index("ix_forecast_backtest_runs_variant_id", "forecast_backtest_runs", ["variant_id"])


def downgrade():
    op.drop_table("forecast_backtest_runs")
