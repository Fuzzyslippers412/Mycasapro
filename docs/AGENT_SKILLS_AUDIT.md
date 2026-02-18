# Agent Skills Audit

This report checks each agent against the expected MyCasa skills.

## manager
- OK: Route requests to the right agent (expected: route_and_execute)
- OK: Coordinate handoffs and approvals (expected: coordinate_team)
- OK: Provide on-demand system status and decisions (expected: quick_status)
- Summary: OK

## mail-skill
- OK: Ingest Gmail and WhatsApp into the inbox (expected: ingest_all, fetch_gmail, fetch_whatsapp)
- OK: Summarize threads and open loops (expected: summarize_threads)
- OK: Tag messages by domain and urgency (expected: _infer_domain_gmail, _infer_domain_whatsapp)
- Summary: OK

## maintenance
- OK: Intake and triage maintenance requests (expected: create_task_from_message)
- OK: Schedule reminders and seasonal tasks (expected: create_task)
- OK: Track service history and task status (expected: list_tasks, get_tasks_from_db)
- Summary: OK

## finance
- OK: Keep bills, budgets, and spending visible (expected: get_bills, get_budget_status, get_spend_summary)
- OK: Summarize portfolio and cash flow (expected: get_portfolio_summary)
- OK: Flag due dates and anomalies (expected: get_upcoming_bills, check_spend_guardrails)
- Summary: OK

## projects
- OK: Break projects into milestones and steps (expected: create_project, add_milestone)
- OK: Track timelines, dependencies, and scope (expected: get_upcoming_milestones)
- OK: Document decisions and progress (expected: update_project, update_project_status)
- Summary: OK

## contractors
- OK: Store contractor contacts and quotes (expected: add_contractor, update_job_details)
- OK: Manage scheduling and follow-ups (expected: schedule_job, get_jobs_needing_action)
- OK: Track job status and outcomes (expected: start_job, complete_job)
- Summary: OK

## security-manager
- OK: Require approval before sensitive actions (expected: request_approval)
- OK: Maintain a clear audit trail (expected: audit_outgoing_content)
- OK: Report risks and mitigation steps (expected: full_report, check_secrets_hygiene)
- Summary: OK

## janitor
- OK: Audit system health and drift (expected: run_audit)
- OK: Run preflight and integrity checks (expected: run_preflight)
- OK: Recommend cleanup and fixes (expected: run_audit_wizard)
- Summary: OK

## backup-recovery
- OK: Run backups and verify integrity (expected: create_backup)
- OK: Track restore points and retention (expected: list_backups)
- OK: Coordinate recovery drills (expected: restore_preview, restore)
- Summary: OK
