import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class SaleItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class SaleCreate(BaseModel):
    store_id: uuid.UUID
    user_id: uuid.UUID | None = None
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    items: list[SaleItemCreate]


class SaleReturnItemCreate(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(gt=0)


class SaleReturnCreate(BaseModel):
    items: list[SaleReturnItemCreate]


class SaleItemResponse(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class SaleResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    user_id: uuid.UUID | None
    status: str
    total_amount: Decimal
    discount_amount: Decimal
    sold_at: datetime
    items: list[SaleItemResponse]

    model_config = {"from_attributes": True}


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    total: int
    limit: int
    offset: int


class SalePeriodFilter(BaseModel):
    sold_from: date | None = None
    sold_to: date | None = None
