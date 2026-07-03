import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user
from app.models.inventory import InventoryBalance
from app.models.product import Product, ProductVariant
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.schemas.dashboard import (
    DashboardDailySalesPoint,
    DashboardInventorySummary,
    DashboardResponse,
    DashboardSalesSummary,
    DashboardStoreSummary,
    DashboardTopVariant,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def decimal_or_zero(value) -> Decimal:
    return value if value is not None else Decimal("0")


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


@router.get("/", response_model=DashboardResponse)
def get_dashboard(
    store_id: uuid.UUID | None = Query(default=None),
    low_stock_threshold: int = Query(default=3, ge=0),
    days: int = Query(default=7, ge=1, le=90),
    top_limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        scoped_store_id = store_id
    elif current_user.role != "admin":
        scoped_store_id = current_user.store_id
    else:
        scoped_store_id = None
    start_date = utc_today() - timedelta(days=days - 1)

    sales_query = db.query(Sale)
    inventory_query = db.query(InventoryBalance)
    store_sales_query = db.query(Sale)
    store_inventory_query = db.query(InventoryBalance)

    if scoped_store_id is not None:
        sales_query = sales_query.filter(Sale.store_id == scoped_store_id)
        inventory_query = inventory_query.filter(InventoryBalance.store_id == scoped_store_id)
        store_sales_query = store_sales_query.filter(Sale.store_id == scoped_store_id)
        store_inventory_query = store_inventory_query.filter(
            InventoryBalance.store_id == scoped_store_id
        )

    sales_row = sales_query.with_entities(
        func.coalesce(func.sum(case((Sale.status == "completed", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Sale.status == "canceled", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Sale.status == "completed", Sale.total_amount + Sale.discount_amount), else_=0)), 0),
        func.coalesce(func.sum(case((Sale.status == "completed", Sale.discount_amount), else_=0)), 0),
        func.coalesce(func.sum(case((Sale.status == "completed", Sale.total_amount), else_=0)), 0),
    ).one()

    items_sold_query = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.status == "completed")
    )
    if scoped_store_id is not None:
        items_sold_query = items_sold_query.filter(Sale.store_id == scoped_store_id)
    items_sold = items_sold_query.scalar() or 0

    inventory_row = inventory_query.with_entities(
        func.count(InventoryBalance.id),
        func.coalesce(func.sum(InventoryBalance.on_hand_qty), 0),
        func.coalesce(func.sum(InventoryBalance.reserved_qty), 0),
        func.coalesce(
            func.sum(
                case(
                    (
                        (InventoryBalance.on_hand_qty > 0)
                        & (InventoryBalance.on_hand_qty <= low_stock_threshold),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(case((InventoryBalance.on_hand_qty == 0, 1), else_=0)),
            0,
        ),
    ).one()

    sales_by_store = {
        row[0]: (row[1], decimal_or_zero(row[2]))
        for row in store_sales_query.with_entities(
            Sale.store_id,
            func.coalesce(
                func.sum(case((Sale.status == "completed", 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((Sale.status == "completed", Sale.total_amount), else_=0)),
                0,
            ),
        )
        .group_by(Sale.store_id)
        .all()
    }

    inventory_by_store = {
        row[0]: row[1]
        for row in store_inventory_query.with_entities(
            InventoryBalance.store_id,
            func.coalesce(func.sum(InventoryBalance.on_hand_qty), 0),
        )
        .group_by(InventoryBalance.store_id)
        .all()
    }

    store_ids = sorted(set(sales_by_store) | set(inventory_by_store), key=str)
    stores = [
        DashboardStoreSummary(
            store_id=store_key,
            sales_count=sales_by_store.get(store_key, (0, Decimal("0")))[0],
            net_revenue=decimal_or_zero(sales_by_store.get(store_key, (0, Decimal("0")))[1]),
            on_hand_qty=inventory_by_store.get(store_key, 0),
        )
        for store_key in store_ids
    ]

    daily_sales_rows = (
        db.query(
            func.date(Sale.sold_at),
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total_amount), 0),
        )
        .filter(
            Sale.status == "completed",
            func.date(Sale.sold_at) >= start_date.isoformat(),
        )
    )
    if scoped_store_id is not None:
        daily_sales_rows = daily_sales_rows.filter(Sale.store_id == scoped_store_id)
    daily_sales_map = {
        date.fromisoformat(str(row[0])): (row[1], decimal_or_zero(row[2]))
        for row in daily_sales_rows.group_by(func.date(Sale.sold_at)).all()
    }
    daily_sales = []
    for offset in range(days):
        current_date = start_date + timedelta(days=offset)
        current_values = daily_sales_map.get(current_date, (0, Decimal("0")))
        daily_sales.append(
            DashboardDailySalesPoint(
                date=current_date,
                sales_count=current_values[0],
                net_revenue=current_values[1],
            )
        )

    top_variants_query = (
        db.query(
            SaleItem.variant_id,
            ProductVariant.sku,
            Product.name,
            func.coalesce(func.sum(SaleItem.quantity), 0),
            func.coalesce(func.sum(SaleItem.line_total), 0),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(ProductVariant, ProductVariant.id == SaleItem.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .filter(
            Sale.status == "completed",
            func.date(Sale.sold_at) >= start_date.isoformat(),
        )
    )
    if scoped_store_id is not None:
        top_variants_query = top_variants_query.filter(Sale.store_id == scoped_store_id)
    top_variants = [
        DashboardTopVariant(
            variant_id=row[0],
            sku=row[1],
            product_name=row[2],
            quantity_sold=row[3],
            net_revenue=decimal_or_zero(row[4]),
        )
        for row in top_variants_query.group_by(
            SaleItem.variant_id,
            ProductVariant.sku,
            Product.name,
        )
        .order_by(
            func.sum(SaleItem.quantity).desc(),
            func.sum(SaleItem.line_total).desc(),
            ProductVariant.sku.asc(),
        )
        .limit(top_limit)
        .all()
    ]

    return DashboardResponse(
        scope_store_id=scoped_store_id,
        sales=DashboardSalesSummary(
            completed_count=sales_row[0],
            canceled_count=sales_row[1],
            gross_revenue=decimal_or_zero(sales_row[2]),
            discount_total=decimal_or_zero(sales_row[3]),
            net_revenue=decimal_or_zero(sales_row[4]),
            items_sold=items_sold,
        ),
        inventory=DashboardInventorySummary(
            tracked_variants=inventory_row[0],
            total_on_hand_qty=inventory_row[1],
            total_reserved_qty=inventory_row[2],
            low_stock_variants=inventory_row[3],
            out_of_stock_variants=inventory_row[4],
        ),
        stores=stores,
        daily_sales=daily_sales,
        top_variants=top_variants,
    )
