"""
Session cleanup helpers.
Used to avoid context sharing between MyCasaPro sessions.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def _session_store_path() -> Path:
    from config.settings import DATA_DIR
    return DATA_DIR / "sessions" / "sessions.json"


def _extract_session_id(item: Any) -> str | None:
    if isinstance(item, dict):
        for key in ("id", "session_id", "name"):
            value = item.get(key)
            if isinstance(value, str):
                return value
    return None


def clear_sessions(prefix: str = "mycasa_", clear_all: bool = False) -> Dict[str, Any]:
    """
    Remove session entries by prefix (safe default).
    If clear_all=True, removes all sessions in the store.
    """
    store_path = _session_store_path()
    if not store_path.exists():
        return {
            "success": False,
            "message": "Session store not found",
            "path": str(store_path),
            "removed": 0,
            "total": 0,
        }

    try:
        raw = json.loads(store_path.read_text())
        original_dump = json.dumps(raw, indent=2)
    except Exception as exc:
        return {
            "success": False,
            "message": f"Failed to read session store: {exc}",
            "path": str(store_path),
            "removed": 0,
            "total": 0,
        }

    removed = 0
    total = 0
    updated = raw

    if isinstance(raw, list):
        total = len(raw)
        if clear_all:
            removed = total
            updated = []
        else:
            filtered = []
            for item in raw:
                session_id = _extract_session_id(item) or ""
                if session_id.startswith(prefix):
                    removed += 1
                    continue
                filtered.append(item)
            updated = filtered
    elif isinstance(raw, dict):
        # Try common shapes: {"sessions": [...] } or {"<id>": {...}}
        if "sessions" in raw and isinstance(raw.get("sessions"), list):
            sessions = raw["sessions"]
            total = len(sessions)
            if clear_all:
                removed = total
                raw["sessions"] = []
            else:
                filtered = []
                for item in sessions:
                    session_id = _extract_session_id(item) or ""
                    if session_id.startswith(prefix):
                        removed += 1
                        continue
                    filtered.append(item)
                raw["sessions"] = filtered
            updated = raw
        else:
            keys = list(raw.keys())
            total = len(keys)
            if clear_all:
                removed = total
                updated = {}
            else:
                for key in keys:
                    if key.startswith(prefix):
                        raw.pop(key, None)
                        removed += 1
                updated = raw
    else:
        return {
            "success": False,
            "message": "Unknown session store format",
            "path": str(store_path),
            "removed": 0,
            "total": 0,
        }

    store_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = store_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        backup_path.write_text(original_dump)
    except Exception:
        # Best-effort backup only
        pass

    store_path.write_text(json.dumps(updated, indent=2))

    return {
        "success": True,
        "message": "Sessions cleaned",
        "path": str(store_path),
        "backup_path": str(backup_path),
        "removed": removed,
        "total": total,
        "prefix": prefix,
        "clear_all": clear_all,
    }
