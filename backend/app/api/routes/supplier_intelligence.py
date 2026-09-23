import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.supplier_risk import calculate_supplier_risk
from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user, require_roles
from app.models.analytics import SupplierDelivery, SupplierRiskScore
from app.models.user import User
from app.schemas.supplier_intelligence import (
    SupplierDeliveryCreate,
    SupplierDeliveryResponse,
    SupplierRiskListResponse,
    SupplierRiskResponse,
    SupplierRiskRun,
)
from app.services.audit import record_audit_event


router = APIRouter(prefix="/supplier-intelligence", tags=["supplier intelligence"])


@router.post("/deliveries", response_model=SupplierDeliveryResponse, status_code=201)
def create_delivery(
    payload: SupplierDeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    delivery = SupplierDelivery(**payload.model_dump(), created_by=current_user.id)
    db.add(delivery)
    db.flush()
    record_audit_event(
        db,
        action="supplier.delivery_recorded",
        entity_type="supplier_delivery",
        entity_id=delivery.id,
        store_id=delivery.store_id,
        actor_id=current_user.id,
        metadata={"supplier_reference": delivery.supplier_reference},
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.post("/scores/run", response_model=SupplierRiskListResponse)
def run_supplier_scores(
    payload: SupplierRiskRun,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    query = db.query(SupplierDelivery).filter(SupplierDelivery.store_id == payload.store_id)
    if payload.supplier_reference:
        query = query.filter(SupplierDelivery.supplier_reference == payload.supplier_reference.strip())
    deliveries = query.all()
    if not deliveries:
        raise HTTPException(status_code=422, detail="Nenhuma entrega encontrada para calcular o risco.")

    total_cost = float(
        db.query(func.coalesce(func.sum(SupplierDelivery.purchase_cost), 0))
        .filter(SupplierDelivery.store_id == payload.store_id)
        .scalar()
    )
    grouped = defaultdict(list)
    for delivery in deliveries:
        grouped[delivery.supplier_reference].append(delivery)

    scores = []
    for supplier_reference, supplier_deliveries in grouped.items():
        result = calculate_supplier_risk(supplier_deliveries, store_purchase_cost=total_cost)
        score = SupplierRiskScore(
            store_id=payload.store_id,
            supplier_reference=supplier_reference,
            score=Decimal(str(result["score"])),
            risk_level=result["risk_level"],
            components=result["components"],
            explanation=result["explanation"],
            delivery_count=result["delivery_count"],
            created_by=current_user.id,
        )
        db.add(score)
        db.flush()
        record_audit_event(
            db,
            action="supplier.risk_scored",
            entity_type="supplier_risk_score",
            entity_id=score.id,
            store_id=score.store_id,
            actor_id=current_user.id,
            metadata={"supplier_reference": supplier_reference, "score": result["score"]},
        )
        scores.append(score)
    db.commit()
    for score in scores:
        db.refresh(score)
    scores.sort(key=lambda item: item.score, reverse=True)
    return {"items": scores, "total": len(scores)}


@router.get("/ranking", response_model=SupplierRiskListResponse)
def get_supplier_ranking(
    store_id: uuid.UUID = Query(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_store_access(current_user, store_id)
    rows = (
        db.query(SupplierRiskScore)
        .filter(SupplierRiskScore.store_id == store_id)
        .order_by(SupplierRiskScore.created_at.desc(), SupplierRiskScore.score.desc())
        .all()
    )
    latest = {}
    for row in rows:
        latest.setdefault(row.supplier_reference, row)
    items = sorted(latest.values(), key=lambda item: item.score, reverse=True)
    return {"items": items, "total": len(items)}
