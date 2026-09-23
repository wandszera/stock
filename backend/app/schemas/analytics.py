import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BacktestCreate(BaseModel):
    store_id: uuid.UUID
    variant_id: uuid.UUID
    horizon: int = Field(default=1, ge=1, le=12)
    minimum_train_periods: int = Field(default=8, ge=4, le=104)


class ModelMetrics(BaseModel):
    model: str
    mae: float
    rmse: float
    wape: float
    bias: float
    service_level: float
    evaluation_points: int
    fallback_count: int


class BacktestResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    variant_id: uuid.UUID
    status: str
    frequency: str
    horizon: int
    minimum_train_periods: int
    winner_model: str
    results: list[ModelMetrics]
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BacktestListResponse(BaseModel):
    items: list[BacktestResponse]
    total: int
