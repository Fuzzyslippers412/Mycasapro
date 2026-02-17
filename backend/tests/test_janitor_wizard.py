import pytest
import os
import importlib
import asyncio
from datetime import datetime


@pytest.mark.unit
def test_janitor_audit_wizard_recommendations(monkeypatch):
    from ..agents.janitor import JanitorAgent

    janitor = JanitorAgent()

    audit_result = {
        "timestamp": "2026-02-13T12:00:00",
        "findings": [
            {"severity": "P1", "domain": "database", "finding": "Database disconnected"},
            {"severity": "P2", "domain": "agents", "finding": "Finance agent not running"},
            {"severity": "P3", "domain": "backups", "finding": "Many backups accumulated: 120"},
        ],
        "checks_passed": 3,
        "checks_total": 6,
        "status": "issues_found",
        "health_score": 50,
    }

    connectors_status = {
        "gmail": {"status": "stub", "connected": False, "using_demo": True},
        "whatsapp": {"status": "stub", "connected": False, "using_demo": True},
        "any_connected": False,
        "all_demo": True,
    }

    security_status = {
        "secure": False,
        "dm_policy": "pairing",
        "allow_from": [],
        "issue": "CRITICAL: dmPolicy='pairing' auto-sends messages to strangers!",
    }

    monkeypatch.setattr(janitor, "run_audit", lambda: audit_result)
    monkeypatch.setattr(janitor, "check_connectors", lambda: connectors_status)
    monkeypatch.setattr(janitor, "check_whatsapp_gateway_security", lambda: security_status)
    monkeypatch.setattr(janitor, "_count_backups", lambda: 120)
    monkeypatch.setattr(
        janitor,
        "_get_agent_runtime_states",
        lambda: {"manager": {"state": "running", "error_count": 0}},
    )
    now = datetime.utcnow().isoformat()
    monkeypatch.setattr(
        janitor,
        "_get_inbox_sync_status",
        lambda: {
            "enabled": True,
            "sync_task_running": True,
            "sync_interval_seconds": 900,
            "last_sync_at": now,
            "last_sync_result": {"gmail": 0, "whatsapp": 0, "new": 0},
        },
    )
    monkeypatch.setattr(janitor, "_get_db_maintenance_age_days", lambda: 0)

    result = janitor.run_audit_wizard()

    assert result["summary"]["health_score"] == 50
    assert result["summary"]["findings_count"] == 3

    rec_ids = {rec["id"] for rec in result["recommendations"]}
    assert "cleanup_backups" in rec_ids
    assert "secure_whatsapp_gateway" in rec_ids
    assert "configure_connectors" in rec_ids

    sections = {section["id"]: section for section in result["sections"]}
    assert sections["security"]["status"] == "error"
    assert sections["database"]["status"] == "error"


@pytest.mark.unit
def test_janitor_audit_wizard_all_clear(monkeypatch):
    from ..agents.janitor import JanitorAgent

    janitor = JanitorAgent()

    audit_result = {
        "timestamp": "2026-02-13T12:00:00",
        "findings": [],
        "checks_passed": 6,
        "checks_total": 6,
        "status": "clean",
        "health_score": 100,
    }

    connectors_status = {
        "gmail": {"status": "connected", "connected": True, "using_demo": False},
        "whatsapp": {"status": "connected", "connected": True, "using_demo": False},
        "any_connected": True,
        "all_demo": False,
    }

    security_status = {
        "secure": True,
        "dm_policy": "allowlist",
        "allow_from": ["+15551234567"],
    }

    monkeypatch.setattr(janitor, "run_audit", lambda: audit_result)
    monkeypatch.setattr(janitor, "check_connectors", lambda: connectors_status)
    monkeypatch.setattr(janitor, "check_whatsapp_gateway_security", lambda: security_status)
    monkeypatch.setattr(janitor, "_count_backups", lambda: 10)
    monkeypatch.setattr(
        janitor,
        "_get_agent_runtime_states",
        lambda: {"manager": {"state": "running", "error_count": 0}},
    )
    now = datetime.utcnow().isoformat()
    monkeypatch.setattr(
        janitor,
        "_get_inbox_sync_status",
        lambda: {
            "enabled": True,
            "sync_task_running": True,
            "sync_interval_seconds": 900,
            "last_sync_at": now,
            "last_sync_result": {"gmail": 0, "whatsapp": 0, "new": 0},
        },
    )
    monkeypatch.setattr(janitor, "_get_db_maintenance_age_days", lambda: 0)

    result = janitor.run_audit_wizard()

    assert result["summary"]["health_score"] == 100
    assert result["recommendations"] == []
    for section in result["sections"]:
        assert section["status"] == "ok"


@pytest.mark.unit
def test_janitor_wizard_persists_to_db(monkeypatch, tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'janitor.db'}"

    from ..storage import database as db_module
    importlib.reload(db_module)
    db_module.init_db()

    from ..agents.janitor import JanitorAgent
    janitor = JanitorAgent()

    audit_result = {
        "timestamp": "2026-02-13T12:00:00",
        "findings": [],
        "checks_passed": 6,
        "checks_total": 6,
        "status": "clean",
        "health_score": 100,
    }

    monkeypatch.setattr(janitor, "run_audit", lambda: audit_result)
    monkeypatch.setattr(janitor, "check_connectors", lambda: {"any_connected": True, "all_demo": False})
    monkeypatch.setattr(janitor, "check_whatsapp_gateway_security", lambda: {"secure": True})
    monkeypatch.setattr(janitor, "_count_backups", lambda: 5)
    monkeypatch.setattr(
        janitor,
        "_get_agent_runtime_states",
        lambda: {"manager": {"state": "running", "error_count": 0}},
    )
    now = datetime.utcnow().isoformat()
    monkeypatch.setattr(
        janitor,
        "_get_inbox_sync_status",
        lambda: {
            "enabled": True,
            "sync_task_running": True,
            "sync_interval_seconds": 900,
            "last_sync_at": now,
            "last_sync_result": {"gmail": 0, "whatsapp": 0, "new": 0},
        },
    )
    monkeypatch.setattr(janitor, "_get_db_maintenance_age_days", lambda: 0)

    janitor.run_audit_wizard()

    with db_module.get_db() as db:
        from ..storage.models import JanitorAuditDB
        assert db.query(JanitorAuditDB).count() == 1


def test_janitor_apply_fix_restart_agent():
    from ..agents.janitor import JanitorAgent
    from ..api import system_routes

    system_routes._agent_states["manager"]["state"] = "idle"

    janitor = JanitorAgent()
    result = asyncio.run(janitor.apply_fix("restart_agent", {"agent_id": "manager"}))

    assert result["success"] is True
    assert system_routes._agent_states["manager"]["state"] == "running"
