"""
MyCasa Pro - Maintenance Page
"""
import streamlit as st
from pathlib import Path
import sys

APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from components.layout import page_header, empty_state, section_header, success_toast
from components.cards import task_card
from components.forms import task_form
from hooks.use_data import clear_all_caches

# Page config  
st.set_page_config(page_title="Maintenance - MyCasa Pro", page_icon="🔧", layout="wide")

# Load CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Header
page_header("Maintenance", "🔧", "Track and manage household tasks")

# Initialize session state
if "show_task_form" not in st.session_state:
    st.session_state.show_task_form = False

# Load data
with st.spinner("Loading tasks..."):
    from agents.maintenance import MaintenanceAgent
    maintenance = MaintenanceAgent()
    tasks = maintenance.get_pending_tasks()
    overdue = maintenance.get_overdue_tasks()
    upcoming = maintenance.get_upcoming_tasks(7)

# Stats row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Pending", len(tasks))
with col2:
    st.metric("Overdue", len(overdue), delta=f"-{len(overdue)}" if overdue else None, delta_color="inverse")
with col3:
    st.metric("This Week", len(upcoming))
with col4:
    completed_today = 0  # TODO: track completions
    st.metric("Completed Today", completed_today)

st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

# Action bar
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    search = st.text_input("🔍 Search tasks", placeholder="Search by title...")
with col2:
    status_filter = st.selectbox("Status", ["All", "Pending", "In Progress", "Completed"])
with col3:
    priority_filter = st.selectbox("Priority", ["All", "Urgent", "High", "Medium", "Low"])

# Add task button
if st.button("➕ Add Task", use_container_width=False, type="primary"):
    st.session_state.show_task_form = True

# Task form
if st.session_state.show_task_form:
    with st.expander("New Task", expanded=True):
        result = task_form(maintenance)
        if result:
            if result.get("success"):
                success_toast("Task created!")
                st.session_state.show_task_form = False
                clear_all_caches()
                st.rerun()
            else:
                st.error(result.get("error", "Failed to create task"))
        
        if st.button("Cancel", key="cancel_task"):
            st.session_state.show_task_form = False
            st.rerun()

st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

# Overdue section
if overdue:
    section_header(f"Overdue ({len(overdue)})", "🚨", "#ef4444")
    for task in overdue:
        col1, col2 = st.columns([4, 1])
        with col1:
            task_card(
                title=task.get("title", "Task"),
                status="overdue",
                priority=task.get("priority", "high"),
                due_date=task.get("scheduled_date"),
                category=task.get("category")
            )
        with col2:
            if st.button("Complete", key=f"complete_overdue_{task.get('id')}"):
                result = maintenance.complete_task(task.get("id"), evidence="Marked complete via UI")
                if result.get("success"):
                    success_toast("Task completed!")
                    clear_all_caches()
                    st.rerun()

# Tasks list
section_header("All Tasks", "📋", "#6366f1")

# Filter tasks
filtered_tasks = tasks
if search:
    filtered_tasks = [t for t in filtered_tasks if search.lower() in t.get("title", "").lower()]
if status_filter != "All":
    filtered_tasks = [t for t in filtered_tasks if t.get("status", "").lower() == status_filter.lower().replace(" ", "_")]
if priority_filter != "All":
    filtered_tasks = [t for t in filtered_tasks if t.get("priority", "").lower() == priority_filter.lower()]

if filtered_tasks:
    for task in filtered_tasks:
        col1, col2 = st.columns([4, 1])
        with col1:
            task_card(
                title=task.get("title", "Task"),
                status=task.get("status", "pending"),
                priority=task.get("priority", "medium"),
                due_date=task.get("scheduled_date"),
                category=task.get("category")
            )
        with col2:
            if task.get("status") != "completed":
                if st.button("✓", key=f"complete_{task.get('id')}", help="Mark complete"):
                    result = maintenance.complete_task(task.get("id"), evidence="Marked complete via UI")
                    if result.get("success"):
                        success_toast("Task completed!")
                        clear_all_caches()
                        st.rerun()
else:
    empty_state(
        "No tasks found" if search or status_filter != "All" or priority_filter != "All" else "No maintenance tasks yet",
        "✨" if not tasks else "🔍",
        "Add Your First Task" if not tasks else None,
        "add_first_task"
    )
