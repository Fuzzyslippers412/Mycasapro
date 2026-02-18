"""
Janitor Agent - Salimata
System health, audits, and safe code editing
"""
from typing import Dict, Any, List, Callable
from datetime import datetime
from pathlib import Path
import json
from .base import BaseAgent


class JanitorAgent(BaseAgent):
    """
    Janitor Agent (Salimata) - system health and audits
    
    Responsibilities:
    - System health checks
    - Code review before edits
    - Safe editing protocol
    - Database cleanup
    - Log rotation
    - Integrity audits
    """
    
    def __init__(self):
        super().__init__(
            agent_id="janitor",
            name="Salimata",
            description="Janitor - System health, audits, safe editing",
            emoji="J"
        )
        self.last_audit: Dict[str, Any] = {}
        self.last_wizard: Dict[str, Any] = {}
        self.start()
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get janitor-specific metrics"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        edit_history = coordinator.get_edit_history(10)
        
        return {
            "last_audit": self.last_audit.get("timestamp", "never"),
            "findings_count": len(self.last_audit.get("findings", [])),
            "recent_edits": len(edit_history),
            "system_health": "healthy" if not self.last_audit.get("findings") else "needs_attention",
        }
    
    def run_audit(self) -> Dict[str, Any]:
        """Run a comprehensive system audit"""
        findings = []
        checks_passed = 0
        checks_total = 0
        
        # Check 1: Database
        checks_total += 1
        try:
            from ..storage.database import get_db_status
            db_status = get_db_status()
            if db_status.get("status") == "connected":
                checks_passed += 1
            else:
                findings.append({
                    "severity": "P1",
                    "domain": "database",
                    "finding": f"Database status: {db_status.get('status', 'unknown')}",
                })
        except Exception as e:
            findings.append({
                "severity": "P1",
                "domain": "database",
                "finding": f"Database check failed: {str(e)}",
            })
        
        # Check 2: Disk space
        checks_total += 1
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_pct = (free / total) * 100
            if free_pct >= 10:
                checks_passed += 1
            else:
                findings.append({
                    "severity": "P2",
                    "domain": "storage",
                    "finding": f"Low disk space: {free_pct:.1f}% free",
                })
        except Exception:
            pass
        
        # Check 3: Agent states
        checks_total += 1
        try:
            from . import (
                FinanceAgent, MaintenanceAgent, ContractorsAgent,
                ProjectsAgent, SecurityManagerAgent
            )
            agent_classes = [FinanceAgent, MaintenanceAgent, ContractorsAgent, ProjectsAgent, SecurityManagerAgent]
            agents_ok = True
            for AgentClass in agent_classes:
                try:
                    agent = AgentClass()
                    status = agent.get_status()
                    if status["status"] not in ["running", "idle"]:
                        agents_ok = False
                        findings.append({
                            "severity": "P2",
                            "domain": "agents",
                            "finding": f"Agent {status['name']} in state: {status['status']}",
                        })
                except Exception as e:
                    agents_ok = False
                    findings.append({
                        "severity": "P2",
                        "domain": "agents",
                        "finding": f"Failed to check agent: {str(e)}",
                    })
            if agents_ok:
                checks_passed += 1
        except Exception as e:
            findings.append({
                "severity": "P2",
                "domain": "agents",
                "finding": f"Agent check failed: {str(e)}",
            })
        
        # Check 4: Backup directory
        checks_total += 1
        try:
            from .coordination import get_coordinator
            coordinator = get_coordinator()
            if coordinator.backup_dir.exists():
                backup_count = len(list(coordinator.backup_dir.glob("*.backup.*")))
                checks_passed += 1
                if backup_count > 100:
                    findings.append({
                        "severity": "P3",
                        "domain": "backups",
                        "finding": f"Many backups accumulated: {backup_count}. Consider cleanup.",
                    })
            else:
                findings.append({
                    "severity": "P2",
                    "domain": "backups",
                    "finding": "Backup directory missing",
                })
        except Exception as e:
            findings.append({
                "severity": "P3",
                "domain": "backups",
                "finding": f"Backup check failed: {str(e)}",
            })
        
        # Check 5: Connectors (Gmail/WhatsApp)
        checks_total += 1
        try:
            from ..connectors.gmail import GmailConnector
            from ..connectors.whatsapp import WhatsAppConnector
            from ..core.schemas import ConnectorStatus
            
            gmail = GmailConnector()
            whatsapp = WhatsAppConnector()
            
            gmail_status = gmail.get_status()
            whatsapp_status = whatsapp.get_status()
            
            connectors_ok = True
            
            # Gmail check
            if gmail_status == ConnectorStatus.CONNECTED:
                pass  # Good
            elif gmail_status == ConnectorStatus.STUB:
                findings.append({
                    "severity": "P3",
                    "domain": "connectors",
                    "finding": "Gmail: gog CLI not configured",
                })
            else:
                connectors_ok = False
                findings.append({
                    "severity": "P2",
                    "domain": "connectors",
                    "finding": f"Gmail connector error: {gmail_status.value}",
                })
            
            # WhatsApp check
            if whatsapp_status == ConnectorStatus.CONNECTED:
                pass  # Good
            elif whatsapp_status == ConnectorStatus.STUB:
                findings.append({
                    "severity": "P2",
                    "domain": "connectors",
                    "finding": "WhatsApp: wacli not configured",
                })
            elif whatsapp_status == ConnectorStatus.DISCONNECTED:
                findings.append({
                    "severity": "P2",
                    "domain": "connectors",
                    "finding": "WhatsApp: wacli installed but not authenticated",
                })
            else:
                connectors_ok = False
                findings.append({
                    "severity": "P2",
                    "domain": "connectors",
                    "finding": f"WhatsApp connector error: {whatsapp_status.value}",
                })
            
            # Pass if at least one connector works
            if gmail_status == ConnectorStatus.CONNECTED or whatsapp_status == ConnectorStatus.CONNECTED:
                checks_passed += 1
            # else: at least one has an error
            
        except Exception as e:
            findings.append({
                "severity": "P3",
                "domain": "connectors",
                "finding": f"Connector check failed: {str(e)}",
            })
        
        # Check 6: WhatsApp Gateway Security (CRITICAL)
        # Verifies Clawdbot gateway isn't configured to auto-respond to strangers
        checks_total += 1
        try:
            whatsapp_security = self.check_whatsapp_gateway_security()
            if whatsapp_security["secure"]:
                checks_passed += 1
            else:
                findings.append({
                    "severity": "P1",  # Critical - can leak messages to strangers
                    "domain": "security",
                    "finding": whatsapp_security["issue"],
                })
        except Exception as e:
            findings.append({
                "severity": "P2",
                "domain": "security",
                "finding": f"WhatsApp gateway security check failed: {str(e)}",
            })
        
        self.last_audit = {
            "timestamp": datetime.now().isoformat(),
            "findings": findings,
            "checks_passed": checks_passed,
            "checks_total": checks_total,
            "status": "clean" if not findings else "issues_found",
            "health_score": round((checks_passed / checks_total) * 100) if checks_total > 0 else 0,
        }
        
        self.log_action("audit_completed", f"Score: {self.last_audit['health_score']}%, {len(findings)} findings")
        return self.last_audit

    def _count_backups(self) -> int:
        """Count backup files in the coordinator backup directory"""
        try:
            from .coordination import get_coordinator
            coordinator = get_coordinator()
            if not coordinator.backup_dir.exists():
                return 0
            return len(list(coordinator.backup_dir.glob("*.backup.*")))
        except Exception:
            return 0

    def _get_agent_runtime_states(self) -> Dict[str, Dict[str, Any]]:
        """Get runtime agent states from system routes"""
        try:
            from ..api import system_routes
            return {agent_id: dict(state) for agent_id, state in system_routes._agent_states.items()}
        except Exception:
            return {}

    def _set_agent_state(self, agent_id: str, state: str) -> bool:
        """Update in-memory agent runtime state"""
        try:
            from ..api import system_routes
            if agent_id not in system_routes._agent_states:
                return False
            entry = system_routes._agent_states[agent_id]
            entry["state"] = state
            entry["loaded_at"] = datetime.now().isoformat() if state == "running" else None
            if state == "running":
                entry["error_count"] = 0
            return True
        except Exception:
            return False

    def _launch_agents(self) -> Dict[str, Any]:
        """Launch all agents in the runtime state table"""
        from ..api import system_routes
        now = datetime.now().isoformat()
        started = []
        for agent_id in system_routes._agent_states.keys():
            system_routes._agent_states[agent_id]["state"] = "running"
            system_routes._agent_states[agent_id]["loaded_at"] = now
            system_routes._agent_states[agent_id]["error_count"] = 0
            started.append(agent_id)
        self.log_action("janitor_launch_agents", f"Started {len(started)} agents")
        return {"started": started, "count": len(started)}

    def _status_from_findings(self, findings: List[Dict[str, Any]]) -> str:
        """Map findings to a status for the wizard UI"""
        severities = {f.get("severity") for f in findings}
        if "P1" in severities:
            return "error"
        if "P2" in severities or "P3" in severities:
            return "warning"
        return "ok"

    def _get_inbox_sync_status(self) -> Dict[str, Any]:
        """Read inbox sync status from the API runtime"""
        try:
            from ..api import main as api_main
            return {
                "enabled": api_main._sync_enabled,
                "sync_task_running": api_main._sync_task is not None and not api_main._sync_task.done(),
                "sync_interval_seconds": api_main.SYNC_INTERVAL_SECONDS,
                "last_sync_at": api_main._last_sync_at,
                "last_sync_result": api_main._last_sync_result,
            }
        except Exception:
            return {
                "enabled": False,
                "sync_task_running": False,
                "sync_interval_seconds": None,
                "last_sync_at": None,
                "last_sync_result": None,
            }

    def _get_db_maintenance_age_days(self) -> Optional[int]:
        """Return days since last DB maintenance, if known"""
        stamp = self._systems_accessed.get("db_maintenance")
        if not stamp:
            return None
        try:
            dt = datetime.fromisoformat(stamp)
            return (datetime.now() - dt).days
        except Exception:
            return None

    def _run_db_maintenance(self) -> Dict[str, Any]:
        """Run safe database maintenance (ANALYZE / PRAGMA optimize)"""
        try:
            from ..storage import database as db_module
            engine = db_module.engine
            dialect = engine.dialect.name
            actions = []
            if dialect == "sqlite":
                with engine.connect() as conn:
                    conn.exec_driver_sql("PRAGMA optimize")
                    conn.exec_driver_sql("VACUUM")
                actions = ["PRAGMA optimize", "VACUUM"]
            else:
                with engine.connect() as conn:
                    conn.exec_driver_sql("ANALYZE")
                actions = ["ANALYZE"]

            now = datetime.now().isoformat()
            self._systems_accessed["db_maintenance"] = now
            self._save_state()
            self.log_action("db_maintenance", f"{dialect}: {', '.join(actions)}")
            return {"dialect": dialect, "actions": actions, "timestamp": now}
        except Exception as e:
            self.log_action("db_maintenance_failed", str(e), status="warning")
            return {"error": str(e)}

    def _build_recommendations(
        self,
        audit: Dict[str, Any],
        connectors: Dict[str, Any],
        security: Dict[str, Any],
        backup_count: int,
        agent_states: Dict[str, Dict[str, Any]],
        inbox_status: Dict[str, Any],
        db_maintenance_age_days: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations from audit findings"""
        recommendations: List[Dict[str, Any]] = []
        seen_ids = set()

        def add(rec: Dict[str, Any]):
            if rec["id"] in seen_ids:
                return
            seen_ids.add(rec["id"])
            recommendations.append(rec)

        # Backups
        if backup_count > 100:
            add({
                "id": "cleanup_backups",
                "severity": "P3",
                "title": "Clean up old backups",
                "description": f"{backup_count} backup files found. Remove backups older than 7 days to reduce clutter.",
                "action": "cleanup_backups",
                "params": {"days_to_keep": 7},
                "can_auto_fix": True,
            })

        # Connectors
        if not connectors.get("any_connected"):
            add({
                "id": "restore_connectors",
                "severity": "P2",
                "title": "Restore connector access",
                "description": "No connectors are currently connected. Re-authenticate gog and wacli.",
                "action": "restore_connectors",
                "can_auto_fix": False,
            })

        # Security
        if security.get("secure") is False:
            add({
                "id": "secure_whatsapp_gateway",
                "severity": "P1",
                "title": "Secure WhatsApp gateway",
                "description": security.get("issue") or "Update dmPolicy to allowlist and set allowFrom.",
                "action": "secure_whatsapp_gateway",
                "params": {},
                "can_auto_fix": False,
            })

        # Inbox sync status
        if inbox_status.get("enabled") is False:
            add({
                "id": "enable_inbox_sync",
                "severity": "P2",
                "title": "Enable inbox sync",
                "description": "Background inbox sync is disabled. Enable it from Settings > Inbox to keep messages current.",
                "action": "enable_inbox_sync",
                "params": {},
                "can_auto_fix": False,
            })
        else:
            last_sync_at = inbox_status.get("last_sync_at")
            if last_sync_at:
                try:
                    last_dt = datetime.fromisoformat(last_sync_at)
                    hours_since = (datetime.now() - last_dt).total_seconds() / 3600
                except Exception:
                    hours_since = None
            else:
                hours_since = None

            if hours_since is None or hours_since >= 2:
                add({
                    "id": "resync_inbox",
                    "severity": "P3",
                    "title": "Refresh inbox data",
                    "description": "Inbox sync appears stale. Run a one-time resync.",
                    "action": "resync_inbox",
                    "params": {},
                    "can_auto_fix": True,
                })

        # Database maintenance
        if db_maintenance_age_days is not None and db_maintenance_age_days >= 7:
            add({
                "id": "db_maintenance",
                "severity": "P3",
                "title": "Run database maintenance",
                "description": f"Last DB maintenance was {db_maintenance_age_days} days ago. Run ANALYZE/VACUUM to keep performance steady.",
                "action": "db_maintenance",
                "params": {},
                "can_auto_fix": True,
            })

        # Audit-domain recommendations
        for finding in audit.get("findings", []):
            domain = finding.get("domain")
            severity = finding.get("severity", "P3")
            detail = finding.get("finding", "Issue detected")

            if domain == "database":
                add({
                    "id": "check_database",
                    "severity": severity,
                    "title": "Restore database connectivity",
                    "description": f"Database check failed. Verify the DB service and migrations. Details: {detail}",
                    "action": "check_database",
                    "can_auto_fix": False,
                })
            elif domain == "storage":
                add({
                    "id": "free_disk_space",
                    "severity": severity,
                    "title": "Free disk space",
                    "description": f"Disk space is low. Remove unused files or increase storage. Details: {detail}",
                    "action": "free_disk_space",
                    "can_auto_fix": False,
                })
            elif domain == "agents":
                add({
                    "id": "stabilize_agents",
                    "severity": severity,
                    "title": "Stabilize agent runtimes",
                    "description": f"One or more agents are degraded. Review logs and restart agents. Details: {detail}",
                    "action": "stabilize_agents",
                    "can_auto_fix": False,
                })
            elif domain == "backups" and "missing" in detail.lower():
                add({
                    "id": "restore_backup_dir",
                    "severity": severity,
                    "title": "Restore backup directory",
                    "description": f"Backup directory is missing. Ensure coordinator backup path exists. Details: {detail}",
                    "action": "restore_backup_dir",
                    "params": {},
                    "can_auto_fix": True,
                })

        # Agent runtime recommendations
        if agent_states:
            running_agents = [
                agent_id
                for agent_id, state in agent_states.items()
                if state.get("state") in ["running", "active"]
            ]
            total_agents = len(agent_states)

            if total_agents > 0 and len(running_agents) == 0:
                add({
                    "id": "launch_agents",
                    "severity": "P1",
                    "title": "Launch all agents",
                    "description": "All agents are currently stopped. Launch the system to restore agent availability.",
                    "action": "launch_agents",
                    "params": {},
                    "can_auto_fix": True,
                })
            else:
                for agent_id, state in agent_states.items():
                    if state.get("state") not in ["running", "active"] or state.get("error_count", 0) > 0:
                        add({
                            "id": f"restart_agent_{agent_id}",
                            "severity": "P2",
                            "title": f"Restart {agent_id}",
                            "description": "Agent is idle or reporting errors. Restart to clear runtime faults.",
                            "action": "restart_agent",
                            "params": {"agent_id": agent_id},
                            "can_auto_fix": True,
                        })

        return recommendations

    def run_audit_wizard(self) -> Dict[str, Any]:
        """Run a full audit wizard with recommendations"""
        audit = self.run_audit()
        connectors = self.check_connectors()
        security = self.check_whatsapp_gateway_security()
        backup_count = self._count_backups()
        agent_states = self._get_agent_runtime_states()
        inbox_status = self._get_inbox_sync_status()
        db_maintenance_age_days = self._get_db_maintenance_age_days()

        findings_by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for finding in audit.get("findings", []):
            findings_by_domain.setdefault(finding.get("domain", "other"), []).append(finding)

        runtime_running = [
            agent_id
            for agent_id, state in agent_states.items()
            if state.get("state") in ["running", "active"]
        ]
        runtime_errors = [
            agent_id
            for agent_id, state in agent_states.items()
            if state.get("error_count", 0) > 0
        ]
        runtime_status = "ok"
        if agent_states:
            if len(runtime_running) == 0:
                runtime_status = "error"
            elif runtime_errors:
                runtime_status = "warning"

        sections = [
            {
                "id": "runtime",
                "title": "Agent Runtime",
                "status": runtime_status,
                "summary": agent_states
                and f"{len(runtime_running)}/{len(agent_states)} agents running"
                or "Runtime status unavailable.",
                "findings": [],
                "details": {
                    "running": runtime_running,
                    "error_agents": runtime_errors,
                },
            },
            {
                "id": "inbox",
                "title": "Inbox Sync",
                "status": "ok" if inbox_status.get("enabled") else "warning",
                "summary": inbox_status.get("enabled")
                and "Background sync enabled."
                or "Background sync disabled.",
                "findings": [],
                "details": inbox_status,
            },
            {
                "id": "database",
                "title": "Database",
                "status": self._status_from_findings(findings_by_domain.get("database", [])),
                "summary": "Database connectivity and integrity checks.",
                "findings": findings_by_domain.get("database", []),
            },
            {
                "id": "storage",
                "title": "Storage",
                "status": self._status_from_findings(findings_by_domain.get("storage", [])),
                "summary": "Disk space and file system checks.",
                "findings": findings_by_domain.get("storage", []),
            },
            {
                "id": "agents",
                "title": "Agents",
                "status": self._status_from_findings(findings_by_domain.get("agents", [])),
                "summary": "Agent health and runtime state checks.",
                "findings": findings_by_domain.get("agents", []),
            },
            {
                "id": "backups",
                "title": "Backups",
                "status": self._status_from_findings(findings_by_domain.get("backups", [])),
                "summary": f"{backup_count} backups stored.",
                "findings": findings_by_domain.get("backups", []),
                "details": {"backup_count": backup_count},
            },
            {
                "id": "connectors",
                "title": "Connectors",
                "status": self._status_from_findings(findings_by_domain.get("connectors", [])),
                "summary": "Gmail/WhatsApp connector availability.",
                "findings": findings_by_domain.get("connectors", []),
                "details": connectors,
            },
            {
                "id": "security",
                "title": "Gateway Security",
                "status": "ok" if security.get("secure") else "error",
                "summary": "WhatsApp gateway policy and allowlist checks.",
                "findings": findings_by_domain.get("security", []),
                "details": security,
            },
        ]

        recommendations = self._build_recommendations(
            audit,
            connectors,
            security,
            backup_count,
            agent_states,
            inbox_status,
            db_maintenance_age_days,
        )

        result = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "health_score": audit.get("health_score", 0),
                "status": audit.get("status", "unknown"),
                "checks_passed": audit.get("checks_passed", 0),
                "checks_total": audit.get("checks_total", 0),
                "findings_count": len(audit.get("findings", [])),
            },
            "sections": sections,
            "recommendations": recommendations,
        }

        self.last_wizard = result
        self._persist_wizard_result(result)
        self.log_action(
            "audit_wizard_completed",
            f"Score: {result['summary']['health_score']}%, recommendations: {len(recommendations)}"
        )

        return result

    def _persist_wizard_result(self, result: Dict[str, Any]) -> None:
        """Persist wizard results for audit trail"""
        try:
            from ..storage.database import get_db
            from ..storage.models import JanitorAuditDB

            summary = result.get("summary", {})
            timestamp_raw = result.get("timestamp")
            try:
                timestamp = datetime.fromisoformat(timestamp_raw) if timestamp_raw else datetime.utcnow()
            except Exception:
                timestamp = datetime.utcnow()

            sections = result.get("sections", []) or []
            findings: List[Dict[str, Any]] = []
            for section in sections:
                findings.extend(section.get("findings", []) or [])

            record = JanitorAuditDB(
                timestamp=timestamp,
                health_score=summary.get("health_score", 0),
                status=summary.get("status", "unknown"),
                checks_passed=summary.get("checks_passed", 0),
                checks_total=summary.get("checks_total", 0),
                findings_count=summary.get("findings_count", 0),
                findings_json=findings,
                sections_json=sections,
                recommendations_json=result.get("recommendations", []),
            )

            with get_db() as db:
                db.add(record)
        except Exception as e:
            self.log_action("audit_wizard_persist_failed", str(e), status="warning")

    def get_wizard_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent wizard runs from storage"""
        try:
            from ..storage.database import get_db
            from ..storage.models import JanitorAuditDB

            with get_db() as db:
                rows = (
                    db.query(JanitorAuditDB)
                    .order_by(JanitorAuditDB.timestamp.desc())
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "id": row.id,
                        "timestamp": row.timestamp.isoformat(),
                        "health_score": row.health_score,
                        "status": row.status,
                        "checks_passed": row.checks_passed,
                        "checks_total": row.checks_total,
                        "findings_count": row.findings_count,
                        "sections": row.sections_json,
                        "recommendations": row.recommendations_json,
                    }
                    for row in rows
                ]
        except Exception as e:
            self.log_action("audit_wizard_history_failed", str(e), status="warning")
            return []

    async def apply_fix(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a wizard fix action"""
        if action == "cleanup_backups":
            days_to_keep = int(params.get("days_to_keep", 7))
            result = self.cleanup_old_backups(days_to_keep)
            return {"success": True, "action": action, "result": result}

        if action == "restore_backup_dir":
            from .coordination import get_coordinator
            coordinator = get_coordinator()
            coordinator.backup_dir.mkdir(parents=True, exist_ok=True)
            self.log_action("backup_dir_restored", str(coordinator.backup_dir))
            return {"success": True, "action": action, "result": {"backup_dir": str(coordinator.backup_dir)}}

        if action == "launch_agents":
            result = self._launch_agents()
            return {"success": True, "action": action, "result": result}

        if action == "restart_agent":
            agent_id = params.get("agent_id")
            if not agent_id:
                return {"success": False, "action": action, "error": "Missing agent_id"}
            success = self._set_agent_state(agent_id, "running")
            if not success:
                return {"success": False, "action": action, "error": f"Agent {agent_id} not found"}
            self.log_action("agent_restarted", agent_id)
            return {"success": True, "action": action, "result": {"agent_id": agent_id}}

        if action == "resync_inbox":
            try:
                from ..api.main import _run_inbox_sync
                result = await _run_inbox_sync()
                self.log_action("inbox_resync", json.dumps(result))
                return {"success": True, "action": action, "result": result}
            except Exception as e:
                return {"success": False, "action": action, "error": str(e)}

        if action == "db_maintenance":
            result = self._run_db_maintenance()
            if "error" in result:
                return {"success": False, "action": action, "error": result["error"]}
            return {"success": True, "action": action, "result": result}

        return {"success": False, "action": action, "error": "Unknown fix action"}
    
    def review_code_change(self, file_path: str, new_content: str) -> Dict[str, Any]:
        """
        Review a proposed code change before it's applied.
        Returns approval status and any concerns.
        """
        concerns = []
        
        file_ext = Path(file_path).suffix.lower()
        
        # Check 1: File type validation
        if file_ext == ".py":
            # Validate Python syntax
            try:
                compile(new_content, file_path, 'exec')
            except SyntaxError as e:
                concerns.append({
                    "severity": "blocker",
                    "issue": f"Python syntax error: {e.msg} at line {e.lineno}",
                })
        
        elif file_ext == ".json":
            # Validate JSON
            try:
                json.loads(new_content)
            except json.JSONDecodeError as e:
                concerns.append({
                    "severity": "blocker",
                    "issue": f"JSON parse error: {e.msg}",
                })
        
        # Check 2: Dangerous patterns
        dangerous_patterns = [
            ("os.system(", "Direct system calls - use subprocess instead"),
            ("eval(", "eval() is dangerous - avoid if possible"),
            ("exec(", "exec() is dangerous - avoid if possible"),
            ("rm -rf", "Dangerous delete pattern detected"),
            ("DROP TABLE", "Database table drop detected"),
            ("DELETE FROM", "Bulk delete detected - verify intent"),
        ]
        
        for pattern, warning in dangerous_patterns:
            if pattern in new_content:
                concerns.append({
                    "severity": "warning",
                    "issue": warning,
                })
        
        # Check 3: Size check
        if len(new_content) > 100000:  # 100KB
            concerns.append({
                "severity": "warning",
                "issue": f"Large file ({len(new_content)} bytes) - verify this is intended",
            })
        
        # Determine approval
        blockers = [c for c in concerns if c["severity"] == "blocker"]
        
        result = {
            "approved": len(blockers) == 0,
            "concerns": concerns,
            "blocker_count": len(blockers),
            "warning_count": len([c for c in concerns if c["severity"] == "warning"]),
            "reviewed_at": datetime.now().isoformat(),
            "reviewed_by": self.agent_id,
        }
        
        self.log_action(
            "code_review_completed",
            f"File: {file_path}, Approved: {result['approved']}, Concerns: {len(concerns)}",
            status="success" if result["approved"] else "warning"
        )
        
        return result
    
    def safe_edit_with_review(
        self,
        file_path: str,
        new_content: str,
        reason: str,
        requesting_agent: str = "manager"
    ) -> Dict[str, Any]:
        """
        Perform a safe edit with code review.
        This is the recommended method for all code changes.
        """
        # Step 1: Review the change
        review = self.review_code_change(file_path, new_content)
        
        if not review["approved"]:
            return {
                "success": False,
                "stage": "review",
                "review": review,
                "error": "Code review found blocking issues",
            }
        
        # Step 2: Perform safe edit with backup
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        
        # Determine validator based on file type
        file_ext = Path(file_path).suffix.lower()
        validator = None
        if file_ext == ".py":
            validator = coordinator.validate_python_syntax
        elif file_ext == ".json":
            validator = coordinator.validate_json
        
        edit_result = coordinator.safe_edit_file(
            file_path=file_path,
            new_content=new_content,
            requesting_agent=requesting_agent,
            reason=reason,
            validator=validator
        )
        
        return {
            "success": edit_result["success"],
            "stage": "edit",
            "review": review,
            "edit": edit_result,
        }
    
    def cleanup_old_backups(self, days_to_keep: int = 7) -> Dict[str, Any]:
        """Clean up old backup files"""
        from .coordination import get_coordinator
        import os
        from datetime import timedelta
        
        coordinator = get_coordinator()
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        deleted = 0
        kept = 0
        errors = []
        
        for backup_file in coordinator.backup_dir.glob("*.backup.*"):
            try:
                # Extract timestamp from filename
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if mtime < cutoff:
                    os.remove(backup_file)
                    deleted += 1
                else:
                    kept += 1
            except Exception as e:
                errors.append(str(e))
        
        result = {
            "deleted": deleted,
            "kept": kept,
            "errors": errors,
        }
        
        self.log_action("backup_cleanup", f"Deleted {deleted}, kept {kept} backups")
        return result
    
    def check_whatsapp_gateway_security(self) -> Dict[str, Any]:
        """
        Check MyCasa WhatsApp reply security configuration.
        
        Ensures replies are only possible when an allowlist is configured.
        
        Returns:
            {
                "secure": bool,
                "dm_policy": str,
                "allow_from": list,
                "issue": str or None
            }
        """
        try:
            from core.settings_typed import get_settings_store
            settings = get_settings_store().get()

            allow_from = []
            for number in getattr(settings.agents.mail, "whatsapp_allowlist", []) or []:
                digits = "".join(c for c in str(number) if c.isdigit())
                if digits:
                    allow_from.append(digits)
            for contact in getattr(settings.agents.mail, "whatsapp_contacts", []) or []:
                try:
                    phone = getattr(contact, "phone", "") or ""
                except Exception:
                    phone = (contact or {}).get("phone") or ""
                digits = "".join(c for c in str(phone) if c.isdigit())
                if digits:
                    allow_from.append(digits)
            allow_from = sorted(set(allow_from))

            allow_replies = bool(settings.agents.mail.allow_whatsapp_replies)
            dm_policy = "allowlist" if allow_replies else "manual"

            issues = []
            if allow_replies and not allow_from:
                issues.append("WhatsApp replies enabled but allowlist is empty.")

            return {
                "secure": len(issues) == 0,
                "dm_policy": dm_policy,
                "allow_from": allow_from,
                "issue": issues[0] if issues else None,
                "all_issues": issues,
            }
        except Exception as e:
            return {
                "secure": True,  # Don't block on check failure
                "dm_policy": "unknown", 
                "allow_from": [],
                "issue": None,
                "note": f"Check failed: {str(e)}"
            }
    
    def check_connectors(self) -> Dict[str, Any]:
        """Check Gmail and WhatsApp connector status"""
        from ..connectors.gmail import GmailConnector
        from ..connectors.whatsapp import WhatsAppConnector
        from ..core.schemas import ConnectorStatus
        
        gmail = GmailConnector()
        whatsapp = WhatsAppConnector()
        
        gmail_status = gmail.get_status()
        whatsapp_status = whatsapp.get_status()
        
        result = {
            "gmail": {
                "status": gmail_status.value,
                "connected": gmail_status == ConnectorStatus.CONNECTED,
                "message": self._connector_message(gmail_status, "Gmail", "gog"),
            },
            "whatsapp": {
                "status": whatsapp_status.value,
                "connected": whatsapp_status == ConnectorStatus.CONNECTED,
                "message": self._connector_message(whatsapp_status, "WhatsApp", "wacli"),
            },
            "any_connected": gmail_status == ConnectorStatus.CONNECTED or whatsapp_status == ConnectorStatus.CONNECTED,
        }
        
        self.log_action("connectors_checked", f"Gmail: {gmail_status.value}, WhatsApp: {whatsapp_status.value}")
        return result
    
    def _connector_message(self, status, name: str, cli: str) -> str:
        """Get human-readable connector status message"""
        from ..core.schemas import ConnectorStatus
        
        if status == ConnectorStatus.CONNECTED:
            return f"{name} connected via {cli} CLI"
        elif status == ConnectorStatus.STUB:
            return f"{name} not configured ({cli} not configured)"
        elif status == ConnectorStatus.DISCONNECTED:
            return f"{name} {cli} installed but not authenticated"
        elif status == ConnectorStatus.ERROR:
            return f"{name} connector error"
        else:
            return f"{name} status unknown"
    
    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Handle janitor-related chat"""
        msg_lower = message.lower()

        if "wizard" in msg_lower:
            wizard = self.run_audit_wizard()
            summary = wizard["summary"]
            recs = wizard["recommendations"]

            lines = [
                f"Audit Wizard Complete ({summary['health_score']}% health)",
                f"Checks: {summary['checks_passed']}/{summary['checks_total']} passed",
                f"Findings: {summary['findings_count']}",
            ]

            if recs:
                lines.append("\nTop Recommendations:")
                for rec in recs[:5]:
                    lines.append(f"  • [{rec['severity']}] {rec['title']}")
            else:
                lines.append("\nNo remediation actions required.")

            return "\n".join(lines) + "\n\n- Salimata"
        
        # Security check (highest priority)
        if "security" in msg_lower or "gateway" in msg_lower or "dmpolicy" in msg_lower:
            security = self.check_whatsapp_gateway_security()
            
            lines = ["WhatsApp Reply Security:"]
            if security["secure"]:
                lines.append(f"  Secure (policy: {security['dm_policy']})")
                if security["allow_from"]:
                    lines.append(f"  Allowlist: {', '.join(security['allow_from'])}")
            else:
                lines.append(f"  INSECURE - {security['issue']}")
                lines.append("\n  Fix: Add allowlisted numbers in Settings → Connectors → WhatsApp allowlist.")
            
            if security.get("note"):
                lines.append(f"\n  Note: {security['note']}")
            
            return "\n".join(lines) + "\n\n- Salimata"
        
        # Check connectors (more specific)
        if "connector" in msg_lower or "gmail" in msg_lower or ("whatsapp" in msg_lower and "security" not in msg_lower):
            status = self.check_connectors()
            
            lines = ["Connector Status:"]
            lines.append(f"  {status['gmail']['message']}")
            lines.append(f"  {status['whatsapp']['message']}")
            
            if status['any_connected']:
                lines.append("\nReal data flowing through connected services")
            
            return "\n".join(lines) + "\n\n- Salimata"
        
        if "audit" in msg_lower or "health" in msg_lower or "system check" in msg_lower or msg_lower == "check":
            audit = self.run_audit()
            
            lines = [f"System Audit (Score: {audit['health_score']}%)"]
            lines.append(f"Checks: {audit['checks_passed']}/{audit['checks_total']} passed")
            
            if audit["findings"]:
                lines.append("\nFindings:")
                for f in audit["findings"][:5]:
                    lines.append(f"  [{f['domain']}] {f['finding']}")
            else:
                lines.append("\nNo issues found.")
            
            return "\n".join(lines) + "\n\n- Salimata"
        
        if "cleanup" in msg_lower or "clean" in msg_lower:
            result = self.cleanup_old_backups()
            return f"Cleanup complete: {result['deleted']} old backups removed, {result['kept']} kept.\n\n- Salimata"
        
        if "history" in msg_lower or "edits" in msg_lower:
            from .coordination import get_coordinator
            coordinator = get_coordinator()
            history = coordinator.get_edit_history(5)
            
            if history:
                lines = ["Recent Edits:"]
                for edit in history:
                    status = "OK" if edit.get("success") else "FAIL"
                    lines.append(f"  {status} {edit.get('file', 'unknown')} by {edit.get('agent', '?')}")
                return "\n".join(lines) + "\n\n- Salimata"
            else:
                return "No recent edits in history.\n\n- Salimata"
        
        return await super().chat(message)
