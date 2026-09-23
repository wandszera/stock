from app.analytics.scenarios import simulate_replenishment_scenario


def test_scenario_compares_stockout_policies_under_demand_and_delay():
    result = simulate_replenishment_scenario(
        [{"variant_id": "a", "forecast_quantity": 10, "forecast_model": "naive", "current_quantity": 5, "unit_cost": 2}],
        demand_multiplier=1.5, supplier_delay_weeks=1, lead_time_weeks=1,
        minimum_stock=5, budget_limit=None,
    )

    item = result[0]
    assert item["effective_lead_time_weeks"] == 2
    assert item["current_policy_stockout"] == 25
    assert item["simple_rule_stockout"] == 0
    assert item["model_stockout"] == 0


def test_scenario_budget_can_leave_residual_stockout():
    result = simulate_replenishment_scenario(
        [{"variant_id": "a", "forecast_quantity": 10, "forecast_model": "naive", "current_quantity": 0, "unit_cost": 10}],
        demand_multiplier=1, supplier_delay_weeks=0, lead_time_weeks=2,
        minimum_stock=5, budget_limit=100,
    )

    assert result[0]["recommended_quantity"] == 10
    assert result[0]["model_stockout"] == 10
