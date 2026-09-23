from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.scenarios import simulate_replenishment_scenario
from app.api.routes.replenishment import forecast_for_variant
from app.core.database import get_db
from app.core.security import ensure_store_access, require_roles
from app.models.inventory import InventoryBalance
from app.models.product import ProductVariant
from app.models.user import User
from app.schemas.scenarios import ReplenishmentScenarioRequest, ReplenishmentScenarioResponse


router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/replenishment", response_model=ReplenishmentScenarioResponse)
def simulate_replenishment(
    payload: ReplenishmentScenarioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    rows = (
        db.query(InventoryBalance, ProductVariant)
        .join(ProductVariant, ProductVariant.id == InventoryBalance.variant_id)
        .filter(InventoryBalance.store_id == payload.store_id)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=422, detail="Nao existem saldos para simular cenarios.")
    items = []
    for balance, variant in rows:
        forecast_quantity, forecast_model = forecast_for_variant(
            db, store_id=payload.store_id, variant_id=variant.id
        )
        items.append({
            "variant_id": variant.id, "forecast_quantity": forecast_quantity,
            "forecast_model": forecast_model, "current_quantity": balance.on_hand_qty,
            "unit_cost": float(variant.cost_price),
        })
    simulated = simulate_replenishment_scenario(
        items, demand_multiplier=payload.demand_multiplier,
        supplier_delay_weeks=payload.supplier_delay_weeks, lead_time_weeks=payload.lead_time_weeks,
        minimum_stock=payload.minimum_stock,
        budget_limit=float(payload.budget_limit) if payload.budget_limit is not None else None,
    )
    response_items = []
    for item in simulated:
        constrained = item["recommended_quantity"] < item["proposed_quantity"]
        explanation = (
            f"Demanda ajustada em {payload.demand_multiplier:.2f}x e prazo total de "
            f"{item['effective_lead_time_weeks']} semana(s). A politica atual perde "
            f"{item['current_policy_stockout']} unidade(s), a regra simples perde "
            f"{item['simple_rule_stockout']} e o modelo perde {item['model_stockout']}."
        )
        if constrained:
            explanation += " O orcamento limita a recomendacao."
        response_items.append({
            "variant_id": item["variant_id"], "forecast_quantity": item["forecast_quantity"],
            "forecast_model": item["forecast_model"], "effective_lead_time_weeks": item["effective_lead_time_weeks"],
            "current_policy_stockout": item["current_policy_stockout"], "simple_rule_stockout": item["simple_rule_stockout"],
            "model_stockout": item["model_stockout"], "simple_rule_quantity": item["simple_rule_quantity"],
            "recommended_quantity": item["recommended_quantity"],
            "planned_cost": Decimal(str(round(item["recommended_quantity"] * item["unit_cost"], 2))),
            "explanation": explanation,
        })
    return {
        "demand_multiplier": payload.demand_multiplier, "supplier_delay_weeks": payload.supplier_delay_weeks,
        "budget_limit": payload.budget_limit, "items": response_items,
        "total_current_policy_stockout": sum(item["current_policy_stockout"] for item in simulated),
        "total_simple_rule_stockout": sum(item["simple_rule_stockout"] for item in simulated),
        "total_model_stockout": sum(item["model_stockout"] for item in simulated),
    }
