"""Transparent supplier-risk scoring used by the decision-intelligence API."""

from __future__ import annotations

from math import sqrt
from typing import Iterable

from app.models.analytics import SupplierDelivery


WEIGHTS = {
    "delay": 0.35,
    "variability": 0.20,
    "defects": 0.25,
    "concentration": 0.20,
}


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 100.0)


def _risk_level(score: float) -> str:
    if score < 30:
        return "low"
    if score < 60:
        return "moderate"
    if score < 80:
        return "high"
    return "critical"


def calculate_supplier_risk(
    deliveries: Iterable[SupplierDelivery], *, store_purchase_cost: float
) -> dict:
    records = list(deliveries)
    if not records:
        raise ValueError("O fornecedor nao possui entregas registradas.")

    delays = [max((item.delivered_at - item.expected_at).days, 0) for item in records]
    lead_times = [(item.delivered_at - item.ordered_at).days for item in records]
    mean_delay = sum(delays) / len(delays)
    mean_lead_time = sum(lead_times) / len(lead_times)
    lead_time_std = sqrt(
        sum((value - mean_lead_time) ** 2 for value in lead_times) / len(lead_times)
    )
    received = sum(item.received_quantity for item in records)
    defects = sum(item.defective_quantity for item in records)
    supplier_cost = sum(float(item.purchase_cost) for item in records)
    defect_rate = defects / received if received else 0.0
    concentration = supplier_cost / store_purchase_cost if store_purchase_cost else 0.0

    normalized = {
        "delay": _clamp(mean_delay / 30 * 100),
        "variability": _clamp(lead_time_std / 15 * 100),
        "defects": _clamp(defect_rate / 0.20 * 100),
        "concentration": _clamp(concentration * 100),
    }
    contributions = {key: normalized[key] * weight for key, weight in WEIGHTS.items()}
    score = round(sum(contributions.values()), 2)
    labels = {
        "delay": "atraso medio",
        "variability": "variabilidade do prazo",
        "defects": "taxa de defeitos",
        "concentration": "concentracao de compras",
    }
    drivers = sorted(contributions, key=contributions.get, reverse=True)[:2]
    explanation = (
        f"Principais fatores: {labels[drivers[0]]} e {labels[drivers[1]]}. "
        f"Atraso medio de {mean_delay:.1f} dias, variabilidade de {lead_time_std:.1f} dias, "
        f"defeitos de {defect_rate:.1%} e concentracao de {concentration:.1%}."
    )
    components = {
        key: {
            "normalized_score": round(normalized[key], 2),
            "weight": WEIGHTS[key],
            "contribution": round(contributions[key], 2),
        }
        for key in WEIGHTS
    }
    components["raw_metrics"] = {
        "mean_delay_days": round(mean_delay, 2),
        "lead_time_std_days": round(lead_time_std, 2),
        "defect_rate": round(defect_rate, 4),
        "purchase_concentration": round(concentration, 4),
    }
    return {
        "score": score,
        "risk_level": _risk_level(score),
        "components": components,
        "explanation": explanation,
        "delivery_count": len(records),
    }
