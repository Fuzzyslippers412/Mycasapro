"""
Hashing utilities for Edge Lab

All hashes use SHA256 for auditability and determinism.
Canonicalization ensures identical inputs produce identical hashes.
"""

import hashlib
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID


def canonicalize(obj: Any) -> str:
    """
    Convert object to canonical string representation for hashing.
    
    Rules:
    - Dicts: sorted by key, recursively canonicalized
    - Lists: elements canonicalized in order
    - Decimals: converted to string with consistent precision
    - Datetimes: ISO format
    - UUIDs: string representation
    - None: literal "null"
    """
    if obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, Decimal):
        # Normalize to remove trailing zeros
        return str(obj.normalize())
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        items = sorted((k, canonicalize(v)) for k, v in obj.items())
        return "{" + ",".join(f"{k}:{v}" for k, v in items) + "}"
    elif isinstance(obj, (list, tuple)):
        return "[" + ",".join(canonicalize(v) for v in obj) + "]"
    else:
        return str(obj)


def compute_hash(data: str) -> str:
    """Compute SHA256 hash of string data"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_json_hash(obj: Any) -> str:
    """Compute SHA256 hash of canonicalized JSON object"""
    canonical = canonicalize(obj)
    return compute_hash(canonical)


def compute_run_hash(
    as_of: datetime,
    source_id: UUID,
    params: Dict[str, Any],
    universe_policy_version: int
) -> str:
    """
    Compute hash for an ingest run.
    
    Hash of: {as_of, source_id, params, universe_policy_version}
    """
    data = {
        "as_of": as_of.isoformat(),
        "source_id": str(source_id),
        "params": params,
        "universe_policy_version": universe_policy_version,
    }
    return compute_json_hash(data)


def compute_snapshot_hash(
    symbols: List[str],
    symbol_hashes: Dict[str, str],
    bar_hashes: Dict[str, str],
) -> str:
    """
    Compute hash for a snapshot.
    
    Hash of: sorted symbols + per-symbol metadata hash + per-symbol bar hash
    """
    data = {
        "symbols": sorted(symbols),
        "symbol_hashes": {k: symbol_hashes.get(k, "") for k in sorted(symbols)},
        "bar_hashes": {k: bar_hashes.get(k, "") for k in sorted(symbols)},
    }
    return compute_json_hash(data)


def compute_symbol_hash(symbol_data: Dict[str, Any]) -> str:
    """Compute hash for symbol metadata"""
    return compute_json_hash(symbol_data)


def compute_bars_hash(bars: List[Dict[str, Any]]) -> str:
    """Compute hash for a symbol's bar data"""
    # Sort bars by date
    sorted_bars = sorted(bars, key=lambda x: x.get("date", ""))
    return compute_json_hash(sorted_bars)


def compute_feature_hash(features: Dict[str, Any]) -> str:
    """Compute hash for computed features"""
    return compute_json_hash(features)


def compute_model_hash(config: Dict[str, Any], weights_hash: Optional[str] = None) -> str:
    """
    Compute hash for a model.
    
    Hash of: config + weights hash (if available)
    """
    data = {
        "config": config,
        "weights_hash": weights_hash or "none",
    }
    return compute_json_hash(data)


def compute_prediction_run_hash(
    snapshot_hash: str,
    model_hash: str,
    params: Dict[str, Any]
) -> str:
    """
    Compute hash for a prediction run.
    
    Hash of: snapshot_hash + model_hash + params
    """
    data = {
        "snapshot_hash": snapshot_hash,
        "model_hash": model_hash,
        "params": params,
    }
    return compute_json_hash(data)


def compute_evaluation_hash(
    prediction_run_id: UUID,
    evaluated_at: datetime
) -> str:
    """
    Compute hash for an evaluation run.
    
    Hash of: prediction_run_id + evaluated_at
    """
    data = {
        "prediction_run_id": str(prediction_run_id),
        "evaluated_at": evaluated_at.isoformat(),
    }
    return compute_json_hash(data)


def compute_policy_hash(rules: Dict[str, Any]) -> str:
    """Compute hash for universe policy rules"""
    return compute_json_hash(rules)


def compute_feature_set_hash(definition: Dict[str, Any]) -> str:
    """Compute hash for feature set definition"""
    return compute_json_hash(definition)
