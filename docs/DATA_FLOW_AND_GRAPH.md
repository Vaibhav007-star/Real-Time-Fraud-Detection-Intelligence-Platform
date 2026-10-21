# Streaming Feature Engineering & Graph Intelligence Guide

## 1. Streaming Feature Definitions (24 Features)

| Category | Feature Name | Description |
| :--- | :--- | :--- |
| **Velocity** | `tx_count_1m`, `tx_count_5m`, `tx_count_15m`, `tx_count_60m` | Rolling transaction counts for the originating account over 1, 5, 15, and 60 minutes prior to the current event. |
| **Velocity** | `tx_amount_sum_5m`, `tx_amount_sum_60m` | Rolling monetary volume over the last 5 and 60 minutes. |
| **Velocity** | `amount_ratio_vs_avg`, `amount_zscore_vs_account` | Ratio and standard-deviation Z-score of current transaction amount relative to the account's historical completed mean/std. |
| **Velocity** | `seconds_since_prev_tx`, `velocity_burst_ratio` | Elapsed seconds since previous transaction and 1m-vs-60m frequency acceleration ratio. |
| **Behavioral** | `is_unusually_large_amount` | Indicator when amount >= $2,500 or >= 4.5x historical account average (for amounts >= $500). |
| **Behavioral** | `rapid_location_change` | Indicator when geographic region changes within 10 minutes (`<= 600s`) of the previous transaction. |
| **Behavioral** | `is_high_risk_merchant_cat` | Indicator for high-risk merchant categories (`CRYPTO_EXCHANGE`, `LUXURY_JEWELRY`, `HIGH_VALUE_GIFT_CARDS`, `OFFSHORE_GAMING`). |
| **Behavioral** | `is_first_time_device`, `is_first_time_merchant` | Indicators when an established account transacts from a previously unseen device or merchant. |
| **Behavioral** | `recent_failed_attempts_15m`, `failed_then_success_pattern` | Count of declined/failed attempts in the last 15 minutes and card-testing indicator (multiple declines followed by a completed purchase). |
| **Graph** | `device_shared_account_count`, `ip_shared_account_count` | Number of distinct accounts connected to the same `device_id` or `ip_address` subnet. |
| **Graph** | `repeated_transfer_count`, `has_circular_transfer_path` | Repeated directed transfers (`A -> B`) within lookback window and directed transfer cycle indicator (`A -> B -> C -> A`). |
| **Graph** | `local_neighborhood_risk`, `entity_degree_spike` | Damped 1-2 hop neighborhood risk score and 5-minute connection velocity spike on the active device. |

## 2. Public Dataset Provenance & Synthetic Graph Relationships

Public tabular fraud datasets (such as the Kaggle Credit Card Fraud Detection dataset with columns `Time, V1..V28, Amount, Class`) do not natively include `source_account_id`, `device_id`, `ip_address`, or `merchant_id`.
- When uploading such a CSV via `POST /api/datasets/upload`, `CSVDatasetInspector` automatically detects which canonical columns are **genuine** vs. **simulated**.
- Simulated graph identifiers are explicitly prefixed with `SIM-` (`SIM-ACC-...`, `SIM-DEV-...`) and returned in `simulated_graph_fields` along with an explicit `provenance_notice` so synthetic relationships are never misrepresented as discoveries from the raw public dataset.
