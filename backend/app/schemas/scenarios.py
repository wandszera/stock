import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class ReplenishmentScenarioRequest(BaseModel):
    store_id: uuid.UUID
    demand_multiplier: float = Field(default=1, ge=0.1, le=5)
    supplier_delay_weeks: int = Field(default=0, ge=0, le=12)
    lead_time_weeks: int = Field(default=2, ge=1, le=12)
    minimum_stock: int = Field(default=0, ge=0)
    budget_limit: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class ReplenishmentScenarioItem(BaseModel):
    variant_id: uuid.UUID
    forecast_quantity: float
    forecast_model: str
    effective_lead_time_weeks: int
    current_policy_stockout: int
    simple_rule_stockout: int
    model_stockout: int
    simple_rule_quantity: int
    recommended_quantity: int
    planned_cost: Decimal
    explanation: str


class ReplenishmentScenarioResponse(BaseModel):
    demand_multiplier: float
    supplier_delay_weeks: int
    budget_limit: Decimal | None
    items: list[ReplenishmentScenarioItem]
    total_current_policy_stockout: int
    total_simple_rule_stockout: int
    total_model_stockout: int
