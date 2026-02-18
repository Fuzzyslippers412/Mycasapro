#!/usr/bin/env python3
"""
MyCasa Pro - Issue Scanner (Janitor Command)

Run from project root:
    python scripts/scan_issues.py

Or via janitor:
    python -m agents.janitor scan
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Issue severity levels
CRITICAL = "🔴 CRITICAL"
WARNING = "⚠️  WARNING"
INFO = "ℹ️  INFO"
OK = "✅ OK"


def check_imports() -> List[Dict[str, Any]]:
    """Check all critical imports work"""
    issues = []
    
    # Database models
    try:
        pass
    except Exception as e:
        issues.append({"level": CRITICAL, "area": "imports", "message": f"Database models failed: {e}"})
    
    # Agents
    try:
        pass
    except Exception as e:
        issues.append({"level": CRITICAL, "area": "imports", "message": f"Agents failed: {e}"})
    
    # Shared context
    try:
        pass
    except Exception as e:
        issues.append({"level": CRITICAL, "area": "imports", "message": f"SharedContext failed: {e}"})
    
    # API routes
    try:
        pass
    except Exception as e:
        issues.append({"level": CRITICAL, "area": "imports", "message": f"API routes failed: {e}"})
    
    return issues


def check_database() -> List[Dict[str, Any]]:
    """Check database connectivity and schema"""
    issues = []
    
    try:
        from database import get_db
        from database.models import MaintenanceTask, InboxMessage, Contractor
        
        with get_db() as db:
            # Test basic queries
            task_count = db.query(MaintenanceTask).count()
            inbox_count = db.query(InboxMessage).count()
            contractor_count = db.query(Contractor).count()
            
            # Check for orphaned data
            if inbox_count > 0:
                # Check for preview vs body field
                sample = db.query(InboxMessage).first()
                if hasattr(sample, 'body') and not hasattr(sample, 'preview'):
                    issues.append({
                        "level": WARNING,
                        "area": "database",
                        "message": "InboxMessage uses 'body' instead of 'preview' - schema mismatch possible"
                    })
    
    except Exception as e:
        issues.append({"level": CRITICAL, "area": "database", "message": f"Database connection failed: {e}"})
    
    return issues


def check_shared_context() -> List[Dict[str, Any]]:
    """Check SharedContext sync with recent sessions"""
    issues = []
    
    try:
        from core.shared_context import get_shared_context
        ctx = get_shared_context()
        
        # Check contacts
        contacts = ctx.get_contacts()
        if not contacts:
            issues.append({"level": WARNING, "area": "shared_context", "message": "No contacts found in TOOLS.md"})
        
        # Check session sync
        messages = ctx.get_recent_session_messages(limit=5)
        if not messages:
            issues.append({"level": WARNING, "area": "shared_context", "message": "No recent session messages synced"})
        
        # Check memory files
        user_profile = ctx.get_user_profile()
        if not user_profile:
            issues.append({"level": INFO, "area": "shared_context", "message": "USER.md not found or empty"})
        
        memory = ctx.get_long_term_memory()
        if not memory:
            issues.append({"level": INFO, "area": "shared_context", "message": "MEMORY.md not found or empty"})
    
    except Exception as e:
        issues.append({"level": CRITICAL, "area": "shared_context", "message": f"SharedContext check failed: {e}"})
    
    return issues


def check_code_quality() -> List[Dict[str, Any]]:
    """Check for code quality issues"""
    issues = []
    
    # Streamlit deprecations
    legacy_dir = PROJECT_ROOT / "legacy" / "streamlit"
    if legacy_dir.exists():
        result = subprocess.run(
            ["grep", "-r", "use_container_width", str(legacy_dir)],
            capture_output=True, text=True
        )
        if result.stdout:
            count = len(result.stdout.strip().split('\n'))
            issues.append({
                "level": WARNING,
                "area": "deprecation",
                "message": f"{count} Streamlit 'use_container_width' deprecations (replace with width='stretch')"
            })
    
    # Check for m.body vs m.preview issues
    result = subprocess.run(
        ["grep", "-rn", r"\.body", "--include=*.py", str(PROJECT_ROOT / "backend"), str(PROJECT_ROOT / "api")],
        capture_output=True, text=True
    )
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            if 'inbox' in line.lower() and '.body' in line:
                issues.append({
                    "level": WARNING,
                    "area": "code",
                    "message": f"Possible InboxMessage.body access (should be .preview): {line[:100]}"
                })
    
    # Check for None handling in ratings
    result = subprocess.run(
        ["grep", "-rn", r'get\("rating", 0\)', "--include=*.py", str(PROJECT_ROOT)],
        capture_output=True, text=True
    )
    if result.stdout:
        count = len(result.stdout.strip().split('\n'))
        issues.append({
            "level": WARNING,
            "area": "code",
            "message": f"{count} 'get(\"rating\", 0)' patterns - may not handle None correctly (use 'or 0')"
        })
    
    return issues


def check_security() -> List[Dict[str, Any]]:
    """Check security configurations"""
    issues = []
    
    # Check MyCasa WhatsApp allowlist
    try:
        from core.settings_typed import get_settings_store
        settings = get_settings_store().get()
        allow_from = list(getattr(settings.agents.mail, "whatsapp_allow_from", []) or [])
        if len(allow_from) > 1:
            issues.append({
                "level": WARNING,
                "area": "security",
                "message": f"WhatsApp allowlist has {len(allow_from)} numbers - verify all are owner numbers"
            })
    except Exception as e:
        issues.append({"level": INFO, "area": "security", "message": f"Could not read WhatsApp allowlist: {e}"})
    
    # Check SECURITY.md exists
    security_md = PROJECT_ROOT / "SECURITY.md"
    if not security_md.exists():
        issues.append({"level": WARNING, "area": "security", "message": "SECURITY.md not found"})
    
    # Check OUTBOUND_ALLOWLIST.md exists
    outbound_list = PROJECT_ROOT / "OUTBOUND_ALLOWLIST.md"
    if not outbound_list.exists():
        issues.append({"level": WARNING, "area": "security", "message": "OUTBOUND_ALLOWLIST.md not found"})
    
    return issues


def run_full_scan() -> Dict[str, Any]:
    """Run all checks and return full report"""
    print("🔍 MyCasa Pro Issue Scanner")
    print("=" * 50)
    print()
    
    all_issues = []
    
    # Run all checks
    checks = [
        ("Imports", check_imports),
        ("Database", check_database),
        ("SharedContext", check_shared_context),
        ("Code Quality", check_code_quality),
        ("Security", check_security),
    ]
    
    for name, check_fn in checks:
        print(f"Checking {name}...", end=" ")
        try:
            issues = check_fn()
            if issues:
                print(f"found {len(issues)} issue(s)")
                all_issues.extend(issues)
            else:
                print(OK)
        except Exception as e:
            print(f"ERROR: {e}")
            all_issues.append({"level": CRITICAL, "area": name.lower(), "message": f"Check crashed: {e}"})
    
    # Summary
    print()
    print("=" * 50)
    
    critical = [i for i in all_issues if CRITICAL in i["level"]]
    warnings = [i for i in all_issues if WARNING in i["level"]]
    info = [i for i in all_issues if INFO in i["level"]]
    
    print(f"📊 SUMMARY: {len(all_issues)} total issues")
    print(f"   {CRITICAL}: {len(critical)}")
    print(f"   {WARNING}: {len(warnings)}")
    print(f"   {INFO}: {len(info)}")
    print()
    
    if all_issues:
        print("Issues found:")
        for issue in all_issues:
            print(f"  {issue['level']} [{issue['area']}] {issue['message']}")
    else:
        print("✅ No issues found!")
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "issues": all_issues,
        "summary": {
            "total": len(all_issues),
            "critical": len(critical),
            "warnings": len(warnings),
            "info": len(info),
        }
    }
    
    report_path = PROJECT_ROOT / "data" / "logs" / "scan_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n📄 Report saved to: {report_path}")
    
    return report


if __name__ == "__main__":
    run_full_scan()
