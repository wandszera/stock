import math

import numpy as np


def calculate_forecast_metrics(actual, predicted) -> dict[str, float]:
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.maximum(np.asarray(predicted, dtype=float), 0)
    errors = actual_values - predicted_values
    absolute_errors = np.abs(errors)
    total_actual = float(np.sum(actual_values))
    served = float(np.minimum(actual_values, predicted_values).sum())
    return {
        "mae": round(float(absolute_errors.mean()), 4),
        "rmse": round(float(math.sqrt(np.mean(errors**2))), 4),
        "wape": round(float(absolute_errors.sum() / total_actual * 100), 4)
        if total_actual > 0
        else 0.0,
        "bias": round(float(np.mean(predicted_values - actual_values)), 4),
        "service_level": round(served / total_actual * 100, 4)
        if total_actual > 0
        else 100.0,
    }
