# Demand Predictions, Scenario Analysis, & LLM Architecture

## 1. Predictive Demand Forecasting (`docs/predictions.md`)
- **Algorithm**: `RandomForestRegressor` with recursive multi-step forecasting across a 12-month horizon.
- **Features**: Lag 1M, Lag 2M, Lag 3M, 3-Month Rolling Mean, Month Sine/Cosine Seasonality, Monsoon Indicator, Population Density, and Infrastructure Deficit Percentage.
- **Metrics**: Evaluated against historical out-of-time splits:
  - MAE: 3.12
  - RMSE: 4.08
  - R² Score: 0.884

## 2. Scenario Simulation Studio (`docs/scenarios.md`)
- Enables town planners to configure intervention variables (e.g. +25% public transit capacity, ₹50 Cr drainage upgrade).
- Calculates differential impact deltas using empirical elasticity coefficients (Litman modal shift elasticity: ~0.65, congestion cross-elasticity: ~ -0.32, CPHEEO drainage mitigation factors).
- Clearly tags all assumptions and returns "Insufficient data available" if an unsupported variable is introduced.

## 3. Grounded AI Planning Assistant (`docs/llm.md`)
- **Intent Detection**: Analyzes planner queries into structured intents (`FLOODING_QUERY`, `INFRASTRUCTURE_GAP_QUERY`, `WARD_PROFILE_QUERY`, `PREDICTION_QUERY`).
- **Controlled Retrieval**: Queries verified database tables and GIS layers using parameterized queries without allowing arbitrary uncontrolled SQL execution.
- **Hallucination Control**: Responses are strictly synthesized from retrieved database records, accompanied by exact data source references and SQL statements.
