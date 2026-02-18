#!/usr/bin/env python3
"""
Audit MyCasa Pro agent skills against expected capabilities.
Outputs a Markdown report to stdout or a file.
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


AGENT_CLASSES: Dict[str, str] = {
    "manager": "agents.manager.ManagerAgent",
    "mail-skill": "agents.mail_skill.MailSkillAgent",
    "maintenance": "agents.maintenance.MaintenanceAgent",
    "finance": "agents.finance.FinanceAgent",
    "projects": "agents.projects.ProjectsAgent",
    "contractors": "agents.contractors.ContractorsAgent",
    "security-manager": "agents.security_manager.SecurityManagerAgent",
    "janitor": "agents.janitor.JanitorAgent",
    "backup-recovery": "agents.backup_recovery.BackupRecoveryAgent",
}


@dataclass
class SkillCheck:
    label: str
    required_methods: List[str]


SKILL_EXPECTATIONS: Dict[str, List[SkillCheck]] = {
    "manager": [
        SkillCheck("Route requests to the right agent", ["route_and_execute"]),
        SkillCheck("Coordinate handoffs and approvals", ["coordinate_team"]),
        SkillCheck("Provide on-demand system status and decisions", ["quick_status"]),
    ],
    "mail-skill": [
        SkillCheck("Ingest Gmail and WhatsApp into the inbox", ["ingest_all", "fetch_gmail", "fetch_whatsapp"]),
        SkillCheck("Summarize threads and open loops", ["summarize_threads"]),
        SkillCheck("Tag messages by domain and urgency", ["_infer_domain_gmail", "_infer_domain_whatsapp"]),
    ],
    "maintenance": [
        SkillCheck("Intake and triage maintenance requests", ["create_task_from_message"]),
        SkillCheck("Schedule reminders and seasonal tasks", ["create_task"]),
        SkillCheck("Track service history and task status", ["list_tasks", "get_tasks_from_db"]),
    ],
    "finance": [
        SkillCheck("Keep bills, budgets, and spending visible", ["get_bills", "get_budget_status", "get_spend_summary"]),
        SkillCheck("Summarize portfolio and cash flow", ["get_portfolio_summary"]),
        SkillCheck("Flag due dates and anomalies", ["get_upcoming_bills", "check_spend_guardrails"]),
    ],
    "projects": [
        SkillCheck("Break projects into milestones and steps", ["create_project", "add_milestone"]),
        SkillCheck("Track timelines, dependencies, and scope", ["get_upcoming_milestones"]),
        SkillCheck("Document decisions and progress", ["update_project", "update_project_status"]),
    ],
    "contractors": [
        SkillCheck("Store contractor contacts and quotes", ["add_contractor", "update_job_details"]),
        SkillCheck("Manage scheduling and follow-ups", ["schedule_job", "get_jobs_needing_action"]),
        SkillCheck("Track job status and outcomes", ["start_job", "complete_job"]),
    ],
    "security-manager": [
        SkillCheck("Require approval before sensitive actions", ["request_approval"]),
        SkillCheck("Maintain a clear audit trail", ["audit_outgoing_content"]),
        SkillCheck("Report risks and mitigation steps", ["full_report", "check_secrets_hygiene"]),
    ],
    "janitor": [
        SkillCheck("Audit system health and drift", ["run_audit"]),
        SkillCheck("Run preflight and integrity checks", ["run_preflight"]),
        SkillCheck("Recommend cleanup and fixes", ["run_audit_wizard"]),
    ],
    "backup-recovery": [
        SkillCheck("Run backups and verify integrity", ["create_backup"]),
        SkillCheck("Track restore points and retention", ["list_backups"]),
        SkillCheck("Coordinate recovery drills", ["restore_preview", "restore"]),
    ],
}


def _module_path_to_file(module_path: str) -> Path:
    rel = Path(*module_path.split(".")).with_suffix(".py")
    return REPO_ROOT / rel


def _class_methods_from_file(file_path: Path, class_name: str) -> Tuple[Optional[List[str]], Optional[str]]:
    if not file_path.exists():
        return None, f"file not found: {file_path}"
    try:
        tree = ast.parse(file_path.read_text())
    except Exception as exc:
        return None, f"parse error: {exc}"
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            methods = [
                n.name
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            return sorted(methods), None
    return None, f"class {class_name} not found"


def _check_methods(
    methods_available: List[str],
    base_methods: List[str],
    required: List[str],
) -> Tuple[bool, List[str]]:
    missing = [m for m in required if m not in methods_available and m not in base_methods]
    return len(missing) == 0, missing


def generate_report() -> str:
    lines: List[str] = []
    lines.append("# Agent Skills Audit")
    lines.append("")
    lines.append("This report checks each agent against the expected MyCasa skills.")
    lines.append("")

    base_file = REPO_ROOT / "agents" / "base.py"
    base_methods, base_error = _class_methods_from_file(base_file, "BaseAgent")
    base_methods = base_methods or []
    if base_error:
        lines.append(f"NOTE: BaseAgent parse error: {base_error}")
        lines.append("")

    for agent_id, class_path in AGENT_CLASSES.items():
        lines.append(f"## {agent_id}")
        module_path, class_name = class_path.rsplit(".", 1)
        file_path = _module_path_to_file(module_path)
        methods, err = _class_methods_from_file(file_path, class_name)
        if err:
            lines.append(f"- Status: ERROR ({err})")
            lines.append("")
            continue
        methods = set(methods or [])
        checks = SKILL_EXPECTATIONS.get(agent_id, [])
        if not checks:
            lines.append("- Status: MISSING (no skill expectations defined)")
            lines.append("")
            continue

        failures = 0
        for check in checks:
            ok, missing = _check_methods(list(methods), base_methods, check.required_methods)
            status = "OK" if ok else "MISSING"
            if not ok:
                failures += 1
            req = ", ".join(check.required_methods) if check.required_methods else "none"
            if missing:
                lines.append(f"- {status}: {check.label} (expected: {req}; missing: {', '.join(missing)})")
            else:
                lines.append(f"- {status}: {check.label} (expected: {req})")

        summary = "OK" if failures == 0 else f"PARTIAL ({failures} missing)"
        lines.append(f"- Summary: {summary}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    output = generate_report()
    if len(sys.argv) > 1:
        out_path = Path(sys.argv[1]).expanduser()
        out_path.write_text(output)
        print(f"Wrote report to {out_path}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
