from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.analytics.supplier_risk import calculate_supplier_risk
from app.models.analytics import SupplierDelivery, SupplierRiskScore
from app.models.audit import AuditEvent


def delivery(*, ordered, expected, delivered, received, defective, cost):
    return SimpleNamespace(
        ordered_at=ordered,
        expected_at=expected,
        delivered_at=delivered,
        received_quantity=received,
        defective_quantity=defective,
        purchase_cost=Decimal(cost),
    )


def test_supplier_risk_exposes_weighted_components_and_raw_metrics():
    records = [
        delivery(
            ordered=date(2026, 1, 1), expected=date(2026, 1, 11),
            delivered=date(2026, 1, 21), received=100, defective=10, cost="800",
        ),
        delivery(
            ordered=date(2026, 2, 1), expected=date(2026, 2, 11),
            delivered=date(2026, 3, 3), received=100, defective=30, cost="800",
        ),
    ]

    result = calculate_supplier_risk(records, store_purchase_cost=2000)

    assert result["score"] == 65.17
    assert result["risk_level"] == "high"
    assert result["delivery_count"] == 2
    assert result["components"]["defects"]["normalized_score"] == 100
    assert result["components"]["raw_metrics"]["purchase_concentration"] == 0.8
    assert "Principais fatores" in result["explanation"]


def test_supplier_intelligence_creates_ranking_and_audit_events(
    client, db_session, auth_headers, store_factory
):
    store = store_factory("Loja Fornecedores")
    headers = auth_headers(
        "manager@supplier.com", "secret123", "manager", store_id=store.id
    )
    headers["X-Request-ID"] = "supplier-run-001"
    deliveries = [
        {
            "supplier_reference": "Fornecedor Critico",
            "ordered_at": "2026-01-01", "expected_at": "2026-01-11",
            "delivered_at": "2026-02-10", "ordered_quantity": 100,
            "received_quantity": 100, "defective_quantity": 20, "purchase_cost": "800.00",
        },
        {
            "supplier_reference": "Fornecedor Estavel",
            "ordered_at": "2026-01-01", "expected_at": "2026-01-11",
            "delivered_at": "2026-01-11", "ordered_quantity": 100,
            "received_quantity": 100, "defective_quantity": 0, "purchase_cost": "200.00",
        },
    ]
    for item in deliveries:
        response = client.post(
            "/supplier-intelligence/deliveries",
            headers=headers,
            json={"store_id": str(store.id), **item},
        )
        assert response.status_code == 201

    response = client.post(
        "/supplier-intelligence/scores/run",
        headers=headers,
        json={"store_id": str(store.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["supplier_reference"] == "Fornecedor Critico"
    assert float(body["items"][0]["score"]) > float(body["items"][1]["score"])
    assert db_session.query(SupplierDelivery).count() == 2
    assert db_session.query(SupplierRiskScore).count() == 2
    events = db_session.query(AuditEvent).filter_by(action="supplier.risk_scored").all()
    assert len(events) == 2
    assert {event.request_id for event in events} == {"supplier-run-001"}

    ranking = client.get(
        "/supplier-intelligence/ranking",
        headers=headers,
        params={"store_id": str(store.id)},
    )
    assert ranking.status_code == 200
    assert ranking.json()["items"][0]["supplier_reference"] == "Fornecedor Critico"


def test_manager_cannot_record_delivery_for_another_store(
    client, auth_headers, store_factory
):
    own_store = store_factory("Loja Propria")
    other_store = store_factory("Outra Loja")
    headers = auth_headers("manager@scope.com", "secret123", "manager", store_id=own_store.id)

    response = client.post(
        "/supplier-intelligence/deliveries",
        headers=headers,
        json={
            "store_id": str(other_store.id), "supplier_reference": "Fornecedor",
            "ordered_at": "2026-01-01", "expected_at": "2026-01-10",
            "delivered_at": "2026-01-10", "ordered_quantity": 10,
            "received_quantity": 10, "defective_quantity": 0, "purchase_cost": "100.00",
        },
    )

    assert response.status_code == 403
