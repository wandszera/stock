import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardSalesSummary(BaseModel):
    completed_count: int
    canceled_count: int
    gross_revenue: Decimal
    discount_total: Decimal
    net_revenue: Decimal
    items_sold: int


class DashboardInventorySummary(BaseModel):
    tracked_variants: int
    total_on_hand_qty: int
    total_reserved_qty: int
    low_stock_variants: int
    out_of_stock_variants: int


class DashboardStoreSummary(BaseModel):
    store_id: uuid.UUID
    sales_count: int
    net_revenue: Decimal
    on_hand_qty: int


class DashboardDailySalesPoint(BaseModel):
    date: date
    sales_count: int
    net_revenue: Decimal


class DashboardTopVariant(BaseModel):
    variant_id: uuid.UUID
    sku: str
    product_name: str
    quantity_sold: int
    net_revenue: Decimal


class DashboardResponse(BaseModel):
    scope_store_id: uuid.UUID | None
    sales: DashboardSalesSummary
    inventory: DashboardInventorySummary
    stores: list[DashboardStoreSummary]
    daily_sales: list[DashboardDailySalesPoint]
    top_variants: list[DashboardTopVariant]
