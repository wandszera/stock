from collections.abc import Callable

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from app.analytics.metrics import calculate_forecast_metrics


def naive_forecast(train: np.ndarray, horizon: int) -> np.ndarray:
    return np.repeat(train[-1], horizon)


def moving_average_forecast(train: np.ndarray, horizon: int, window: int = 4) -> np.ndarray:
    return np.repeat(float(np.mean(train[-min(window, len(train)) :])), horizon)


def exponential_smoothing_forecast(train: np.ndarray, horizon: int) -> np.ndarray:
    trend = "add" if len(train) >= 6 and np.count_nonzero(train) >= 3 else None
    fitted = ExponentialSmoothing(
        train,
        trend=trend,
        seasonal=None,
        initialization_method="estimated",
    ).fit(optimized=True, remove_bias=True)
    return np.maximum(np.asarray(fitted.forecast(horizon), dtype=float), 0)


MODELS: dict[str, Callable[[np.ndarray, int], np.ndarray]] = {
    "naive": naive_forecast,
    "moving_average_4": moving_average_forecast,
    "exponential_smoothing": exponential_smoothing_forecast,
}


def temporal_backtest(
    values: list[float], *, horizon: int = 1, minimum_train_periods: int = 8
) -> list[dict]:
    series = np.asarray(values, dtype=float)
    if len(series) < minimum_train_periods + horizon:
        raise ValueError(
            f"Sao necessarios pelo menos {minimum_train_periods + horizon} periodos para o backtesting."
        )

    model_observations: dict[str, tuple[list[float], list[float], int]] = {
        name: ([], [], 0) for name in MODELS
    }
    for train_end in range(minimum_train_periods, len(series) - horizon + 1, horizon):
        train = series[:train_end]
        actual = series[train_end : train_end + horizon]
        for name, forecast_function in MODELS.items():
            actuals, predictions, failures = model_observations[name]
            try:
                forecast = forecast_function(train, horizon)
            except Exception:
                failures += 1
                forecast = moving_average_forecast(train, horizon)
            actuals.extend(actual.tolist())
            predictions.extend(forecast.tolist())
            model_observations[name] = (actuals, predictions, failures)

    results = []
    for name, (actuals, predictions, failures) in model_observations.items():
        metrics = calculate_forecast_metrics(actuals, predictions)
        results.append(
            {
                "model": name,
                **metrics,
                "evaluation_points": len(actuals),
                "fallback_count": failures,
            }
        )
    return sorted(results, key=lambda item: (item["wape"], item["rmse"], item["mae"]))
