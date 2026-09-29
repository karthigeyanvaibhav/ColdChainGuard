# ColdChainGuard -- Day 8: Forecasting Report

## Analogue Mapping

| Official Requirement | ColdChainGuard Implementation |
|----------------------|-------------------------------|
| Sales Forecasting (Day 8) | Compliance Rate and Temperature-Excursion Count Forecasting |
| Forecast sales volume per SKU | Forecast weekly fraction of compliant shipments |
| Time-series model | Holt Double Exponential Smoothing (level + trend) |
| Evaluation metric | MAE, RMSE, MAPE on held-out actuals |

**Rationale:** ColdChainGuard processes cold-chain shipments, not retail transactions.
The directly analogous quantity to "weekly sales" is "weekly shipment compliance rate"
and "weekly excursion count" — both are the key operational KPIs that dispatchers
need to forecast for capacity planning and threshold adjustment.

## Dataset

- Weeks of data: 20
- Mean weekly compliance rate: 44.8%
- Mean weekly excursions: 15.8

## Model: Holt Double Exponential Smoothing

Holt's method captures both **level** (current value) and **trend** (direction of change),
making it appropriate for compliance data that can drift week-to-week as route conditions,
product mix, and sensor quality change.

```
Level:  L(t) = alpha * y(t) + (1 - alpha) * (L(t-1) + B(t-1))
Trend:  B(t) = beta  * (L(t) - L(t-1)) + (1 - beta)  * B(t-1)
Forecast(h) = L(t) + h * B(t)
```

## Compliance Rate Forecast (next 4 weeks)

| Week | Predicted Compliance Rate |
|------|--------------------------|
| 2024-05-26 | 42.7% |
| 2024-06-02 | 42.4% |
| 2024-06-09 | 42.1% |
| 2024-06-16 | 41.8% |

Trend: **falling** (from 42.4% actual to 41.8% forecast)

## Forecast Accuracy

| Series | MAE | RMSE | MAPE |
|--------|-----|------|------|
| Compliance Rate | 0.0317 | 0.0390 | 6.8% |
| Excursion Count | 10.1886 | 10.7206 | 65.0% |

## Operational Use

A dispatcher receiving a forecast of rising excursion rates can:
1. Tighten alert thresholds for the affected week
2. Schedule manual checks for high-risk product batches
3. Pre-position replacement vehicles for routes flagged as high-risk by the ML model

## Outputs

- `weekly_actuals.csv` — historical weekly aggregates
- `compliance_forecast.csv` — 4-week compliance rate forecast
- `excursion_forecast.csv` — 4-week excursion count forecast
- `forecast_accuracy.csv` — MAE, RMSE, MAPE
- `forecast_plots/compliance_forecast.png`
- `forecast_plots/excursion_forecast.png`
