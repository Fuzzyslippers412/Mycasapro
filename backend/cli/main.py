#!/usr/bin/env python3
"""
MyCasa Pro CLI
Command-line interface for MyCasa Pro backend
"""
import click
import requests
import json
import subprocess
import sys
import os
import time
from pathlib import Path
from datetime import date

API_BASE = os.environ.get("MYCASA_API_URL", "http://localhost:8000")


def api_call(method: str, endpoint: str, data: dict = None) -> dict:
    """Make API call to backend"""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=data)
        elif method == "POST":
            resp = requests.post(url, json=data)
        elif method == "PATCH":
            resp = requests.patch(url, json=data)
        elif method == "PUT":
            resp = requests.put(url, json=data)
        else:
            return {"error": f"Unknown method: {method}"}
        
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Backend not running. Start with: mycasa backend start"}
    except Exception as e:
        return {"error": str(e)}


def print_json(data: dict):
    """Pretty print JSON"""
    click.echo(json.dumps(data, indent=2, default=str))


@click.group()
def cli():
    """MyCasa Pro - Home Operating System CLI"""


# ============ BACKEND ============

@cli.group()
def backend():
    """Backend service management"""


@backend.command("start")
@click.option("--port", default=8000, help="API port")
def backend_start(port: int):
    """Start the backend API server"""
    click.echo(f"Starting MyCasa Pro backend on port {port}...")
    
    backend_dir = Path(__file__).parent.parent
    
    # Start uvicorn
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(port), "--reload"],
        cwd=str(backend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for startup
    time.sleep(2)
    
    # Check health
    result = api_call("GET", "/health")
    if "error" not in result:
        click.echo(f"✓ Backend running at http://localhost:{port}")
        click.echo(f"  Docs: http://localhost:{port}/docs")
    else:
        click.echo(f"✗ Failed to start: {result.get('error')}")


@backend.command("stop")
def backend_stop():
    """Stop the backend API server"""
    click.echo("Stopping MyCasa Pro backend...")
    subprocess.run(["pkill", "-f", "uvicorn.*api.main"], capture_output=True)
    click.echo("✓ Backend stopped")


@backend.command("status")
def backend_status():
    """Check backend status"""
    result = api_call("GET", "/health")
    if "error" in result:
        click.echo(f"✗ Backend offline: {result['error']}")
    else:
        click.echo(f"✓ Backend healthy")
        click.echo(f"  Uptime: {result.get('uptime_seconds', 0):.0f}s")
        click.echo(f"  DB: {result.get('db_status', 'unknown')}")
        click.echo(f"  Active tasks: {result.get('active_tasks', 0)}")
        connectors = result.get("connectors", {})
        click.echo(f"  Gmail: {connectors.get('gmail', 'unknown')}")
        click.echo(f"  WhatsApp: {connectors.get('whatsapp', 'unknown')}")


# ============ UI ============

@cli.group()
def ui():
    """UI management"""


@ui.command("start")
def ui_start():
    """Start the frontend UI"""
    click.echo("Starting MyCasa Pro UI...")
    
    frontend_dir = Path(__file__).parent.parent.parent / "frontend"
    
    if not (frontend_dir / "node_modules").exists():
        click.echo("Installing dependencies...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), capture_output=True)
    
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(3)
    click.echo("✓ UI running at http://localhost:3000")


@ui.command("stop")
def ui_stop():
    """Stop the frontend UI"""
    subprocess.run(["pkill", "-f", "next dev"], capture_output=True)
    click.echo("✓ UI stopped")


# ============ INTAKE ============

@cli.command("intake")
@click.option("--income-name", default="J.P. Morgan Brokerage", help="Primary income source name")
@click.option("--income-type", default="brokerage", help="Account type")
@click.option("--institution", default="J.P. Morgan", help="Institution name")
@click.option("--monthly-limit", default=10000.0, help="Monthly spend limit")
@click.option("--daily-limit", default=150.0, help="Daily spend limit")
@click.option("--system-limit", default=1000.0, help="System cost limit")
def run_intake(income_name, income_type, institution, monthly_limit, daily_limit, system_limit):
    """Complete system intake/setup"""
    click.echo("Running system intake...")
    
    data = {
        "primary_income_source": {
            "name": income_name,
            "account_type": income_type,
            "institution": institution,
            "is_primary": True
        },
        "monthly_spend_limit": monthly_limit,
        "daily_spend_limit": daily_limit,
        "system_cost_limit": system_limit,
        "enable_gmail": True,
        "enable_whatsapp": True,
        "notification_channels": ["whatsapp"]
    }
    
    result = api_call("POST", "/intake", data)
    
    if result.get("status") == "success":
        click.echo("✓ Intake completed successfully")
        if result.get("next_steps"):
            click.echo("Next steps:")
            for step in result["next_steps"]:
                click.echo(f"  - {step}")
    else:
        click.echo(f"✗ Intake failed: {result}")


# ============ TASKS ============

@cli.group()
def tasks():
    """Task management"""


@tasks.command("list")
@click.option("--status", help="Filter by status")
@click.option("--limit", default=20, help="Max results")
def tasks_list(status, limit):
    """List tasks"""
    params = {"limit": limit}
    if status:
        params["status"] = status
    
    result = api_call("GET", "/tasks", params)
    
    if "tasks" in result:
        for task in result["tasks"]:
            status_icon = "✓" if task["status"] == "completed" else "○"
            click.echo(f"{status_icon} [{task['id']}] {task['title']} ({task['status']})")
    else:
        click.echo(f"Error: {result}")


@tasks.command("create")
@click.argument("title")
@click.option("--category", default="general", help="Task category")
@click.option("--priority", default="medium", help="Priority level")
def tasks_create(title, category, priority):
    """Create a new task"""
    data = {
        "title": title,
        "category": category,
        "priority": priority
    }
    
    result = api_call("POST", "/tasks", data)
    
    if result.get("status") == "success":
        click.echo(f"✓ Created task #{result['data']['task_id']}: {title}")
    else:
        click.echo(f"✗ Failed: {result}")


@tasks.command("complete")
@click.argument("task_id", type=int)
@click.option("--evidence", help="Completion evidence")
def tasks_complete(task_id, evidence):
    """Mark a task as complete"""
    params = {}
    if evidence:
        params["evidence"] = evidence
    
    result = api_call("PATCH", f"/tasks/{task_id}/complete", params)
    
    if result.get("status") == "success":
        click.echo(f"✓ Task #{task_id} completed")
    else:
        click.echo(f"✗ Failed: {result}")


# ============ TRANSACTIONS ============

@cli.group()
def transactions():
    """Transaction management"""


@transactions.command("list")
@click.option("--days", default=7, help="Days to look back")
@click.option("--category", help="Filter by category")
def transactions_list(days, category):
    """List transactions"""
    from datetime import timedelta
    
    start = (date.today() - timedelta(days=days)).isoformat()
    params = {"start_date": start, "limit": 50}
    if category:
        params["category"] = category
    
    result = api_call("GET", "/transactions", params)
    
    if "transactions" in result:
        for txn in result["transactions"]:
            click.echo(f"${txn['amount']:>8.2f} | {txn['date']} | {txn['merchant'] or 'Unknown'} | {txn['category'] or 'Uncategorized'}")
    else:
        click.echo(f"Error: {result}")


@transactions.command("summary")
@click.option("--days", default=7, help="Days to summarize")
def transactions_summary(days):
    """Get spending summary"""
    result = api_call("GET", "/transactions/summary", {"days": days})
    
    if "total_spend" in result:
        click.echo(f"Spending Summary ({days} days)")
        click.echo(f"  Total: ${result['total_spend']:,.2f}")
        click.echo(f"  Daily Avg: ${result['avg_daily']:,.2f}")
        click.echo(f"  Transactions: {result['transaction_count']}")
        
        if result.get("by_category"):
            click.echo("\nBy Category:")
            for cat, amount in sorted(result["by_category"].items(), key=lambda x: -x[1]):
                click.echo(f"  {cat}: ${amount:,.2f}")
    else:
        click.echo(f"Error: {result}")


# ============ JOBS ============

@cli.group()
def jobs():
    """Contractor job management"""


@jobs.command("list")
@click.option("--status", help="Filter by status")
def jobs_list(status):
    """List contractor jobs"""
    params = {}
    if status:
        params["status"] = status
    
    result = api_call("GET", "/jobs", params)
    
    if "jobs" in result:
        for job in result["jobs"]:
            cost = f"${job['estimated_cost']:,.2f}" if job.get('estimated_cost') else "TBD"
            click.echo(f"[{job['id']}] {job['description'][:40]} | {job['status']} | {cost}")
    else:
        click.echo(f"Error: {result}")


@jobs.command("create")
@click.argument("description")
@click.option("--contractor", help="Contractor name")
@click.option("--cost", type=float, help="Estimated cost")
def jobs_create(description, contractor, cost):
    """Create a contractor job"""
    data = {
        "description": description,
        "contractor_name": contractor,
        "estimated_cost": cost
    }
    
    result = api_call("POST", "/jobs", data)
    
    if result.get("status") == "success":
        click.echo(f"✓ Created job #{result['data']['job_id']}")
        if result.get("next_steps"):
            click.echo("Next steps:")
            for step in result["next_steps"]:
                click.echo(f"  - {step}")
    else:
        click.echo(f"✗ Failed: {result}")


# ============ COST ============

@cli.group()
def cost():
    """Cost tracking"""


@cost.command("summary")
@click.option("--period", default="month", help="Period: today, month, all")
def cost_summary(period):
    """Get cost summary"""
    result = api_call("GET", "/cost", {"period": period})
    
    if "total_cost" in result:
        click.echo(f"System Cost Summary ({period})")
        click.echo(f"  Total: ${result['total_cost']:.4f}")
        click.echo(f"  Tokens In: {result['total_tokens_in']:,}")
        click.echo(f"  Tokens Out: {result['total_tokens_out']:,}")
        click.echo(f"  Budget Used: {result['budget_used_pct']:.1f}%")
    else:
        click.echo(f"Error: {result}")


@cost.command("budget")
def cost_budget():
    """Check budget status"""
    result = api_call("GET", "/cost/budget")
    
    if "budgets" in result:
        click.echo("Budget Status:")
        for b in result["budgets"]:
            status = "✓" if b["can_proceed"] else "✗"
            click.echo(f"  {status} {b['name']}: ${b['current_spend']:,.2f} / ${b['limit']:,.2f} ({b['pct_used']:.1f}%)")
            for w in b.get("warnings", []):
                click.echo(f"    ⚠ {w}")
    else:
        click.echo(f"Error: {result}")


# ============ BACKUP ============

@cli.group()
def backup():
    """Backup management"""


@backup.command("export")
@click.option("--notes", help="Backup notes")
def backup_export(notes):
    """Export database backup"""
    click.echo("Creating backup...")
    
    data = {}
    if notes:
        data["notes"] = notes
    
    result = api_call("POST", "/backup/export", data)
    
    if result.get("status") == "success":
        click.echo(f"✓ Backup created: {result['data']['filename']}")
        click.echo(f"  Path: {result['data']['path']}")
        click.echo(f"  Size: {result['data']['size_bytes']} bytes")
        click.echo(f"  Checksum: {result['data']['checksum'][:16]}...")
    else:
        click.echo(f"✗ Failed: {result}")


@backup.command("restore")
@click.argument("backup_path")
@click.option("--dry-run", is_flag=True, help="Verify only, don't restore")
def backup_restore(backup_path, dry_run):
    """Restore from backup"""
    click.echo(f"{'Verifying' if dry_run else 'Restoring'} backup...")
    
    data = {
        "backup_path": backup_path,
        "verify_checksum": True,
        "dry_run": dry_run
    }
    
    result = api_call("POST", "/backup/restore", data)
    
    if result.get("status") == "success":
        if dry_run:
            click.echo("✓ Backup verified successfully")
        else:
            click.echo("✓ Backup restored successfully")
        click.echo(f"  Backup ID: {result['data']['backup_id']}")
    else:
        click.echo(f"✗ Failed: {result}")


@backup.command("list")
def backup_list():
    """List available backups"""
    result = api_call("GET", "/backup/list")
    
    if "backups" in result:
        click.echo("Available backups:")
        for b in result["backups"]:
            click.echo(f"  {b['filename']} ({b['size_bytes']} bytes)")
    else:
        click.echo(f"Error: {result}")


# ============ EVENTS ============

@cli.command("events")
@click.option("--limit", default=20, help="Max events")
def show_events(limit):
    """Show recent events"""
    result = api_call("GET", "/events", {"limit": limit})
    
    if "events" in result:
        for event in result["events"]:
            click.echo(f"[{event['timestamp'][:19]}] {event['event_type']}: {event['action']}")
    else:
        click.echo(f"Error: {result}")


# ============ STATUS ============

@cli.command("status")
def show_status():
    """Show full system status"""
    result = api_call("GET", "/status")
    
    if "status" in result:
        click.echo("MyCasa Pro Status")
        click.echo(f"  System: {result['status']}")
        click.echo(f"  Database: {result['db']['status']}")
        click.echo(f"\nTasks:")
        click.echo(f"  Pending: {result['tasks']['pending']}")
        click.echo(f"  In Progress: {result['tasks']['in_progress']}")
        click.echo(f"\nCost ({result['cost'].get('month', 0):.2f} this month):")
        click.echo(f"  Budget: {result['cost']['budget_pct']:.1f}% used")
        click.echo(f"\nBudgets:")
        for b in result.get("budgets", []):
            click.echo(f"  {b['name']}: {b['pct']:.1f}% (${b['current']:,.2f} / ${b['limit']:,.2f})")
    else:
        click.echo(f"Error: {result}")


# ============ JANITOR ============

@cli.group()
def janitor():
    """Janitor agent - system health & maintenance (Salimata ✨)"""


@janitor.command("status")
def janitor_status():
    """Show Janitor agent status"""
    result = api_call("GET", "/api/janitor/status")
    
    if "agent" in result:
        agent = result["agent"]
        metrics = result.get("metrics", {})
        
        click.echo(f"✨ {agent['name']} - {agent['description']}")
        click.echo(f"  Status: {agent['status']}")
        click.echo(f"  Last Audit: {metrics.get('last_audit', 'never')}")
        click.echo(f"  System Health: {metrics.get('system_health', 'unknown')}")
        click.echo(f"  Findings: {metrics.get('findings_count', 0)}")
        click.echo(f"  Recent Edits: {metrics.get('recent_edits', 0)}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("audit")
def janitor_audit():
    """Run a comprehensive system health audit"""
    click.echo("✨ Running system audit...")
    
    result = api_call("GET", "/api/janitor/audit")
    
    if "health_score" in result:
        click.echo(f"\n✨ System Audit Complete")
        click.echo(f"  Health Score: {result['health_score']}%")
        click.echo(f"  Status: {result['status']}")
        click.echo(f"  Checks: {result['checks_passed']}/{result['checks_total']} passed")
        
        if result.get("findings"):
            click.echo(f"\nFindings ({len(result['findings'])}):")
            for f in result["findings"]:
                icon = "🔴" if f["severity"] == "P1" else "🟡" if f["severity"] == "P2" else "🟢"
                click.echo(f"  {icon} [{f['severity']}] {f['domain']}: {f['finding']}")
        else:
            click.echo("\n✅ No issues found!")
    else:
        click.echo(f"Error: {result}")


@janitor.command("cleanup")
@click.option("--days", default=7, help="Keep backups newer than N days")
def janitor_cleanup(days):
    """Clean up old backup files"""
    click.echo(f"✨ Cleaning backups older than {days} days...")
    
    result = api_call("POST", f"/api/janitor/cleanup?days_to_keep={days}", {})
    
    if "deleted" in result:
        click.echo(f"✓ Cleanup complete")
        click.echo(f"  Deleted: {result['deleted']} old backups")
        click.echo(f"  Kept: {result['kept']} recent backups")
        if result.get("errors"):
            click.echo(f"  Errors: {len(result['errors'])}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("history")
@click.option("--limit", default=20, help="Number of edits to show")
def janitor_history(limit):
    """Show recent file edit history"""
    result = api_call("GET", f"/api/janitor/history?limit={limit}")
    
    if "edits" in result:
        if result["edits"]:
            click.echo(f"✨ Recent Edits ({result['total']}):")
            for edit in result["edits"]:
                status = "✓" if edit["success"] else "✗"
                click.echo(f"  {status} {edit['timestamp'][:19]} | {edit['file']} | {edit['agent']}")
        else:
            click.echo("✨ No edit history yet")
    else:
        click.echo(f"Error: {result}")


@janitor.command("connectors")
def janitor_connectors():
    """Check Gmail and WhatsApp connector status"""
    result = api_call("GET", "/api/janitor/connectors")
    
    if "gmail" in result:
        click.echo("✨ Connector Status:")
        click.echo(f"  {result['gmail']['message']}")
        click.echo(f"  {result['whatsapp']['message']}")
        
        if result.get("any_connected"):
            click.echo("\n✅ Real data flowing through connected services")
        elif result.get("all_demo"):
            click.echo("\n📋 All connectors using demo data (configure via Settings)")
    else:
        click.echo(f"Error: {result}")


@janitor.command("backups")
@click.option("--limit", default=20, help="Number of backups to show")
def janitor_backups(limit):
    """List current backup files"""
    result = api_call("GET", f"/api/janitor/backups?limit={limit}")
    
    if "backups" in result:
        if result["backups"]:
            click.echo(f"✨ Backups ({result['count']}):")
            for b in result["backups"]:
                size_kb = b["size_bytes"] / 1024
                click.echo(f"  {b['modified'][:19]} | {size_kb:>7.1f}KB | {b['filename'][:50]}")
        else:
            click.echo("✨ No backup files found")
        click.echo(f"\n  Backup dir: {result.get('backup_dir', 'unknown')}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("logs")
@click.option("--limit", default=20, help="Number of logs to show")
def janitor_logs(limit):
    """Show Janitor activity logs"""
    result = api_call("GET", f"/api/janitor/logs?limit={limit}")
    
    if "logs" in result:
        if result["logs"]:
            click.echo(f"✨ Janitor Activity ({result['count']} logs):")
            for log in result["logs"]:
                status = "✓" if log.get("status") == "success" else "⚠" if log.get("status") == "warning" else "✗"
                click.echo(f"  {status} {log['timestamp'][:19]} | {log['action']}: {log['details'][:50]}")
        else:
            click.echo("✨ No activity logs yet")
    else:
        click.echo(f"Error: {result}")


@janitor.command("review")
@click.argument("file_path")
@click.argument("content_file", type=click.Path(exists=True))
def janitor_review(file_path, content_file):
    """Review a code change before applying it"""
    click.echo(f"✨ Reviewing changes to {file_path}...")
    
    try:
        with open(content_file, 'r') as f:
            new_content = f.read()
    except Exception as e:
        click.echo(f"✗ Could not read content file: {e}")
        return
    
    result = api_call("POST", "/api/janitor/review", {
        "file_path": file_path,
        "new_content": new_content,
    })
    
    if "approved" in result:
        status = "✅ APPROVED" if result["approved"] else "❌ BLOCKED"
        click.echo(f"\n{status}")
        click.echo(f"  Blockers: {result['blocker_count']}")
        click.echo(f"  Warnings: {result['warning_count']}")
        
        if result.get("concerns"):
            click.echo(f"\nConcerns:")
            for c in result["concerns"]:
                icon = "🔴" if c["severity"] == "blocker" else "🟡"
                click.echo(f"  {icon} {c['issue']}")
    else:
        click.echo(f"Error: {result}")


@janitor.command("chat")
@click.argument("message")
def janitor_chat(message):
    """Chat with Salimata (Janitor Agent)"""
    result = api_call("POST", f"/api/janitor/chat?message={message}", {})
    
    if "response" in result:
        click.echo(result["response"])
    else:
        click.echo(f"Error: {result}")


# Entry point
app = cli

if __name__ == "__main__":
    cli()
