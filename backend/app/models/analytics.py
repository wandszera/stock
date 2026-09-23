import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ForecastBacktestRun(Base):
    __tablename__ = "forecast_backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="weekly")
    horizon: Mapped[int] = mapped_column(nullable=False)
    minimum_train_periods: Mapped[int] = mapped_column(nullable=False)
    winner_model: Mapped[str] = mapped_column(String(80), nullable=False)
    results: Mapped[list] = mapped_column(JSON, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SupplierDelivery(Base):
    __tablename__ = "supplier_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True
    )
    supplier_reference: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    document_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ordered_at: Mapped[date] = mapped_column(Date, nullable=False)
    expected_at: Mapped[date] = mapped_column(Date, nullable=False)
    delivered_at: Mapped[date] = mapped_column(Date, nullable=False)
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    defective_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SupplierRiskScore(Base):
    __tablename__ = "supplier_risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True
    )
    supplier_reference: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    components: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ReplenishmentRecommendation(Base):
    __tablename__ = "replenishment_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product_variants.id"), nullable=False, index=True)
    forecast_quantity: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    forecast_model: Mapped[str] = mapped_column(String(80), nullable=False)
    lead_time_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    simple_rule_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    planned_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="proposed")
    explanation: Mapped[str] = mapped_column(String(700), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
