"""Service-demand forecasting.

One panel model per metric (complaint_volume, water_demand_mld, waste_generation_tpd, transit_ridership),
trained on the monthly history stored in service_demand_records across all wards.

Target is scale-free: y / ward_mean, so a single model generalises across large and small wards.
Features: lags 1–3 and 12, 3-month rolling mean, month seasonality (sin/cos), monsoon flag, trend index,
log population density. Model: GradientBoostingRegressor (quantile-free) with residual-based 95 % intervals
that widen with horizon (σ·√h). Backtest: last 6 months of every ward held out.
"""
import logging
import os
import pickle
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score

from backend.app.core.config import settings

logger = logging.getLogger("urban_planning_dss")

MODEL_VERSION = "v2.0-gbr-panel"
METRICS = {
    "complaint_volume": {"label": "Citizen complaints / month", "unit": "complaints"},
    "water_demand_mld": {"label": "Water demand", "unit": "MLD"},
    "waste_generation_tpd": {"label": "Solid waste generation", "unit": "TPD"},
    "transit_ridership": {"label": "Daily public-transit boardings", "unit": "trips/day"},
}
FEATURES = ["lag_1", "lag_2", "lag_3", "lag_12", "roll_3", "month_sin", "month_cos", "monsoon", "trend", "log_density"]
TEST_MONTHS = 6


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def _features(values: List[float], month: int, t: int, log_density: float) -> List[float]:
    return [values[-1], values[-2], values[-3], values[-12] if len(values) >= 12 else values[-1],
            float(np.mean(values[-3:])), np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12),
            1.0 if month in (6, 7, 8, 9) else 0.0, float(t), log_density]


class MetricForecaster:
    def __init__(self, metric: str):
        self.metric = metric
        self.model: Optional[GradientBoostingRegressor] = None
        self.metrics: Dict[str, float] = {}
        self.residual_std: float = 0.1
        self.feature_importance: Dict[str, float] = {}

    def _frame(self, history: Dict[int, Tuple[List[date], List[float], float]]) -> pd.DataFrame:
        rows = []
        for ward_id, (months, values, density) in history.items():
            scale = float(np.mean(values)) or 1.0
            norm = [v / scale for v in values]
            for i in range(12, len(norm)):
                rows.append([ward_id, i, months[i]] + _features(norm[:i], months[i].month, i, np.log1p(density)) + [norm[i]])
        return pd.DataFrame(rows, columns=["ward_id", "t", "month"] + FEATURES + ["y"])

    def fit(self, history: Dict[int, Tuple[List[date], List[float], float]]) -> Dict[str, float]:
        df = self._frame(history)
        if df.empty:
            raise ValueError(f"Not enough history to train {self.metric}")
        cutoff = df["t"].max() - TEST_MONTHS
        train, test = df[df["t"] <= cutoff], df[df["t"] > cutoff]
        params = dict(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, random_state=42)
        model = GradientBoostingRegressor(**params).fit(train[FEATURES].values, train["y"].values)
        pred = model.predict(test[FEATURES].values)
        # Report errors in original units
        scales = {w: float(np.mean(v[1])) or 1.0 for w, v in history.items()}
        s = test["ward_id"].map(scales).values
        y_true, y_pred = test["y"].values * s, pred * s
        naive = test["lag_12"].values * s  # seasonal-naive baseline
        self.metrics = {
            "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
            "mape_pct": round(float(mean_absolute_percentage_error(y_true, y_pred) * 100), 2),
            "r2_score": round(float(r2_score(y_true, y_pred)), 4),
            "seasonal_naive_mape_pct": round(float(mean_absolute_percentage_error(y_true, naive) * 100), 2),
            "test_samples": int(len(test)),
            "train_samples": int(len(train)),
        }
        self.residual_std = float(np.std(test["y"].values - pred)) or 0.05
        self.model = GradientBoostingRegressor(**params).fit(df[FEATURES].values, df["y"].values)  # refit on all data
        self.feature_importance = {f: round(float(v), 4) for f, v in zip(FEATURES, self.model.feature_importances_)}
        return self.metrics

    def forecast(self, months: List[date], values: List[float], density: float, horizon: int) -> List[Dict[str, Any]]:
        scale = float(np.mean(values)) or 1.0
        hist = [v / scale for v in values]
        t0 = len(hist)
        out = []
        for h in range(1, horizon + 1):
            d = _add_months(months[-1], h)
            x = np.array([_features(hist, d.month, t0 + h - 1, np.log1p(density))])
            p = float(self.model.predict(x)[0])
            band = 1.96 * self.residual_std * np.sqrt(h)
            out.append({"date": d.strftime("%Y-%m"), "predicted_value": round(p * scale, 2),
                        "lower_bound": round(max(0.0, (p - band) * scale), 2), "upper_bound": round((p + band) * scale, 2)})
            hist.append(p)
        return out


class UrbanDemandForecaster:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_version = MODEL_VERSION
        self.model_dir = model_dir or settings.MODELS_DIR
        self.model_path = os.path.join(self.model_dir, f"demand_forecaster_{MODEL_VERSION}.pkl")
        self.models: Dict[str, MetricForecaster] = {}
        self.trained_at: Optional[str] = None

    def train(self, histories: Dict[str, Dict[int, Tuple[List[date], List[float], float]]]) -> Dict[str, Dict[str, float]]:
        results = {}
        for metric, hist in histories.items():
            mf = MetricForecaster(metric)
            results[metric] = mf.fit(hist)
            self.models[metric] = mf
            logger.info("Forecaster %s: MAPE %.2f%% (seasonal naive %.2f%%)", metric,
                        results[metric]["mape_pct"], results[metric]["seasonal_naive_mape_pct"])
        self.trained_at = datetime.now(timezone.utc).isoformat()
        os.makedirs(self.model_dir, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({"models": self.models, "trained_at": self.trained_at, "sklearn_version": sklearn.__version__}, f)
        return results

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            return False
        try:
            with open(self.model_path, "rb") as f:
                data = pickle.load(f)
            if data.get("sklearn_version") != sklearn.__version__:
                return False
            self.models, self.trained_at = data["models"], data["trained_at"]
            return True
        except Exception as exc:
            logger.warning("Could not load forecaster (%s)", exc)
            return False

    def is_ready(self, metric: str) -> bool:
        return metric in self.models


_forecaster: Optional[UrbanDemandForecaster] = None


def get_forecaster() -> UrbanDemandForecaster:
    global _forecaster
    if _forecaster is None:
        _forecaster = UrbanDemandForecaster()
        _forecaster.load()
    return _forecaster


def reset_forecaster() -> None:
    global _forecaster
    _forecaster = None
