"""Deterministic, explainable replenishment policy and budget allocator."""

from __future__ import annotations

from math import ceil


def build_replenishment_candidate(
    *, forecast_quantity: float, forecast_model: str, current_quantity: int,
    minimum_stock: int, lead_time_weeks: int, unit_cost: float,
) -> dict:
    lead_time_demand = ceil(max(forecast_quantity, 0) * lead_time_weeks)
    safety_stock = ceil(max(forecast_quantity, 0) * 0.25)
    simple_rule_quantity = max(lead_time_demand - current_quantity, 0)
    proposed_quantity = max(minimum_stock + lead_time_demand + safety_stock - current_quantity, 0)
    return {
        "forecast_quantity": round(max(forecast_quantity, 0), 2),
        "forecast_model": forecast_model,
        "lead_time_demand": lead_time_demand,
        "safety_stock": safety_stock,
        "baseline_quantity": 0,
        "simple_rule_quantity": simple_rule_quantity,
        "proposed_quantity": proposed_quantity,
        "unit_cost": unit_cost,
    }


def allocate_budget(candidates: list[dict], budget_limit: float | None) -> list[dict]:
    """Fund the highest expected stockout exposure first, without exceeding budget."""
    if budget_limit is None:
        for candidate in candidates:
            candidate["recommended_quantity"] = candidate["proposed_quantity"]
        return candidates
    remaining = budget_limit
    ordered = sorted(
        candidates,
        key=lambda item: (
            item["proposed_quantity"] * item["unit_cost"],
            item["forecast_quantity"],
        ),
        reverse=True,
    )
    for candidate in ordered:
        cost = candidate["unit_cost"]
        affordable = candidate["proposed_quantity"] if cost <= 0 else int(remaining // cost)
        quantity = min(candidate["proposed_quantity"], max(affordable, 0))
        candidate["recommended_quantity"] = quantity
        remaining -= quantity * cost
    return candidates
