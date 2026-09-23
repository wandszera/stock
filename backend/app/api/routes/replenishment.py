import uuid
from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.datasets import build_weekly_demand_series
from app.analytics.forecasting import MODELS
from app.analytics.replenishment import allocate_budget, build_replenishment_candidate
from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user, require_roles
from app.models.analytics import ForecastBacktestRun, ReplenishmentRecommendation
from app.models.inventory import InventoryBalance
from app.models.product import ProductVariant
from app.models.user import User
from app.schemas.replenishment import (
    ReplenishmentDecision, ReplenishmentListResponse, ReplenishmentResponse, ReplenishmentRun,
)
from app.services.audit import record_audit_event


router = APIRouter(prefix="/replenishment", tags=["replenishment"])


def forecast_for_variant(db: Session, *, store_id: uuid.UUID, variant_id: uuid.UUID) -> tuple[float, str]:
    series = build_weekly_demand_series(db, store_id=store_id, variant_id=variant_id)
    if series.empty:
        return 0.0, "no_sales_history"
    run = (
        db.query(ForecastBacktestRun)
        .filter(ForecastBacktestRun.store_id == store_id, ForecastBacktestRun.variant_id == variant_id)
        .order_by(ForecastBacktestRun.created_at.desc())
        .first()
    )
    model_name = run.winner_model if run and run.winner_model in MODELS else "moving_average_4"
    values = np.asarray(series.tolist(), dtype=float)
    try:
        return float(MODELS[model_name](values, 1)[0]), model_name
    except Exception:
        return float(np.mean(values[-min(4, len(values)) :])), "moving_average_4_fallback"


@router.post("/recommendations/run", response_model=ReplenishmentListResponse)
def run_replenishment(
    payload: ReplenishmentRun,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    query = (
        db.query(InventoryBalance, ProductVariant)
        .join(ProductVariant, ProductVariant.id == InventoryBalance.variant_id)
        .filter(InventoryBalance.store_id == payload.store_id)
    )
    if payload.variant_ids:
        query = query.filter(InventoryBalance.variant_id.in_(payload.variant_ids))
    rows = query.all()
    if not rows:
        raise HTTPException(status_code=422, detail="Nao existem saldos para gerar recomendacoes.")

    candidates = []
    for balance, variant in rows:
        forecast_quantity, forecast_model = forecast_for_variant(
            db, store_id=payload.store_id, variant_id=variant.id
        )
        candidate = build_replenishment_candidate(
            forecast_quantity=forecast_quantity, forecast_model=forecast_model,
            current_quantity=balance.on_hand_qty, minimum_stock=payload.minimum_stock,
            lead_time_weeks=payload.lead_time_weeks, unit_cost=float(variant.cost_price),
        )
        candidate.update({"balance": balance, "variant": variant})
        candidates.append(candidate)
    allocate_budget(candidates, float(payload.budget_limit) if payload.budget_limit is not None else None)

    recommendations = []
    for candidate in candidates:
        quantity = candidate["recommended_quantity"]
        planned_cost = Decimal(str(round(quantity * candidate["unit_cost"], 2)))
        constrained = quantity < candidate["proposed_quantity"]
        explanation = (
            f"Previsao de {candidate['forecast_quantity']:.2f} unidades/semana pelo modelo "
            f"{candidate['forecast_model']}; prazo de {payload.lead_time_weeks} semana(s), "
            f"estoque atual de {candidate['balance'].on_hand_qty}, minimo de {payload.minimum_stock} "
            f"e reserva de {candidate['safety_stock']} unidades. A politica atual sugere 0, "
            f"a regra simples sugere {candidate['simple_rule_quantity']} e o modelo sugere {quantity}."
        )
        if constrained:
            explanation += " A recomendacao foi reduzida para respeitar o orcamento informado."
        recommendation = ReplenishmentRecommendation(
            store_id=payload.store_id, variant_id=candidate["variant"].id,
            forecast_quantity=Decimal(str(candidate["forecast_quantity"])), forecast_model=candidate["forecast_model"],
            lead_time_weeks=payload.lead_time_weeks, minimum_stock=payload.minimum_stock,
            current_quantity=candidate["balance"].on_hand_qty, baseline_quantity=candidate["baseline_quantity"],
            simple_rule_quantity=candidate["simple_rule_quantity"], recommended_quantity=quantity,
            unit_cost=Decimal(str(candidate["unit_cost"])), planned_cost=planned_cost,
            budget_limit=payload.budget_limit, status="proposed", explanation=explanation,
            created_by=current_user.id,
        )
        db.add(recommendation)
        db.flush()
        record_audit_event(
            db, action="replenishment.recommended", entity_type="replenishment_recommendation",
            entity_id=recommendation.id, store_id=payload.store_id, actor_id=current_user.id,
            metadata={"variant_id": str(recommendation.variant_id), "recommended_quantity": quantity, "planned_cost": str(planned_cost)},
        )
        recommendations.append(recommendation)
    db.commit()
    for item in recommendations:
        db.refresh(item)
    recommendations.sort(key=lambda item: item.planned_cost, reverse=True)
    return {"items": recommendations, "total": len(recommendations)}


@router.get("/recommendations", response_model=ReplenishmentListResponse)
def list_recommendations(
    store_id: uuid.UUID = Query(),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    ensure_store_access(current_user, store_id)
    items = (
        db.query(ReplenishmentRecommendation)
        .filter(ReplenishmentRecommendation.store_id == store_id)
        .order_by(ReplenishmentRecommendation.created_at.desc())
        .all()
    )
    return {"items": items, "total": len(items)}


@router.patch("/recommendations/{recommendation_id}/decision", response_model=ReplenishmentResponse)
def decide_recommendation(
    recommendation_id: uuid.UUID, payload: ReplenishmentDecision,
    db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "manager")),
):
    recommendation = db.query(ReplenishmentRecommendation).filter(ReplenishmentRecommendation.id == recommendation_id).first()
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recomendacao nao encontrada.")
    ensure_store_access(current_user, recommendation.store_id)
    recommendation.status = payload.status
    recommendation.approved_quantity = (
        payload.approved_quantity if payload.status == "overridden"
        else (recommendation.recommended_quantity if payload.status == "approved" else 0)
    )
    recommendation.decided_by = current_user.id
    recommendation.decided_at = datetime.now(timezone.utc)
    record_audit_event(
        db, action="replenishment.decision_recorded", entity_type="replenishment_recommendation",
        entity_id=recommendation.id, store_id=recommendation.store_id, actor_id=current_user.id,
        metadata={"status": recommendation.status, "approved_quantity": recommendation.approved_quantity},
    )
    db.commit()
    db.refresh(recommendation)
    return recommendation
