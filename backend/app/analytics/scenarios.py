"""What-if calculations for replenishment recommendations."""

from __future__ import annotations

from app.analytics.replenishment import allocate_budget, build_replenishment_candidate


def simulate_replenishment_scenario(
    items: list[dict], *, demand_multiplier: float, supplier_delay_weeks: int,
    lead_time_weeks: int, minimum_stock: int, budget_limit: float | None,
) -> list[dict]:
    effective_lead_time = lead_time_weeks + supplier_delay_weeks
    candidates = []
    for item in items:
        candidate = build_replenishment_candidate(
            forecast_quantity=item["forecast_quantity"] * demand_multiplier,
            forecast_model=item["forecast_model"], current_quantity=item["current_quantity"],
            minimum_stock=minimum_stock, lead_time_weeks=effective_lead_time,
            unit_cost=item["unit_cost"],
        )
        candidate.update(item)
        candidates.append(candidate)
    allocate_budget(candidates, budget_limit)
    for candidate in candidates:
        demand_until_arrival = candidate["lead_time_demand"]
        candidate["effective_lead_time_weeks"] = effective_lead_time
        candidate["current_policy_stockout"] = max(demand_until_arrival - candidate["current_quantity"], 0)
        candidate["simple_rule_stockout"] = max(
            demand_until_arrival - candidate["current_quantity"] - candidate["simple_rule_quantity"], 0
        )
        candidate["model_stockout"] = max(
            demand_until_arrival - candidate["current_quantity"] - candidate["recommended_quantity"], 0
        )
    return candidates
