# Forecasting, scenarios & recommendations

## Demand forecasting (`backend/app/forecasting/demand_model.py`)

- One **panel** GradientBoostingRegressor per metric: `complaint_volume` (aggregated from complaints), `water_demand_mld`, `waste_generation_tpd`, `transit_ridership`.
- Target: value ÷ ward mean (scale-free).
- Features: lags 1 / 2 / 3 / 12, 3-month rolling mean, month sin / cos, monsoon flag, trend, log density.
- Back-test: last 6 months of every ward, compared with a seasonal-naive baseline. Residual σ gives 95 % intervals widening with √h.
- City forecasts are sums of ward forecasts, with intervals combined in quadrature.
- Seeded results: water MAPE 1.3 % (naive 1.7 %), waste 2.1 % (3.4 %), ridership 2.8 % (3.9 %), complaints 23 % (26 %). Monthly complaint counts are small and noisy.

**Future infrastructure demand** (`/predictions/infrastructure-demand?target_year=`): Census 2011 population projected with the 2001–11 CAGR, then converted to norm-based requirements minus existing supply.

## Scenarios (`backend/app/scenarios/engine.py`)

The baseline is aggregated from the database for the city or selected wards. Lever effects:

| Lever | Effect |
|---|---|
| Transit capacity % | ridership × (1 + 0.65·Δ); congestion excess × (1 − 0.32·Δ) (Litman / VTPI) |
| New bus stops | ridership access elasticity 0.3 |
| Drainage upgrade % of gap | capacity added; flood risk × (1 − 0.6 × share of gap closed) |
| Green cover (percentage points) | lower runoff coefficient; flood risk −1.5 % per point |
| Population growth / rezoning | demand at CPHEEO / MoHUA norms; congestion ∝ √population |
| Water MLD, waste %, clinics, schools | direct supply additions |

**Score:** a weighted mean of eight adequacy criteria (0–100), where each criterion is supply ÷ norm, clipped to 1:

| Criterion | Weight |
|---|---|
| Water | 15 |
| Drainage | 15 |
| Flood safety | 15 |
| Mobility | 13 |
| Health | 12 |
| Waste | 10 |
| Schools | 10 |
| Open space | 10 |

Capital cost uses the indicative unit rates in `analytics/norms.py`. `/scenarios/compare` ranks 2–4 scenarios and adds a narrative (LLM when configured).

## Recommendations (`backend/app/recommendations/engine.py`)

**Ward priority:** min-max normalised MCDA across wards.

| Criterion | Weight |
|---|---|
| Complaints per 1,000 residents | 25 % |
| Confidence-weighted mean deficit | 25 % |
| Density | 20 % |
| Flood exposure (DEM + imperviousness + flood complaints) | 15 % |
| Forecast demand growth | 15 % |

**Interventions:** one for every CRITICAL / HIGH gap, scored as follows. Low-confidence gaps are multiplied by 0.6 and carry a verification caveat.

| Component | Weight |
|---|---|
| Severity × data-confidence factor | 35 % |
| Population affected | 25 % |
| Sector complaint pressure | 20 % |
| Growth pressure | 20 % |
