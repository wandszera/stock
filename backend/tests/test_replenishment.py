from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.analytics.replenishment import allocate_budget, build_replenishment_candidate
from app.models.analytics import ReplenishmentRecommendation
from app.models.audit import AuditEvent
from app.models.sale import Sale, SaleItem


def seed_sales(db_session, *, store_id, variant_id):
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    for index, quantity in enumerate([8, 9, 10, 11, 12, 13]):
        sale = Sale(store_id=store_id, status="completed", total_amount=Decimal("100"), discount_amount=Decimal("0"), sold_at=start + timedelta(weeks=index))
        db_session.add(sale)
        db_session.flush()
        db_session.add(SaleItem(sale_id=sale.id, variant_id=variant_id, quantity=quantity, unit_price=Decimal("10"), line_total=Decimal("10")))
    db_session.commit()


def test_budget_allocator_prioritizes_exposure_without_exceeding_limit():
    urgent = build_replenishment_candidate(forecast_quantity=10, forecast_model="naive", current_quantity=0, minimum_stock=5, lead_time_weeks=2, unit_cost=10)
    less_urgent = build_replenishment_candidate(forecast_quantity=4, forecast_model="naive", current_quantity=0, minimum_stock=0, lead_time_weeks=1, unit_cost=10)

    allocate_budget([urgent, less_urgent], 100)

    assert urgent["recommended_quantity"] == 10
    assert less_urgent["recommended_quantity"] == 0
    assert sum(item["recommended_quantity"] * item["unit_cost"] for item in [urgent, less_urgent]) <= 100


def test_replenishment_compares_policies_and_supports_human_override(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Reposicao")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=2)
    seed_sales(db_session, store_id=store.id, variant_id=variant.id)
    headers = auth_headers("manager@replenishment.com", "secret123", "manager", store_id=store.id)
    headers["X-Request-ID"] = "replenishment-run-001"

    response = client.post(
        "/replenishment/recommendations/run", headers=headers,
        json={"store_id": str(store.id), "lead_time_weeks": 2, "minimum_stock": 5, "budget_limit": "100.00"},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["baseline_quantity"] == 0
    assert item["recommended_quantity"] <= item["simple_rule_quantity"]
    assert "orcamento" in item["explanation"]
    assert "politica atual" in item["explanation"]
    assert db_session.query(ReplenishmentRecommendation).count() == 1
    assert db_session.query(AuditEvent).filter_by(action="replenishment.recommended").count() == 1

    decision = client.patch(
        f"/replenishment/recommendations/{item['id']}/decision", headers=headers,
        json={"status": "overridden", "approved_quantity": 3},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "overridden"
    assert decision.json()["approved_quantity"] == 3
    assert db_session.query(AuditEvent).filter_by(action="replenishment.decision_recorded").count() == 1
