from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.analytics.forecasting import temporal_backtest
from app.analytics.metrics import calculate_forecast_metrics
from app.models.analytics import ForecastBacktestRun
from app.models.audit import AuditEvent
from app.models.sale import Sale, SaleItem


def seed_weekly_sales(db_session, *, store_id, variant_id, quantities):
    start = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)
    for index, quantity in enumerate(quantities):
        sale = Sale(
            store_id=store_id,
            status="completed",
            total_amount=Decimal(quantity * 10),
            discount_amount=Decimal("0"),
            sold_at=start + timedelta(weeks=index),
        )
        db_session.add(sale)
        db_session.flush()
        db_session.add(
            SaleItem(
                sale_id=sale.id,
                variant_id=variant_id,
                quantity=quantity,
                unit_price=Decimal("10"),
                line_total=Decimal(quantity * 10),
            )
        )
    db_session.commit()


def test_forecast_metrics_are_calculated_in_business_units():
    metrics = calculate_forecast_metrics([10, 20], [8, 22])

    assert metrics == {
        "mae": 2.0,
        "rmse": 2.0,
        "wape": 13.3333,
        "bias": 0.0,
        "service_level": 93.3333,
    }


def test_temporal_backtest_uses_only_prior_periods_and_compares_three_models():
    results = temporal_backtest(
        [5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        horizon=1,
        minimum_train_periods=6,
    )

    assert {item["model"] for item in results} == {
        "naive",
        "moving_average_4",
        "exponential_smoothing",
    }
    assert all(item["evaluation_points"] == 4 for item in results)
    assert results[0]["wape"] <= results[-1]["wape"]


def test_backtest_endpoint_persists_model_comparison_and_audit(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Forecast")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=100)
    seed_weekly_sales(
        db_session,
        store_id=store.id,
        variant_id=variant.id,
        quantities=[5, 6, 7, 8, 8, 9, 10, 11, 12, 13, 14, 15],
    )
    headers = auth_headers("manager@forecast.com", "secret123", "manager", store_id=store.id)
    headers["X-Request-ID"] = "forecast-run-001"

    response = client.post(
        "/analytics/backtests",
        headers=headers,
        json={
            "store_id": str(store.id),
            "variant_id": str(variant.id),
            "horizon": 1,
            "minimum_train_periods": 6,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["winner_model"] in {
        "naive", "moving_average_4", "exponential_smoothing"
    }
    assert len(body["results"]) == 3
    assert body["results"][0]["wape"] <= body["results"][-1]["wape"]
    assert db_session.query(ForecastBacktestRun).count() == 1
    event = db_session.query(AuditEvent).filter_by(
        action="analytics.backtest_completed"
    ).one()
    assert event.request_id == "forecast-run-001"


def test_backtest_rejects_series_without_enough_history(
    client, db_session, auth_headers, store_factory, stock_factory
):
    store = store_factory("Loja Historico Curto")
    variant, _ = stock_factory(store_id=store.id, on_hand_qty=10)
    seed_weekly_sales(
        db_session,
        store_id=store.id,
        variant_id=variant.id,
        quantities=[2, 3, 4],
    )
    headers = auth_headers("manager@curto.com", "secret123", "manager", store_id=store.id)

    response = client.post(
        "/analytics/backtests",
        headers=headers,
        json={
            "store_id": str(store.id),
            "variant_id": str(variant.id),
            "minimum_train_periods": 4,
        },
    )

    assert response.status_code == 422
    assert "periodos" in response.json()["detail"]
