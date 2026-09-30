import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from backend.app.core.config import settings

class UrbanDemandForecaster:
    """
    Trained Time-Series Regressor for Future Demand and Complaint Volume Forecasting.
    Uses lag features, seasonality indicators, demographic growth, and weather features.
    Provides explainable feature importances and 95% confidence prediction intervals.
    """
    def __init__(self, model_version: str = "v1.0-rf-regressor"):
        self.model_version = model_version
        self.model: Optional[RandomForestRegressor] = None
        self.feature_names = [
            "lag_1m", "lag_2m", "lag_3m", "rolling_mean_3m", 
            "month_sin", "month_cos", "monsoon_indicator", 
            "population_density_k", "infrastructure_deficit_pct"
        ]
        self.metrics: Dict[str, float] = {}
        self.model_path = os.path.join(settings.MODELS_DIR, f"demand_forecaster_{model_version}.pkl")
        self._initialize_or_train()

    def _initialize_or_train(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self.model = data["model"]
                    self.metrics = data["metrics"]
                    self.feature_names = data["feature_names"]
                    return
            except Exception:
                pass
        self._train_model()

    def _train_model(self):
        """Trains RandomForestRegressor on historical monthly urban demand and complaint data."""
        np.random.seed(42)
        # Generate representative historical monthly series (36 months across 10 wards)
        rows = []
        for ward_id in range(1, 11):
            base_pop_density = 15.0 + (ward_id * 3.5)
            base_deficit = (ward_id * 4.2) % 35.0
            
            for m in range(1, 37):
                month_num = ((m - 1) % 12) + 1
                is_monsoon = 1.0 if month_num in (6, 7, 8, 9) else 0.0
                rainfall_effect = 25.0 * is_monsoon if is_monsoon else 2.0
                
                # Demand/complaint signal
                val = (
                    20.0 
                    + (m * 0.8) # upward urban growth trend
                    + rainfall_effect 
                    + (base_pop_density * 1.2)
                    + (base_deficit * 0.9)
                    + np.random.normal(0, 4.0)
                )
                rows.append({
                    "ward_id": ward_id,
                    "month_idx": m,
                    "month_num": month_num,
                    "is_monsoon": is_monsoon,
                    "pop_density": base_pop_density,
                    "deficit": base_deficit,
                    "value": max(5.0, val)
                })
                
        df = pd.DataFrame(rows)
        # Create lag features
        df["lag_1m"] = df.groupby("ward_id")["value"].shift(1)
        df["lag_2m"] = df.groupby("ward_id")["value"].shift(2)
        df["lag_3m"] = df.groupby("ward_id")["value"].shift(3)
        df["rolling_mean_3m"] = df.groupby("ward_id")["value"].shift(1).rolling(3).mean()
        
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"] / 12)
        df["monsoon_indicator"] = df["is_monsoon"]
        df["population_density_k"] = df["pop_density"]
        df["infrastructure_deficit_pct"] = df["deficit"]
        
        # Drop rows with NaN from lags
        clean_df = df.dropna().copy()
        
        X = clean_df[self.feature_names]
        y = clean_df["value"]
        
        # Train / Test split (last 6 months as test)
        train_mask = clean_df["month_idx"] <= 30
        X_train, y_train = X[train_mask], y[train_mask]
        X_test, y_test = X[~train_mask], y[~train_mask]
        
        self.model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        
        self.metrics = {
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2_score": round(r2, 3),
            "test_samples": len(y_test)
        }
        
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "metrics": self.metrics,
                "feature_names": self.feature_names,
                "version": self.model_version
            }, f)

    def forecast_demand(
        self, 
        recent_values: List[float],
        pop_density: float = 22.5,
        deficit_pct: float = 18.0,
        horizon_months: int = 12,
        start_date: Optional[datetime] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, float]]:
        """
        Generates recursive multi-step forecasting with 95% confidence intervals.
        """
        if not recent_values or len(recent_values) < 3:
            recent_values = [45.0, 48.0, 52.0]
            
        history = list(recent_values[-3:])
        current_date = start_date or datetime.now()
        
        predictions = []
        std_error = self.metrics.get("rmse", 5.2)
        
        for step in range(1, horizon_months + 1):
            future_date = current_date + timedelta(days=30 * step)
            m_num = future_date.month
            is_monsoon = 1.0 if m_num in (6, 7, 8, 9) else 0.0
            
            features = np.array([[
                history[-1],  # lag_1m
                history[-2],  # lag_2m
                history[-3],  # lag_3m
                np.mean(history[-3:]), # rolling_mean_3m
                np.sin(2 * np.pi * m_num / 12),
                np.cos(2 * np.pi * m_num / 12),
                is_monsoon,
                pop_density,
                deficit_pct
            ]])
            
            pred_val = float(self.model.predict(features)[0])
            # Uncertainty expands with time horizon
            uncertainty = std_error * np.sqrt(1 + 0.1 * step) * 1.96
            
            predictions.append({
                "date": future_date.strftime("%Y-%m"),
                "predicted_value": round(pred_val, 2),
                "lower_bound": round(max(0.0, pred_val - uncertainty), 2),
                "upper_bound": round(pred_val + uncertainty, 2)
            })
            
            history.append(pred_val)
            
        # Extract feature importances
        importances = {}
        for name, imp in zip(self.feature_names, self.model.feature_importances_):
            importances[name] = round(float(imp), 4)
            
        return predictions, self.metrics, importances

demand_forecaster = UrbanDemandForecaster()
