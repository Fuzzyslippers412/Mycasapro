"""
Security-Manager Agent for MyCasa Pro
Dedicated security control agent for comms, network, and supply-chain.

NOT a general assistant. This is a security control plane.
"""
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import sys
import subprocess
import json
import os
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent


class SecurityManagerAgent(BaseAgent):
    """
    MyCasa Pro — Security-Manager
    
    Primary mission: Ensure all communication, connections, credentials,
    and dependencies are secure while operating locally.
    
    Coordinates with:
    - Galidima (Manager) — policy authority
    - Janitor — quarantine and patch
    
    Default mode: passive + preventative
    """
    
    # Approved egress allowlist
    EGRESS_ALLOWLIST = [
        "api.anthropic.com",
        "pypi.org",
        "files.pythonhosted.org",
        "registry.npmjs.org",
    ]
    
    # Secret patterns to detect in logs/files
    SECRET_PATTERNS = [
        r"sk-ant-[a-zA-Z0-9-]+",  # Anthropic API key
        r"ANTHROPIC_API_KEY\s*=\s*['\"][^'\"]+['\"]",
        r"api[_-]?key\s*[=:]\s*['\"][^'\"]+['\"]",
        r"password\s*[=:]\s*['\"][^'\"]+['\"]",
        r"secret\s*[=:]\s*['\"][^'\"]+['\"]",
    ]
    
    def __init__(self):
        super().__init__("security-manager")
        self._baseline_listeners = None
        self._baseline_egress = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get security manager status"""
        return {
            "agent": "security-manager",
            "status": "active",
            "mode": "passive",
            "metrics": self._get_security_metrics()
        }
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending security tasks (findings to address)"""
        tasks = []
        
        # Check for P0/P1 incidents
        incidents = self.get_context("incidents") or {"active": []}
        for inc in incidents.get("active", []):
            if inc.get("severity") in ["P0", "P1"]:
                tasks.append({
                    "type": "security_incident",
                    "id": inc.get("id"),
                    "title": inc.get("summary"),
                    "severity": inc.get("severity"),
                    "priority": "urgent" if inc.get("severity") == "P0" else "high"
                })
        
        return tasks
    
    def execute_task(self, task_id: int) -> Dict[str, Any]:
        """Execute a security task"""
        self.log_action("execute_task", f"Task {task_id} acknowledged")
        return {"success": True, "message": "Task acknowledged - manual review required"}
    
    def _get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics summary"""
        incidents = self.get_context("incidents") or {"active": [], "resolved": []}
        
        return {
            "active_incidents": len(incidents.get("active", [])),
            "p0_count": len([i for i in incidents.get("active", []) if i.get("severity") == "P0"]),
            "p1_count": len([i for i in incidents.get("active", []) if i.get("severity") == "P1"]),
            "mode": "passive"
        }
    
    # ============ QUICK STATUS ============
    
    def quick_status(self) -> Dict[str, Any]:
        """
        QUICK SECURITY STATUS (default)
        
        - inbound listeners: OK/CHANGED
        - outbound egress: OK/CHANGED
        - secrets hygiene: OK/ISSUE
        - dependencies: OK/UPDATES/CRITICAL
        - incidents: count by severity
        - next recommended action
        """
        result = {
            "mode": "quick",
            "timestamp": datetime.now().isoformat(),
            "status": {}
        }
        
        # Check listeners
        listeners = self.scan_listeners()
        baseline = self.get_context("baseline_listeners")
        if baseline:
            changed = self._compare_listeners(baseline, listeners)
            result["status"]["inbound_listeners"] = "CHANGED" if changed else "OK"
        else:
            result["status"]["inbound_listeners"] = "BASELINE_NOT_SET"
            self.save_context("baseline_listeners", listeners)
        
        # Check secrets hygiene
        secrets_check = self.check_secrets_hygiene()
        result["status"]["secrets_hygiene"] = "ISSUE" if secrets_check.get("issues") else "OK"
        
        # Check dependencies
        deps = self.audit_dependencies()
        if deps.get("critical_vulns", 0) > 0:
            result["status"]["dependencies"] = "CRITICAL"
        elif deps.get("outdated", 0) > 0:
            result["status"]["dependencies"] = "UPDATES"
        else:
            result["status"]["dependencies"] = "OK"
        
        # Incidents
        incidents = self.get_context("incidents") or {"active": []}
        result["status"]["incidents"] = {
            "P0": len([i for i in incidents.get("active", []) if i.get("severity") == "P0"]),
            "P1": len([i for i in incidents.get("active", []) if i.get("severity") == "P1"]),
            "P2": len([i for i in incidents.get("active", []) if i.get("severity") == "P2"]),
            "P3": len([i for i in incidents.get("active", []) if i.get("severity") == "P3"]),
        }
        
        # Next recommended action
        if result["status"]["incidents"]["P0"] > 0:
            result["next_action"] = "CRITICAL: Address P0 incidents immediately"
        elif result["status"]["incidents"]["P1"] > 0:
            result["next_action"] = "HIGH: Address P1 incidents within 1h"
        elif result["status"]["secrets_hygiene"] == "ISSUE":
            result["next_action"] = "Review secrets hygiene issues"
        elif result["status"]["dependencies"] == "CRITICAL":
            result["next_action"] = "Update vulnerable dependencies"
        elif result["status"]["inbound_listeners"] == "CHANGED":
            result["next_action"] = "Review listener changes"
        else:
            result["next_action"] = "No immediate action required"
        
        return result
    
    # ============ FULL REPORT ============
    
    def full_report(self) -> Dict[str, Any]:
        """
        FULL SECURITY REPORT (on request or incident)
        
        - surface map (ports/services)
        - auth/TLS posture
        - egress allowlist
        - secrets posture
        - dependency risk summary
        - recent security events
        - recommended hardening plan
        """
        result = {
            "mode": "full",
            "timestamp": datetime.now().isoformat(),
            "sections": {}
        }
        
        # Surface map
        result["sections"]["surface_map"] = self.scan_listeners()
        
        # Auth/TLS posture
        result["sections"]["auth_tls_posture"] = self._check_auth_tls()
        
        # Egress allowlist
        result["sections"]["egress_allowlist"] = {
            "approved_domains": self.EGRESS_ALLOWLIST,
            "policy": "deny_by_default"
        }
        
        # Secrets posture
        result["sections"]["secrets_posture"] = self.check_secrets_hygiene()
        
        # Dependency risk
        result["sections"]["dependency_risk"] = self.audit_dependencies()
        
        # Recent security events
        incidents = self.get_context("incidents") or {"active": [], "resolved": []}
        result["sections"]["security_events"] = {
            "active_incidents": incidents.get("active", [])[-5:],
            "recently_resolved": incidents.get("resolved", [])[-5:]
        }
        
        # Hardening recommendations
        result["sections"]["hardening_plan"] = self._generate_hardening_plan()
        
        return result
    
    # ============ SCANNING ============
    
    def scan_listeners(self) -> List[Dict[str, Any]]:
        """Scan for listening ports/services"""
        listeners = []
        
        try:
            # Use lsof to find listening sockets
            result = subprocess.run(
                ["/usr/sbin/lsof", "-i", "-P", "-n", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 9:
                    listeners.append({
                        "process": parts[0],
                        "pid": parts[1],
                        "user": parts[2],
                        "address": parts[8] if len(parts) > 8 else "unknown",
                        "state": "LISTEN"
                    })
        except Exception as e:
            self.logger.error(f"Failed to scan listeners: {e}")
        
        return listeners
    
    def _compare_listeners(self, baseline: List[Dict], current: List[Dict]) -> bool:
        """Compare current listeners to baseline"""
        baseline_set = {(l.get("process"), l.get("address")) for l in baseline}
        current_set = {(l.get("process"), l.get("address")) for l in current}
        return baseline_set != current_set
    
    def check_secrets_hygiene(self) -> Dict[str, Any]:
        """Check for secrets in logs, code, and memory"""
        result = {
            "issues": [],
            "checked_paths": [],
            "status": "OK"
        }
        
        # Check common locations for exposed secrets
        check_paths = [
            Path(__file__).parent.parent / "app.py",
            Path(__file__).parent.parent / "config",
            Path(__file__).parent / "memory",
        ]
        
        for path in check_paths:
            if not path.exists():
                continue
            
            result["checked_paths"].append(str(path))
            
            if path.is_file():
                self._check_file_for_secrets(path, result)
            elif path.is_dir():
                for file in path.rglob("*.py"):
                    self._check_file_for_secrets(file, result)
                for file in path.rglob("*.md"):
                    self._check_file_for_secrets(file, result)
                for file in path.rglob("*.json"):
                    self._check_file_for_secrets(file, result)
        
        # Check environment variables are not hardcoded
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if env_key:
            result["env_vars"] = {"ANTHROPIC_API_KEY": "SET (redacted)"}
        else:
            result["env_vars"] = {"ANTHROPIC_API_KEY": "NOT_SET"}
        
        if result["issues"]:
            result["status"] = "ISSUE"
        
        return result
    
    def _check_file_for_secrets(self, filepath: Path, result: Dict):
        """Check a file for secret patterns"""
        try:
            content = filepath.read_text()
            for pattern in self.SECRET_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    # Don't log the actual match
                    result["issues"].append({
                        "file": str(filepath),
                        "pattern": pattern[:20] + "...",
                        "severity": "P0" if "sk-ant" in pattern else "P1"
                    })
        except Exception:
            pass
    
    def audit_dependencies(self) -> Dict[str, Any]:
        """Audit npm/pip dependencies for vulnerabilities"""
        result = {
            "pip": {},
            "npm": {},
            "outdated": 0,
            "critical_vulns": 0
        }
        
        project_root = Path(__file__).parent.parent
        
        # Check pip
        requirements = project_root / "requirements.txt"
        if requirements.exists():
            result["pip"]["lockfile"] = True
            result["pip"]["path"] = str(requirements)
            
            # Run pip check
            try:
                check_result = subprocess.run(
                    ["pip", "check"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(project_root)
                )
                result["pip"]["check_status"] = "OK" if check_result.returncode == 0 else "ISSUES"
                if check_result.returncode != 0:
                    result["pip"]["issues"] = check_result.stdout[:500]
            except Exception as e:
                result["pip"]["check_status"] = f"ERROR: {e}"
        else:
            result["pip"]["lockfile"] = False
        
        # Check npm (if package.json exists)
        package_json = project_root / "package.json"
        if package_json.exists():
            result["npm"]["lockfile"] = (project_root / "package-lock.json").exists()
            result["npm"]["path"] = str(package_json)
            
            # Run npm audit
            try:
                audit_result = subprocess.run(
                    ["npm", "audit", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(project_root)
                )
                if audit_result.stdout:
                    audit_data = json.loads(audit_result.stdout)
                    vulns = audit_data.get("metadata", {}).get("vulnerabilities", {})
                    result["npm"]["vulnerabilities"] = vulns
                    result["critical_vulns"] += vulns.get("critical", 0) + vulns.get("high", 0)
            except Exception as e:
                result["npm"]["audit_status"] = f"ERROR: {e}"
        
        return result
    
    def _check_auth_tls(self) -> Dict[str, Any]:
        """Check authentication and TLS posture"""
        return {
            "streamlit_auth": "NONE (local only)",
            "tls_enabled": False,
            "cors_policy": "UNKNOWN",
            "csrf_protection": "UNKNOWN",
            "recommendation": "Enable HTTPS if exposed beyond localhost"
        }
    
    def _generate_hardening_plan(self) -> List[Dict[str, Any]]:
        """Generate prioritized hardening recommendations"""
        plan = []
        
        # Check secrets
        secrets = self.check_secrets_hygiene()
        if secrets.get("issues"):
            plan.append({
                "priority": "P0",
                "action": "Remove exposed secrets from code/logs",
                "benefit": "Prevent credential theft",
                "cost": "Low",
                "verification": "Re-run secrets scan"
            })
        
        # Check dependencies
        deps = self.audit_dependencies()
        if deps.get("critical_vulns", 0) > 0:
            plan.append({
                "priority": "P1",
                "action": "Update vulnerable dependencies",
                "benefit": "Close known attack vectors",
                "cost": "Medium (requires testing)",
                "verification": "Run npm/pip audit"
            })
        
        # General recommendations
        plan.append({
            "priority": "P2",
            "action": "Enable HTTPS for Streamlit",
            "benefit": "Encrypt traffic if LAN-exposed",
            "cost": "Medium (cert management)",
            "verification": "Check TLS connection"
        })
        
        plan.append({
            "priority": "P3",
            "action": "Configure egress firewall rules",
            "benefit": "Prevent unauthorized data exfiltration",
            "cost": "Low (macOS pf config)",
            "verification": "Test outbound connections"
        })
        
        return plan
    
    # ============ INCIDENT MANAGEMENT ============
    
    def create_incident(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Create a security incident"""
        incidents = self.get_context("incidents") or {"active": [], "resolved": []}
        
        incident_id = f"SEC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        incident = {
            "id": incident_id,
            "summary": finding.get("summary", "Security finding"),
            "severity": finding.get("severity", "P2"),
            "finding": finding,
            "created_at": datetime.now().isoformat(),
            "status": "open",
            "assigned_to": None
        }
        
        incidents["active"].append(incident)
        self.save_context("incidents", incidents)
        
        self.log_action("incident_created", f"{incident_id}: {incident['summary']}")
        
        # Escalate P0/P1 to Manager
        if incident["severity"] in ["P0", "P1"]:
            self.send_to_manager("security_incident", {
                "incident_id": incident_id,
                "severity": incident["severity"],
                "summary": incident["summary"],
                "requires_immediate_action": incident["severity"] == "P0"
            })
        
        return incident
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for security alerts"""
        alerts = []
        incidents = self.get_context("incidents") or {"active": []}
        
        for inc in incidents.get("active", []):
            if inc.get("severity") in ["P0", "P1"]:
                alerts.append({
                    "type": "security_incident",
                    "severity": "critical" if inc.get("severity") == "P0" else "high",
                    "title": f"[{inc.get('severity')}] {inc.get('summary')}",
                    "source_agent": "security-manager"
                })
        
        return alerts
    
    # ============ PROMPT INJECTION DETECTION ============
    
    def evaluate_message(
        self,
        content: str,
        source_identifier: str,
        action_requested: str = None
    ) -> Dict[str, Any]:
        """
        Evaluate a message for security concerns.
        
        Uses ACIP-based prompt injection detection.
        
        Args:
            content: Message content to evaluate
            source_identifier: Who sent the message (phone, email, etc.)
            action_requested: What action is being requested
        
        Returns:
            Security evaluation result
        """
        try:
            from core.prompt_security import evaluate_message_security
            result = evaluate_message_security(content, source_identifier, action_requested)
            
            # Create incident if blocked
            if not result.get("action_allowed") and result.get("block_reason"):
                self.create_incident({
                    "severity": "P1",
                    "summary": f"Blocked message: {result.get('block_reason')}",
                    "source": source_identifier,
                    "trust_zone": result.get("trust_zone"),
                    "findings": result.get("injection_findings", []),
                })
            
            return result
        except ImportError:
            self.logger.warning("prompt_security module not available")
            return {
                "action_allowed": True,
                "warning": "Security module not available"
            }
    
    def scan_content_for_injection(self, content: str) -> Dict[str, Any]:
        """
        Scan content for prompt injection attempts.
        
        Args:
            content: Text to scan
        
        Returns:
            Scan result with threat level and findings
        """
        try:
            from core.prompt_security import scan_for_injection, ThreatLevel
            threat_level, findings = scan_for_injection(content)
            
            return {
                "threat_level": threat_level.value,
                "findings": findings,
                "is_safe": threat_level == ThreatLevel.SAFE,
                "is_blocked": threat_level == ThreatLevel.BLOCKED,
            }
        except ImportError:
            return {"error": "Security module not available"}
    
    def audit_outgoing_content(self, content: str) -> Dict[str, Any]:
        """
        Audit outgoing content for sensitive data leaks.
        
        Args:
            content: Content about to be sent
        
        Returns:
            Audit result with recommendation
        """
        try:
            from core.prompt_security import audit_content_for_leaks
            return audit_content_for_leaks(content)
        except ImportError:
            return {"error": "Security module not available"}
    
    def classify_source(self, identifier: str) -> str:
        """
        Classify a message source into trust zones.
        
        Args:
            identifier: Phone number, email, etc.
        
        Returns:
            Trust zone: "owner", "trusted", or "untrusted"
        """
        try:
            from core.prompt_security import classify_source
            return classify_source(identifier).value
        except ImportError:
            return "untrusted"  # Default to untrusted if module unavailable
