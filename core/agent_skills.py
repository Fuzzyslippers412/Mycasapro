from typing import Dict, List


AGENT_SKILLS: Dict[str, List[str]] = {
    "manager": [
        "Route requests to the right agent",
        "Summarize system status and decisions",
        "Coordinate approvals and handoffs",
    ],
    "maintenance": [
        "Intake and triage maintenance requests",
        "Schedule and track maintenance tasks",
        "Log service history and reminders",
    ],
    "finance": [
        "Track bills, budgets, and cash flow",
        "Summarize portfolio and spending",
        "Flag due dates and anomalies",
    ],
    "contractors": [
        "Source and track service providers",
        "Manage quotes, scheduling, and follow-ups",
        "Maintain vendor notes and history",
    ],
    "projects": [
        "Plan projects into milestones",
        "Track timelines, dependencies, and scope",
        "Document decisions and progress",
    ],
    "security-manager": [
        "Monitor security signals and alerts",
        "Run checks and incident triage",
        "Report risks and mitigation steps",
    ],
    "janitor": [
        "Audit system health and drift",
        "Run preflight and integrity checks",
        "Recommend cleanup and fixes",
    ],
    "backup-recovery": [
        "Run backups and verify integrity",
        "Track restore points and retention",
        "Coordinate recovery drills",
    ],
    "mail-skill": [
        "Triage inbox and flag priorities",
        "Summarize threads and open loops",
        "Draft replies for approval",
    ],
}


def get_agent_skills(agent_id: str) -> List[str]:
    return list(AGENT_SKILLS.get(agent_id, []))


def get_all_agent_skills() -> Dict[str, List[str]]:
    return {key: list(value) for key, value in AGENT_SKILLS.items()}
