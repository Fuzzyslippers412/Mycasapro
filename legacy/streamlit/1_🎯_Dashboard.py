"""
MyCasa Pro - Dashboard Page
Live system awareness with cost telemetry
"""
import streamlit as st
from pathlib import Path
import sys

# Add app root to path
APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from components.layout import page_header, empty_state, section_header
from components.cards import metric_card, task_card, bill_card, activity_item
from hooks.use_data import use_dashboard_data, use_manager, clear_all_caches

# Page config
st.set_page_config(page_title="Dashboard - MyCasa Pro", page_icon="🏠", layout="wide")

# Load CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Header
page_header("Dashboard", "🎯", "Live system status and activity")

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE STATUS BAR
# ═══════════════════════════════════════════════════════════════════════════════

# Load event bus for live data
try:
    from core.events import get_event_bus
    event_bus = get_event_bus()
    system_summary = event_bus.get_system_summary()
    is_active = system_summary.get("is_active", False)
    active_count = system_summary.get("active_agents", 0)
    last_event = system_summary.get("last_event_time")
except Exception:
    is_active = False
    active_count = 0
    last_event = None
    system_summary = {}

# Active work indicator
status_color = "#22c55e" if is_active else "#6b7280"
status_text = f"{active_count} agent{'s' if active_count != 1 else ''} working" if is_active else "System idle"
animation_style = "animation: pulse 2s infinite;" if is_active else ""
last_activity = last_event[:19].replace('T', ' ') if last_event else 'No recent activity'

status_html = f'''<div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1.25rem; background: var(--bg-surface); border-radius: 10px; border: 1px solid var(--border-default); margin-bottom: 1.5rem;">
<div style="display: flex; align-items: center; gap: 1rem;">
<div style="width: 12px; height: 12px; background: {status_color}; border-radius: 50%; box-shadow: 0 0 8px {status_color}40; {animation_style}"></div>
<div>
<div style="font-weight: 600; font-size: 0.95rem;">{status_text}</div>
<div style="color: var(--text-muted); font-size: 0.75rem;">Last activity: {last_activity}</div>
</div>
</div>
<div style="display: flex; align-items: center; gap: 0.5rem;">
<span style="color: var(--text-muted); font-size: 0.75rem;">Auto-refresh</span>
<span style="font-size: 0.75rem;">🔄</span>
</div>
</div>
<style>@keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}</style>'''

st.markdown(status_html, unsafe_allow_html=True)

# Load dashboard data
with st.spinner("Loading..."):
    dashboard = use_dashboard_data()
    manager = use_manager()

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM COST WIDGET - DISABLED until API cost tracking is ready
# ═══════════════════════════════════════════════════════════════════════════════
# TODO: Re-enable when ready to track real API costs
# (Removed to avoid showing fake/placeholder data)

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTS (if any)
# ═══════════════════════════════════════════════════════════════════════════════

alerts = dashboard.get("alerts", [])
if alerts:
    for alert in alerts[:3]:
        # Support both 'severity' and 'priority' keys
        severity = alert.get("severity") or alert.get("priority", "medium")
        is_critical = severity in ["high", "critical", "urgent"]
        bg = "rgba(239, 68, 68, 0.1)" if is_critical else "rgba(245, 158, 11, 0.1)"
        border = "#ef4444" if is_critical else "#f59e0b"
        icon = "🚨" if is_critical else "⚠️"
        
        st.markdown(f'''<div style="background: {bg}; border-left: 3px solid {border}; padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-bottom: 0.5rem;">
<div style="font-weight: 500;">{icon} {alert.get('title', 'Alert')}</div>
<div style="color: var(--text-muted); font-size: 0.8rem;">{alert.get('message', '')}</div>
</div>''', unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# QUICK STATS ROW
# ═══════════════════════════════════════════════════════════════════════════════

quick = dashboard.get("quick_stats", {})
col1, col2, col3, col4 = st.columns(4)

with col1:
    pending = quick.get("tasks_today", 0)
    overdue = len(dashboard.get("overdue_tasks", []))
    metric_card(
        title="Tasks Today",
        value=pending,
        icon="📋",
        subtitle=f"{overdue} overdue" if overdue > 0 else "On track",
        color="#ef4444" if overdue > 0 else "#22c55e"
    )

with col2:
    bills_due = quick.get("bills_this_week", 0)
    metric_card(
        title="Bills This Week",
        value=bills_due,
        icon="💳",
        subtitle="Due soon" if bills_due > 0 else "All clear",
        color="#f59e0b" if bills_due > 0 else "#22c55e"
    )

with col3:
    projects = quick.get("active_projects", 0)
    metric_card(
        title="Active Projects",
        value=projects,
        icon="🏗️",
        subtitle="In progress",
        color="#6366f1"
    )

with col4:
    portfolio_val = quick.get("portfolio_value")
    metric_card(
        title="Portfolio",
        value=f"${portfolio_val:,.0f}" if portfolio_val else "—",
        icon="📈",
        subtitle="Current value",
        color="#8b5cf6"
    )

st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT: THREE COLUMNS
# ═══════════════════════════════════════════════════════════════════════════════

col_left, col_mid, col_right = st.columns([2, 2, 1.5])

# ─────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN: Tasks & Bills
# ─────────────────────────────────────────────────────────────────────────────
with col_left:
    section_header("Upcoming Tasks", "📅", "#6366f1")
    tasks = dashboard.get("upcoming_tasks", [])
    if tasks:
        for task in tasks[:4]:
            task_card(
                title=task.get("title", "Task"),
                status=task.get("status", "pending"),
                priority=task.get("priority", "medium"),
                due_date=task.get("scheduled_date"),
                category=task.get("category")
            )
    else:
        empty_state("No upcoming tasks", "✨")
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    section_header("Upcoming Bills", "💰", "#22c55e")
    bills = dashboard.get("upcoming_bills", [])
    if bills:
        for bill in bills[:3]:
            bill_card(
                name=bill.get("name", "Bill"),
                amount=bill.get("amount", 0),
                due_date=bill.get("due_date"),
                days_until=bill.get("days_until_due"),
                is_paid=bill.get("is_paid", False),
                auto_pay=bill.get("auto_pay", False)
            )
    else:
        empty_state("No upcoming bills", "🎉")

# ─────────────────────────────────────────────────────────────────────────────
# MIDDLE COLUMN: Live Events & Agent Activity
# ─────────────────────────────────────────────────────────────────────────────
with col_mid:
    section_header("Live Events", "⚡", "#f59e0b")
    
    # Get recent events
    recent_events = system_summary.get("recent_events", [])
    
    if recent_events:
        for event in recent_events[-6:]:
            event_type = event.get("event_type", "info")
            agent = event.get("agent_id", "system")
            title = event.get("title", event_type)
            timestamp = event.get("timestamp", "")[:19].replace("T", " ")
            duration = event.get("duration_ms")
            
            # Icon based on event type
            icons = {
                "task_started": "▶️",
                "task_completed": "✅",
                "task_failed": "❌",
                "cost_recorded": "💵",
                "prompt_started": "🤖",
                "prompt_completed": "🤖",
                "connector_sync_started": "🔄",
                "connector_sync_completed": "✅",
                "warning": "⚠️",
                "error": "❌"
            }
            icon = icons.get(event_type, "📌")
            
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: flex-start;
                gap: 0.75rem;
                padding: 0.5rem 0;
                border-bottom: 1px solid var(--border-default);
            ">
                <span style="font-size: 0.9rem;">{icon}</span>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-size: 0.85rem; font-weight: 500;">{title}</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">
                        {agent} • {timestamp[-8:]}
                        {f' • {duration}ms' if duration else ''}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
        ">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">📭</div>
            <div>No recent events</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Agent Activity
    section_header("Agent Status", "🤖", "#8b5cf6")
    
    agent_activity = event_bus.get_agent_activity() if 'event_bus' in dir() else {}
    
    if agent_activity:
        for agent_id, activity in agent_activity.items():
            state = activity.state.value if hasattr(activity, 'state') else 'unknown'
            state_icon = {
                "idle": "⚪",
                "running": "🟢",
                "blocked": "🟡",
                "error": "🔴",
                "disabled": "⚫"
            }.get(state, "⚪")
            
            current_task = activity.current_task_type if hasattr(activity, 'current_task_type') else None
            elapsed = activity.elapsed_ms() if hasattr(activity, 'elapsed_ms') else None
            
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.5rem 0.75rem;
                background: var(--bg-surface);
                border-radius: 6px;
                margin-bottom: 0.5rem;
                border: 1px solid var(--border-default);
            ">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>{state_icon}</span>
                    <span style="font-weight: 500; text-transform: capitalize;">{agent_id}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">
                    {current_task if current_task else state}
                    {f' ({elapsed/1000:.1f}s)' if elapsed else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Show default agents
        default_agents = ["finance", "maintenance", "security", "janitor"]
        for agent in default_agents:
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.5rem 0.75rem;
                background: var(--bg-surface);
                border-radius: 6px;
                margin-bottom: 0.5rem;
                border: 1px solid var(--border-default);
            ">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span>⚪</span>
                    <span style="font-weight: 500; text-transform: capitalize;">{agent}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">idle</div>
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN: Activity Log
# ─────────────────────────────────────────────────────────────────────────────
with col_right:
    # Cost Trend disabled until API cost tracking is ready
    
    section_header("Activity Log", "🕐", "#f59e0b")
    activity = dashboard.get("recent_activity", [])
    if activity:
        for log in activity[:5]:
            activity_item(
                agent=log.get("agent", "system"),
                action=log.get("action", "action"),
                details=log.get("details"),
                timestamp=log.get("time", "")[-8:] if log.get("time") else None,
                status=log.get("status", "success")
            )
    else:
        empty_state("No recent activity", "📝")

# ═══════════════════════════════════════════════════════════════════════════════
# REFRESH BUTTON
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        clear_all_caches()
        st.rerun()
