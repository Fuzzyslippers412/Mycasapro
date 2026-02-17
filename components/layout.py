"""
Layout Components for MyCasa Pro
Common wrappers, empty states, loading states, confirmations
"""
import streamlit as st
from typing import Optional


def page_header(title: str, icon: str = "", subtitle: str = None):
    """Standard page header"""
    from datetime import datetime
    
    st.markdown(f"""
    <div style="margin-bottom: 1.5rem;">
        <h1 style="margin: 0; font-size: 1.75rem; font-weight: 600;">
            {icon} {title}
        </h1>
        {f'<p style="color: var(--text-muted); margin: 0.25rem 0 0 0; font-size: 0.875rem;">{subtitle}</p>' if subtitle else ''}
        <p style="color: var(--text-muted); margin: 0.25rem 0 0 0; font-size: 0.75rem;">
            Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </p>
    </div>
    """, unsafe_allow_html=True)


def empty_state(
    message: str,
    icon: str = "📭",
    action_label: str = None,
    action_key: str = None
) -> bool:
    """
    Display an empty state with optional action button.
    Returns True if action button was clicked.
    """
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 3rem 2rem;
        background: var(--bg-surface);
        border-radius: 12px;
        border: 1px dashed var(--border-default);
        margin: 1rem 0;
    ">
        <div style="font-size: 3rem; margin-bottom: 1rem;">{icon}</div>
        <div style="color: var(--text-secondary); font-size: 1rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if action_label and action_key:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            return st.button(action_label, key=action_key, use_container_width=True, type="primary")
    return False


def loading_skeleton(height: int = 100, count: int = 1):
    """Display loading skeleton placeholders"""
    for _ in range(count):
        st.markdown(f"""
        <div style="
            height: {height}px;
            background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-surface) 50%, var(--bg-secondary) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 8px;
            margin-bottom: 0.75rem;
        "></div>
        <style>
        @keyframes shimmer {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}
        </style>
        """, unsafe_allow_html=True)


def confirm_dialog(
    message: str,
    confirm_label: str = "Confirm",
    cancel_label: str = "Cancel",
    key: str = "confirm"
) -> Optional[bool]:
    """
    Display a confirmation dialog.
    Returns True if confirmed, False if cancelled, None if no action yet.
    """
    if f"{key}_show" not in st.session_state:
        st.session_state[f"{key}_show"] = False
    
    if st.session_state[f"{key}_show"]:
        st.warning(message)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button(cancel_label, key=f"{key}_cancel", use_container_width=True):
                st.session_state[f"{key}_show"] = False
                return False
        with col2:
            if st.button(confirm_label, key=f"{key}_confirm", use_container_width=True, type="primary"):
                st.session_state[f"{key}_show"] = False
                return True
        return None
    return None


def show_confirm(key: str):
    """Show a confirmation dialog"""
    st.session_state[f"{key}_show"] = True


def success_toast(message: str):
    """Show a success toast notification"""
    st.toast(message, icon="✅")


def error_toast(message: str):
    """Show an error toast notification"""
    st.toast(message, icon="❌")


def info_toast(message: str):
    """Show an info toast notification"""
    st.toast(message, icon="ℹ️")


def section_header(title: str, icon: str = "", color: str = "#6366f1"):
    """Display a colored section header"""
    st.markdown(f"""
    <div style='
        background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
        padding: 1rem 1.25rem;
        border-radius: 12px;
        border: 1px solid rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.2);
        margin-bottom: 1rem;
    '>
        <div style='font-weight: 600; font-size: 1rem;'>{icon} {title}</div>
    </div>
    """, unsafe_allow_html=True)


def stat_row(stats: list):
    """Display a row of stats"""
    cols = st.columns(len(stats))
    for col, stat in zip(cols, stats):
        with col:
            st.metric(
                label=stat.get("label", ""),
                value=stat.get("value", 0),
                delta=stat.get("delta"),
                delta_color=stat.get("delta_color", "normal")
            )
