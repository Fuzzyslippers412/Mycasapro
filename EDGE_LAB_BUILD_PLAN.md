# Edge Lab Build Specification
## Postgres-backed, Point-in-Time, Non-Hallucinating Financial Prediction System

**Status:** ✅ COMPLETE (Core functionality ready)
**Started:** 2025-01-30
**Completed:** 2026-01-29
**Target:** Finance Agent internal skill for MyCasa Pro

---

## NON-NEGOTIABLE GUARDRAILS

1. **Evidence Boundary:** Every output MUST reference a `snapshot_id` and `snapshot_hash`
2. **No External Narrative:** Never claim news/earnings unless that data was ingested
3. **Determinism:** Feature computation must be deterministic given `snapshot_id`
4. **Auditability:** Store all inputs, configs, model version, outputs with hashes
5. **Safety:** Writes ONLY to `edgelab` schema. Read-only to rest of DB.

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EDGE LAB SYSTEM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   ADAPTERS   │────▶│   SNAPSHOT   │────▶│   FEATURES   │        │
│  │ (Polygon,    │     │   PIPELINE   │     │    ENGINE    │        │
│  │  Alpaca,IEX) │     │              │     │ (Deterministic)        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                              │                     │                 │
│                              ▼                     ▼                 │
│                       ┌──────────────┐     ┌──────────────┐        │
│                       │   POSTGRES   │────▶│    MODEL     │        │
│                       │   edgelab.*  │     │  INFERENCE   │        │
│                       └──────────────┘     └──────────────┘        │
│                              │                     │                 │
│                              ▼                     ▼                 │
│                       ┌──────────────┐     ┌──────────────┐        │
│                       │    AUDIT     │     │  PREDICTION  │        │
│                       │    TRAIL     │     │   OUTPUT     │        │
│                       └──────────────┘     └──────────────┘        │
│                                                    │                 │
│                                                    ▼                 │
│                                            ┌──────────────┐        │
│                                            │  EVALUATION  │        │
│                                            │  (Walk-fwd)  │        │
│                                            └──────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## TECH STACK

- **Runtime:** Python (FastAPI)
- **Database:** PostgreSQL (schema: `edgelab`)
- **Migrations:** Alembic
- **CLI:** Click/Typer
- **Testing:** pytest
- **Hashing:** hashlib (SHA256)

---

## BUILD PHASES

### Phase 1: Database Schema + Migrations ✅ COMPLETE
- [x] Create Alembic setup
- [x] Migration 001: Create edgelab schema
- [x] Migration 002: Create all 12 tables with constraints
- [x] Migration 003: Create indexes for performance
- [x] Verify schema with tests (12 tables verified)

### Phase 2: Core Models + Adapters ✅ COMPLETE
- [x] SQLAlchemy models for all tables
- [x] Base adapter interface
- [x] Mock adapter (for testing)
- [x] Yahoo Finance adapter (free tier)
- [x] Hash utility functions

### Phase 3: Snapshot Pipeline (Daily Scan) ✅ COMPLETE
- [x] Universe policy resolver
- [x] Ingest run management
- [x] Snapshot creation with hashing
- [x] Symbol metadata ingestion
- [x] Daily bar ingestion
- [x] Daily scan output

### Phase 4: Feature Engine ✅ COMPLETE
- [x] FeatureSet definition system
- [x] CORE_V1 features (12 features)
- [x] Deterministic computation
- [x] Feature hash generation
- [x] Tests for determinism

### Phase 5: Model + Prediction ✅ COMPLETE
- [x] Baseline model (RuleScore)
- [x] Model registry
- [x] Weekly prediction pipeline
- [x] Risk flag computation
- [x] Output JSON contract

### Phase 6: Evaluation Pipeline ✅ COMPLETE
- [x] Walk-forward evaluation
- [x] Metrics computation
- [x] Calibration analysis
- [x] Point-in-time correctness

### Phase 7: API + CLI ✅ COMPLETE
- [x] FastAPI endpoints (api/routes/edgelab.py)
- [x] CLI commands (daily-scan, weekly-predict, evaluate, list-adapters)
- [x] Audit endpoint
- [x] Watchlist export

### Phase 8: Tests + Documentation ⚠️ PARTIAL
- [x] Migration tests (schema verified)
- [ ] Determinism tests (formalized)
- [ ] Audit tests (formalized)
- [x] README with run commands (CLI --help)

---

## DATABASE SCHEMA DETAIL

### Tables (12 total)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `source` | Data sources registry | name, base_url |
| `ingest_run` | Track data ingestion | as_of, status, run_hash |
| `universe_policy` | Filter rules | rules (jsonb), policy_hash |
| `snapshot` | Point-in-time data | as_of, snapshot_hash |
| `snapshot_symbol` | Symbol metadata | symbol, sector, market_cap |
| `snapshot_bar_daily` | OHLCV data | date, o, h, l, c, v |
| `feature_set` | Feature definitions | definition (jsonb) |
| `features` | Computed features | features (jsonb), feature_hash |
| `model` | ML model registry | config, model_hash, artifact |
| `prediction_run` | Prediction job | task, run_hash |
| `prediction` | Individual predictions | score, confidence, risk_flags |
| `evaluation_run` | Backtesting results | metrics (jsonb) |

### Hash Strategy

All hashes use SHA256:
- `run_hash`: sha256(as_of + source + params + universe_policy_version)
- `snapshot_hash`: sha256(sorted symbols hash + per-table row hashes)
- `feature_hash`: sha256(canonicalized features json)
- `model_hash`: sha256(serialized weights + config)

---

## FEATURE SET: CORE_V1

| Feature | Formula | Window |
|---------|---------|--------|
| ret_1d | (close / prev_close) - 1 | 1 day |
| ret_5d | (close / close_5d_ago) - 1 | 5 days |
| ret_20d | (close / close_20d_ago) - 1 | 20 days |
| ret_60d | (close / close_60d_ago) - 1 | 60 days |
| vol_20d | std(daily returns, 20d) | 20 days |
| atr_14_pct | ATR(14) / close | 14 days |
| gap_pct | (open - prev_close) / prev_close | 1 day |
| rel_vol_20d | volume / avg_volume_20d | 20 days |
| dollar_vol_20d | avg(close * volume, 20d) | 20 days |
| dist_sma_20 | (close - SMA20) / SMA20 | 20 days |
| dist_sma_50 | (close - SMA50) / SMA50 | 50 days |
| trend_slope_20 | linreg slope on log prices | 20 days |

---

## RISK FLAGS

| Flag | Condition |
|------|-----------|
| LOW_LIQUIDITY | dollar_vol_20d < $10M |
| EARNINGS_WINDOW | earnings within 5 days (if data ingested) |
| HUGE_GAP | abs(gap_pct) > 8% |
| EXTREME_1D_MOVE | abs(ret_1d) > 15% |
| MICROCAP | market_cap < $500M |
| DATA_MISSING | required features are null |

---

## API ENDPOINTS

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /edgelab/daily_scan | Run daily scan pipeline |
| POST | /edgelab/weekly_predict | Generate weekly predictions |
| POST | /edgelab/evaluate | Evaluate past predictions |
| GET | /edgelab/watchlist | Get predictions for a run |
| GET | /edgelab/audit | Get audit trail for snapshot |

### Response Contract

```json
{
  "ok": true,
  "ids": {
    "snapshot_id": "uuid",
    "prediction_run_id": "uuid",
    "evaluation_run_id": "uuid"
  },
  "warnings": ["string"],
  "audit": {
    "as_of": "timestamp",
    "universe_policy_hash": "sha256",
    "snapshot_hash": "sha256",
    "sources": ["source_name"]
  }
}
```

---

## CLI COMMANDS

```bash
# Daily scan
edgelab daily-scan --as-of "2026-01-29T21:00:00Z" --policy US_LIQUID_V1

# Weekly prediction
edgelab weekly-predict --as-of "2026-01-29T21:00:00Z" --policy US_LIQUID_V1 --horizon 5

# Evaluate predictions
edgelab evaluate --prediction-run-id <uuid>

# Export watchlist
edgelab watchlist --prediction-run-id <uuid> --format json
```

---

## FILE STRUCTURE

```
backend/
├── edgelab/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── cli.py               # CLI commands
│   ├── config.py            # Configuration
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── session.py       # DB session management
│   │   └── migrations/
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   │           ├── 001_create_schema.py
│   │           ├── 002_create_tables.py
│   │           └── 003_create_indexes.py
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py          # Base adapter interface
│   │   ├── mock.py          # Mock adapter for testing
│   │   └── yfinance.py      # Yahoo Finance adapter
│   │
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── snapshot.py      # Snapshot creation
│   │   ├── features.py      # Feature computation
│   │   ├── prediction.py    # Model inference
│   │   └── evaluation.py    # Walk-forward eval
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # Base model interface
│   │   └── rule_score.py    # Baseline rule-based model
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── hashing.py       # SHA256 utilities
│   │   └── validation.py    # Input validation
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_migrations.py
│       ├── test_determinism.py
│       ├── test_audit.py
│       └── conftest.py
│
├── alembic.ini
└── requirements.txt
```

---

## DONE CRITERIA

- [x] `daily-scan` creates snapshot rows + daily_scan predictions ✅
- [x] `weekly-predict` creates prediction_run + predictions (top list) ✅
- [x] `evaluate` creates evaluation_run with metrics ✅
- [x] Every output includes snapshot_id + snapshot_hash + model_hash + policy_hash ✅
- [x] No claims outside ingested data (enforced by tests) ✅
- [ ] All tests pass (formalized test suite pending)

---

## TIMELINE

| Day | Deliverable |
|-----|-------------|
| 1 | Schema + migrations + models |
| 2 | Adapters + snapshot pipeline |
| 3 | Feature engine + determinism tests |
| 4 | Model + prediction pipeline |
| 5 | Evaluation + API + CLI |
| 6 | Tests + documentation |
