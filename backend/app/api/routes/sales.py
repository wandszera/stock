import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user, require_roles
from app.models.inventory import InventoryBalance, StockMovement
from app.models.product import Product, ProductVariant
from app.models.sale import Sale, SaleItem
from app.models.user import User
from app.schemas.sale import SaleCreate, SaleListResponse, SaleResponse, SaleReturnCreate

router = APIRouter(prefix="/sales", tags=["sales"])


def build_sales_query(db: Session):
    return db.query(Sale).options(selectinload(Sale.items))


@router.get("/", response_model=SaleListResponse)
def list_sales(
    store_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sold_from: date | None = Query(default=None),
    sold_to: date | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = build_sales_query(db)

    if store_id is not None:
        ensure_store_access(current_user, store_id)
        query = query.filter(Sale.store_id == store_id)
    elif current_user.role != "admin":
        query = query.filter(Sale.store_id == current_user.store_id)

    if q:
        search = f"%{q.strip()}%"
        query = (
            query.join(Sale.items)
            .join(SaleItem.variant)
            .join(ProductVariant.product)
            .filter(
                or_(
                    ProductVariant.sku.ilike(search),
                    Product.name.ilike(search),
                )
            )
            .distinct()
        )
    if status is not None:
        query = query.filter(Sale.status == status)
    if sold_from is not None:
        query = query.filter(
            Sale.sold_at >= datetime.combine(sold_from, time.min, tzinfo=timezone.utc)
        )
    if sold_to is not None:
        query = query.filter(
            Sale.sold_at < datetime.combine(sold_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )

    total = query.count()
    items = query.order_by(Sale.sold_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/", response_model=SaleResponse)
def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "operator")),
):
    total_amount = Decimal("0")

    if not payload.items:
        raise HTTPException(status_code=400, detail="A venda precisa ter pelo menos um item.")

    ensure_store_access(current_user, payload.store_id)
    sale: Sale | None = None

    try:
        balances: dict[uuid.UUID, InventoryBalance] = {}

        for item in payload.items:
            balance = db.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.store_id == payload.store_id,
                    InventoryBalance.variant_id == item.variant_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if not balance or balance.on_hand_qty < item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Estoque insuficiente para {item.variant_id}",
                )

            balances[item.variant_id] = balance
            total_amount += item.quantity * item.unit_price

        final_amount = total_amount - payload.discount_amount
        if final_amount < 0:
            raise HTTPException(
                status_code=400,
                detail="O desconto nao pode ser maior que o total da venda.",
            )

        sale = Sale(
            store_id=payload.store_id,
            user_id=payload.user_id or current_user.id,
            status="completed",
            total_amount=final_amount,
            discount_amount=payload.discount_amount,
        )
        db.add(sale)
        db.flush()

        for item in payload.items:
            balances[item.variant_id].on_hand_qty -= item.quantity

            db.add(
                SaleItem(
                    sale_id=sale.id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.quantity * item.unit_price,
                )
            )
            db.add(
                StockMovement(
                    store_id=payload.store_id,
                    variant_id=item.variant_id,
                    movement_type="sale",
                    quantity_delta=-item.quantity,
                    reference_type="sale",
                    reference_id=sale.id,
                    reason="sale_completed",
                    created_by=current_user.id,
                )
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Loja, usuario ou variante informado nao foi encontrado.",
        ) from None

    if sale is None:
        raise HTTPException(status_code=500, detail="Nao foi possivel concluir a venda.")

    db.refresh(sale)
    return sale


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = (
        build_sales_query(db)
        .filter(Sale.id == sale_id)
        .first()
    )

    if not sale:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    ensure_store_access(current_user, sale.store_id)
    return sale


@router.post("/{sale_id}/cancel", response_model=SaleResponse)
def cancel_sale(
    sale_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    sale: Sale | None = None

    try:
        sale = db.execute(
            select(Sale).where(Sale.id == sale_id).with_for_update()
        ).scalar_one_or_none()

        if not sale:
            raise HTTPException(status_code=404, detail="Venda nao encontrada")

        ensure_store_access(current_user, sale.store_id)

        if sale.status == "canceled":
            raise HTTPException(status_code=400, detail="Venda ja cancelada")

        items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()

        for item in items:
            balance = db.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.store_id == sale.store_id,
                    InventoryBalance.variant_id == item.variant_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if not balance:
                raise HTTPException(
                    status_code=500,
                    detail="Saldo nao encontrado para estornar a venda.",
                )

            balance.on_hand_qty += item.quantity
            db.add(
                StockMovement(
                    store_id=sale.store_id,
                    variant_id=item.variant_id,
                    movement_type="reversal",
                    quantity_delta=item.quantity,
                    reference_type="sale_cancel",
                    reference_id=sale.id,
                    reason="sale_canceled",
                    created_by=current_user.id,
                )
            )

        sale.status = "canceled"
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nao foi possivel cancelar a venda.") from None

    if sale is None:
        raise HTTPException(status_code=500, detail="Nao foi possivel carregar a venda.")

    db.refresh(sale)
    return sale


@router.post("/{sale_id}/return", response_model=SaleResponse)
def return_sale_items(
    sale_id: uuid.UUID,
    payload: SaleReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Informe ao menos um item para devolucao.")

    sale: Sale | None = None
    try:
        sale = db.execute(
            select(Sale).where(Sale.id == sale_id).with_for_update()
        ).scalar_one_or_none()

        if not sale:
            raise HTTPException(status_code=404, detail="Venda nao encontrada")

        ensure_store_access(current_user, sale.store_id)

        if sale.status != "completed":
            raise HTTPException(status_code=400, detail="Apenas vendas concluidas podem receber devolucao.")

        sale_items = {
            item.variant_id: item
            for item in db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
        }

        for return_item in payload.items:
            sale_item = sale_items.get(return_item.variant_id)
            if sale_item is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Variante {return_item.variant_id} nao pertence a esta venda.",
                )

            returned_qty = db.execute(
                select(func.coalesce(func.sum(StockMovement.quantity_delta), 0)).where(
                    StockMovement.store_id == sale.store_id,
                    StockMovement.variant_id == return_item.variant_id,
                    StockMovement.reference_type == "sale_return",
                    StockMovement.reference_id == sale.id,
                )
            ).scalar_one()

            available_to_return = sale_item.quantity - int(returned_qty or 0)
            if return_item.quantity > available_to_return:
                raise HTTPException(
                    status_code=409,
                    detail=f"Quantidade de devolucao maior que o disponivel para {return_item.variant_id}.",
                )

            balance = db.execute(
                select(InventoryBalance)
                .where(
                    InventoryBalance.store_id == sale.store_id,
                    InventoryBalance.variant_id == return_item.variant_id,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if not balance:
                raise HTTPException(
                    status_code=500,
                    detail="Saldo nao encontrado para processar a devolucao.",
                )

            balance.on_hand_qty += return_item.quantity
            db.add(
                StockMovement(
                    store_id=sale.store_id,
                    variant_id=return_item.variant_id,
                    movement_type="return",
                    quantity_delta=return_item.quantity,
                    reference_type="sale_return",
                    reference_id=sale.id,
                    reason="sale_item_returned",
                    created_by=current_user.id,
                )
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nao foi possivel processar a devolucao.") from None

    if sale is None:
        raise HTTPException(status_code=500, detail="Nao foi possivel carregar a venda.")

    db.refresh(sale)
    return sale
