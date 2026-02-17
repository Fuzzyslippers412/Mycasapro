# Edge Lab

Postgres-backed, point-in-time, non-hallucinating financial prediction system.

## Non-Negotiable Guardrails

1. **Evidence Boundary**: Every output references `snapshot_id` + `snapshot_hash`
2. **No External Narrative**: No claims without ingested data
3. **Determinism**: Features are pure functions of `snapshot_id`
4. **Auditability**: All inputs/outputs stored with SHA256 hashes
5. **Safety**: Writes ONLY to `edgelab` schema

## Quick Start

### 1. Install Dependencies

```bash
cd backend/edgelab
pip install -r requirements.txt
```

### 2. Set Database URL

```bash
export DATABASE_URL="postgresql://user:pass@localhost/mycasa_pro"
# or
export EDGELAB_DATABASE_URL="postgresql://user:pass@localhost/mycasa_pro"
```

### 3. Initialize Database

```bash
python -m edgelab.cli init-db
```

### 4. Run Daily Scan

```bash
# With mock data (for testing)
python -m edgelab.cli daily-scan \
  --as-of "2026-01-29T21:00:00Z" \
  --policy US_LIQUID_V1 \
  --adapter mock

# With real data (yfinance)
python -m edgelab.cli daily-scan \
  --as-of "2026-01-29T21:00:00Z" \
  --policy US_LIQUID_V1 \
  --adapter yfinance
```

### 5. Run Weekly Prediction

```bash
python -m edgelab.cli weekly-predict \
  --as-of "2026-01-29T21:00:00Z" \
  --policy US_LIQUID_V1 \
  --horizon 5 \
  --output predictions.json
```

### 6. Evaluate Predictions

```bash
python -m edgelab.cli evaluate \
  --prediction-run-id <uuid> \
  --top-n 20
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init-db` | Initialize database schema |
| `daily-scan` | Create snapshot + daily scan predictions |
| `weekly-predict` | Create snapshot + features + weekly predictions |
| `evaluate` | Evaluate a prediction run with walk-forward |
| `list-adapters` | Show available data adapters |

## Database Schema

All tables in `edgelab` schema:

| Table | Purpose |
|-------|---------|
| `source` | Data source registry |
| `universe_policy` | Filter rules |
| `ingest_run` | Data ingestion tracking |
| `snapshot` | Point-in-time data snapshots |
| `snapshot_symbol` | Symbol metadata |
| `snapshot_bar_daily` | Daily OHLCV bars |
| `feature_set` | Feature definitions |
| `features` | Computed features |
| `model` | ML model registry |
| `prediction_run` | Prediction job tracking |
| `prediction` | Individual predictions |
| `evaluation_run` | Backtest results |

## Feature Set: CORE_V1

| Feature | Description |
|---------|-------------|
| `ret_1d` | 1-day return |
| `ret_5d` | 5-day return |
| `ret_20d` | 20-day return |
| `ret_60d` | 60-day return |
| `vol_20d` | 20-day volatility |
| `atr_14_pct` | ATR as % of price |
| `gap_pct` | Overnight gap |
| `rel_vol_20d` | Relative volume |
| `dollar_vol_20d` | Dollar volume |
| `dist_sma_20` | Distance to SMA20 |
| `dist_sma_50` | Distance to SMA50 |
| `trend_slope_20` | Trend slope |

## Risk Flags

| Flag | Trigger |
|------|---------|
| `LOW_LIQUIDITY` | Dollar vol < $10M |
| `HUGE_GAP` | Gap > 8% |
| `EXTREME_1D_MOVE` | 1d move > 15% |
| `MICROCAP` | Market cap < $500M |
| `DATA_MISSING` | Required features null |

## Output Format

All outputs include:

```json
{
  "ok": true,
  "ids": {
    "snapshot_id": "uuid",
    "prediction_run_id": "uuid"
  },
  "audit": {
    "as_of": "timestamp",
    "snapshot_hash": "sha256",
    "policy": "US_LIQUID_V1"
  },
  "warnings": [],
  "candidates": [...]
}
```

## Testing

```bash
# Run all tests
pytest edgelab/tests/

# Run specific tests
pytest edgelab/tests/test_determinism.py -v
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ADAPTERS   │────▶│  SNAPSHOT   │────▶│  FEATURES   │
│ (yfinance,  │     │  PIPELINE   │     │   ENGINE    │
│  mock)      │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  POSTGRES   │────▶│   MODEL     │
                    │  edgelab.*  │     │ INFERENCE   │
                    └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   AUDIT     │     │ EVALUATION  │
                    │   TRAIL     │     │             │
                    └─────────────┘     └─────────────┘
```

## License

Internal use only - MyCasa Pro Finance Agent
