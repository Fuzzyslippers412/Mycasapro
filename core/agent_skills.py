from typing import Dict, List


AGENT_SKILLS: Dict[str, List[str]] = {
    "manager": [
        "Route requests to the right agent",
        "Coordinate handoffs and approvals",
        "Provide on-demand system status and decisions",
    ],
    "maintenance": [
        "Intake and triage maintenance requests",
        "Schedule reminders and seasonal tasks",
        "Track service history and task status",
    ],
    "finance": [
        "Keep bills, budgets, and spending visible",
        "Summarize portfolio and cash flow",
        "Flag due dates and anomalies",
    ],
    "contractors": [
        "Store contractor contacts and quotes",
        "Manage scheduling and follow-ups",
        "Track job status and outcomes",
    ],
    "projects": [
        "Break projects into milestones and steps",
        "Track timelines, dependencies, and scope",
        "Document decisions and progress",
    ],
    "security-manager": [
        "Require approval before sensitive actions",
        "Maintain a clear audit trail",
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
        "Ingest Gmail and WhatsApp into the inbox",
        "Summarize threads and open loops",
        "Tag messages by domain and urgency",
    ],
}


def get_agent_skills(agent_id: str) -> List[str]:
    return list(AGENT_SKILLS.get(agent_id, []))


def get_all_agent_skills() -> Dict[str, List[str]]:
    return {key: list(value) for key, value in AGENT_SKILLS.items()}
