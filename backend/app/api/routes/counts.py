from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user, require_roles
from app.models.inventory import InventoryBalance
from app.models.inventory_count import InventoryCount, InventoryCountItem
from app.models.user import User
from app.schemas.inventory_count import (
    InventoryCountCreate,
    InventoryCountItemCreate,
    InventoryCountResponse,
)
from app.services.inventory import lock_inventory_balances, set_stock_quantity
from app.services.audit import record_audit_event

router = APIRouter(prefix="/counts", tags=["counts"])


@router.post("/", response_model=InventoryCountResponse)
def create_inventory_count(
    payload: InventoryCountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)

    count = InventoryCount(
        store_id=payload.store_id,
        scope=payload.scope,
        reason=payload.reason,
        created_by=current_user.id,
    )
    db.add(count)
    db.flush()
    record_audit_event(
        db,
        action="inventory_count.created",
        entity_type="inventory_count",
        entity_id=count.id,
        store_id=count.store_id,
        actor_id=current_user.id,
        metadata={"scope": count.scope},
    )
    db.commit()
    db.refresh(count)
    return count


@router.post("/{count_id}/items", response_model=InventoryCountResponse)
def upsert_inventory_count_item(
    count_id: uuid.UUID,
    payload: InventoryCountItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    count = db.execute(
        select(InventoryCount).where(InventoryCount.id == count_id).with_for_update()
    ).scalar_one_or_none()
    if not count:
        raise HTTPException(status_code=404, detail="Contagem nao encontrada")
    if count.status != "open":
        raise HTTPException(status_code=400, detail="A contagem ja foi fechada")

    ensure_store_access(current_user, count.store_id)

    balance = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.store_id == count.store_id,
            InventoryBalance.variant_id == payload.variant_id,
        )
        .first()
    )
    system_quantity = balance.on_hand_qty if balance else 0
    difference_quantity = payload.counted_quantity - system_quantity

    item = (
        db.query(InventoryCountItem)
        .filter(
            InventoryCountItem.count_id == count.id,
            InventoryCountItem.variant_id == payload.variant_id,
        )
        .first()
    )

    if item:
        item.system_quantity = system_quantity
        item.counted_quantity = payload.counted_quantity
        item.difference_quantity = difference_quantity
    else:
        item = InventoryCountItem(
            count_id=count.id,
            variant_id=payload.variant_id,
            system_quantity=system_quantity,
            counted_quantity=payload.counted_quantity,
            difference_quantity=difference_quantity,
        )
        db.add(item)

    record_audit_event(
        db,
        action="inventory_count.item_recorded",
        entity_type="inventory_count",
        entity_id=count.id,
        store_id=count.store_id,
        actor_id=current_user.id,
        metadata={
            "variant_id": str(payload.variant_id),
            "system_quantity": system_quantity,
            "counted_quantity": payload.counted_quantity,
            "difference_quantity": difference_quantity,
        },
    )
    db.commit()
    db.refresh(count)
    return count


@router.post("/{count_id}/close", response_model=InventoryCountResponse)
def close_inventory_count(
    count_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    count = db.execute(
        select(InventoryCount).where(InventoryCount.id == count_id).with_for_update()
    ).scalar_one_or_none()
    if not count:
        raise HTTPException(status_code=404, detail="Contagem nao encontrada")
    if count.status != "open":
        raise HTTPException(status_code=400, detail="A contagem ja foi fechada")

    ensure_store_access(current_user, count.store_id)

    try:
        items = db.scalars(
            select(InventoryCountItem).where(InventoryCountItem.count_id == count.id)
        ).all()
        if not items:
            raise HTTPException(status_code=400, detail="A contagem nao possui itens")

        lock_inventory_balances(
            db,
            [(count.store_id, item.variant_id) for item in items],
            create_if_missing=True,
        )
        for item in items:
            set_stock_quantity(
                db,
                store_id=count.store_id,
                variant_id=item.variant_id,
                quantity=item.counted_quantity,
                reference_type="inventory_count",
                reference_id=count.id,
                reason="inventory_count_closed",
                created_by=current_user.id,
            )

        count.status = "closed"
        count.closed_by = current_user.id
        count.closed_at = datetime.now(timezone.utc)
        record_audit_event(
            db,
            action="inventory_count.closed",
            entity_type="inventory_count",
            entity_id=count.id,
            store_id=count.store_id,
            actor_id=current_user.id,
            metadata={
                "item_count": len(items),
                "adjusted_item_count": sum(
                    1 for item in items if item.counted_quantity != item.system_quantity
                ),
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nao foi possivel fechar a contagem") from None

    db.refresh(count)
    return count


@router.get("/", response_model=list[InventoryCountResponse])
def list_inventory_counts(
    store_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(InventoryCount)
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        query = query.filter(InventoryCount.store_id == store_id)
    elif current_user.role != "admin":
        query = query.filter(InventoryCount.store_id == current_user.store_id)
    return query.order_by(InventoryCount.created_at.desc()).all()
