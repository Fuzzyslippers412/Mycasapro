"""
Card Components for MyCasa Pro
Premium Light Theme - Clean, intentional design
"""
import streamlit as st
from typing import Any


def metric_card(
    title: str,
    value: Any,
    subtitle: str = None,
    icon: str = None,
    trend: str = None,
    trend_value: str = None,
    color: str = None
):
    """
    Display a metric card
    
    Intent: Quick glanceable numbers with context
    - Large value for immediate comprehension
    - Subtle title and subtitle for context
    - Optional trend indicator for change awareness
    """
    accent = color or "var(--accent-primary)"
    
    trend_style = ""
    trend_icon = ""
    if trend == "up":
        trend_style = "background: var(--success-bg); color: var(--success);"
        trend_icon = "↑"
    elif trend == "down":
        trend_style = "background: var(--danger-bg); color: var(--danger);"
        trend_icon = "↓"
    
    st.markdown(f"""
    <div class="metric-card" style="border-left: 3px solid {accent};">
        <div class="metric-header">
            <span class="metric-icon">{icon or '📊'}</span>
            <span class="metric-title">{title}</span>
        </div>
        <div class="metric-value">{value}</div>
        {f'<div class="metric-subtitle">{subtitle}</div>' if subtitle else ''}
        {f'<div class="metric-trend" style="{trend_style}">{trend_icon} {trend_value}</div>' if trend_value else ''}
    </div>
    """, unsafe_allow_html=True)


def task_card(
    title: str,
    status: str,
    priority: str,
    due_date: str = None,
    category: str = None,
    on_click: callable = None
):
    """
    Display a task card
    
    Intent: Scannable task list with clear priority signals
    - Status icon for completion state at a glance
    - Priority badge with semantic colors (urgent=red, high=amber, etc.)
    - Category and due date as secondary info
    """
    priority_config = {
        "urgent": {"color": "var(--danger)", "bg": "var(--danger-bg)"},
        "high": {"color": "var(--warning)", "bg": "var(--warning-bg)"},
        "medium": {"color": "var(--accent-primary)", "bg": "var(--accent-primary-subtle)"},
        "low": {"color": "var(--success)", "bg": "var(--success-bg)"}
    }
    status_icons = {
        "pending": "○",
        "in_progress": "◐",
        "completed": "●",
        "cancelled": "✕"
    }
    
    config = priority_config.get(priority, priority_config["medium"])
    icon = status_icons.get(status, "○")
    
    st.markdown(f"""
    <div class="task-card" style="border-left: 3px solid {config['color']};">
        <div class="task-header">
            <span class="task-icon" style="color: {config['color']};">{icon}</span>
            <span class="task-title">{title}</span>
        </div>
        <div class="task-meta">
            {f'<span class="task-category">{category}</span>' if category else ''}
            {f'<span class="task-due">📅 {due_date}</span>' if due_date else ''}
            <span class="task-priority" style="background: {config['bg']}; color: {config['color']};">{priority.upper()}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def bill_card(
    name: str,
    amount: float,
    due_date: str,
    days_until: int = None,
    is_paid: bool = False,
    auto_pay: bool = False
):
    """
    Display a bill card
    
    Intent: Clear bill status with urgency indicators
    - Amount prominently displayed
    - Status badge shows urgency (overdue=red, due soon=amber)
    - Auto-pay indicator reduces mental load for managed bills
    """
    if is_paid:
        config = {"color": "var(--success)", "bg": "var(--success-bg)", "text": "PAID"}
    elif days_until is not None and days_until < 0:
        config = {"color": "var(--danger)", "bg": "var(--danger-bg)", "text": "OVERDUE"}
    elif days_until is not None and days_until <= 3:
        config = {"color": "var(--danger)", "bg": "var(--danger-bg)", "text": f"{days_until}d"}
    elif days_until is not None and days_until <= 7:
        config = {"color": "var(--warning)", "bg": "var(--warning-bg)", "text": f"{days_until}d"}
    else:
        config = {"color": "var(--text-muted)", "bg": "var(--bg-secondary)", "text": f"{days_until}d" if days_until else "—"}
    
    st.markdown(f"""
    <div class="bill-card" style="border-left: 3px solid {config['color']};">
        <div class="bill-header">
            <span class="bill-name">{name}</span>
            <span class="bill-amount">${amount:,.2f}</span>
        </div>
        <div class="bill-meta">
            <span class="bill-due">📅 {due_date}</span>
            <span class="bill-status" style="background: {config['bg']}; color: {config['color']};">{config['text']}</span>
            {f'<span class="bill-autopay">⟳ Auto-pay</span>' if auto_pay else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)


def alert_card(
    title: str,
    message: str,
    severity: str = "medium",
    action_label: str = None
):
    """
    Display an alert card
    
    Intent: Attention-grabbing notifications with clear severity
    - Left border color indicates urgency level
    - Background tint reinforces severity
    - Concise title + explanatory message
    """
    config = {
        "critical": {"color": "var(--danger)", "bg": "var(--danger-bg)", "icon": "⚠"},
        "high": {"color": "var(--warning)", "bg": "var(--warning-bg)", "icon": "!"},
        "medium": {"color": "var(--info)", "bg": "var(--info-bg)", "icon": "ℹ"},
        "low": {"color": "var(--success)", "bg": "var(--success-bg)", "icon": "✓"}
    }.get(severity, {"color": "var(--info)", "bg": "var(--info-bg)", "icon": "ℹ"})
    
    st.markdown(f"""
    <div class="alert-card" style="background: {config['bg']}; border-left-color: {config['color']};">
        <div class="alert-header">
            <span class="alert-icon" style="color: {config['color']};">{config['icon']}</span>
            <span class="alert-title">{title}</span>
        </div>
        <div class="alert-message">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def contractor_card(
    name: str,
    service_type: str,
    phone: str = None,
    rating: int = None,
    hourly_rate: float = None,
    notes: str = None
):
    """
    Display a contractor card
    
    Intent: Quick reference for service providers
    - Name and type immediately visible
    - Contact info and rate for quick reference
    - Star rating for quality assessment
    """
    stars = "★" * (rating or 0) + "☆" * (5 - (rating or 0))
    
    st.markdown(f"""
    <div class="contractor-card">
        <div class="contractor-header">
            <span class="contractor-name">{name}</span>
            <span class="contractor-type">{service_type.replace('_', ' ')}</span>
        </div>
        <div class="contractor-meta">
            {f'<span>📞 {phone}</span>' if phone else ''}
            {f'<span>💰 ${hourly_rate:.0f}/hr</span>' if hourly_rate else ''}
        </div>
        {f'<div class="contractor-rating">{stars}</div>' if rating else ''}
        {f'<div style="margin-top: 0.5rem; font-size: 0.8125rem; color: var(--text-secondary);">{notes}</div>' if notes else ''}
    </div>
    """, unsafe_allow_html=True)


def activity_item(
    agent: str,
    action: str,
    details: str = None,
    timestamp: str = None,
    status: str = "success"
):
    """
    Display an activity log item
    
    Intent: Chronological system activity for transparency
    - Agent icon identifies the source
    - Action as primary text
    - Timestamp for temporal context
    """
    icons = {
        "supervisor": "🎯",
        "maintenance": "🔧",
        "finance": "💰"
    }
    
    icon = icons.get(agent, "📋")
    time_display = timestamp.replace("T", " ")[:16] if timestamp and "T" in timestamp else (timestamp or "")
    
    st.markdown(f"""
    <div class="activity-item">
        <span class="activity-icon">{icon}</span>
        <div class="activity-content">
            <span class="activity-action">{action}</span>
            {f'<span class="activity-details">{details}</span>' if details else ''}
        </div>
        <span class="activity-time">{time_display}</span>
    </div>
    """, unsafe_allow_html=True)
