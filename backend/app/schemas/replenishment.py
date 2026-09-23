import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ReplenishmentRun(BaseModel):
    store_id: uuid.UUID
    lead_time_weeks: int = Field(default=2, ge=1, le=12)
    minimum_stock: int = Field(default=0, ge=0)
    budget_limit: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    variant_ids: list[uuid.UUID] | None = None

    @model_validator(mode="after")
    def unique_variants(self):
        if self.variant_ids and len(set(self.variant_ids)) != len(self.variant_ids):
            raise ValueError("Cada variante deve ser informada apenas uma vez.")
        return self


class ReplenishmentDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected|overridden)$")
    approved_quantity: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def override_requires_quantity(self):
        if self.status == "overridden" and self.approved_quantity is None:
            raise ValueError("Informe a quantidade aprovada para uma substituicao manual.")
        return self


class ReplenishmentResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    variant_id: uuid.UUID
    forecast_quantity: Decimal
    forecast_model: str
    lead_time_weeks: int
    minimum_stock: int
    current_quantity: int
    baseline_quantity: int
    simple_rule_quantity: int
    recommended_quantity: int
    approved_quantity: int | None
    unit_cost: Decimal
    planned_cost: Decimal
    budget_limit: Decimal | None
    status: str
    explanation: str
    created_by: uuid.UUID
    decided_by: uuid.UUID | None
    created_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}


class ReplenishmentListResponse(BaseModel):
    items: list[ReplenishmentResponse]
    total: int
