"""
MyCasa Pro - Projects Page
"""
import streamlit as st
from pathlib import Path
import sys

APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from components.layout import page_header, empty_state, section_header, success_toast
from components.forms import project_form
from hooks.use_data import clear_all_caches

# Page config
st.set_page_config(page_title="Projects - MyCasa Pro", page_icon="🏗️", layout="wide")

# Load CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Header
page_header("Projects", "🏗️", "Renovations and improvements")

# Initialize session state
if "show_project_form" not in st.session_state:
    st.session_state.show_project_form = False

# Load data
from agents.projects import ProjectsAgent
projects_agent = ProjectsAgent()

with st.spinner("Loading projects..."):
    projects = projects_agent.get_projects()
    active = projects_agent.get_active_projects()

# Stats
col1, col2, col3, col4 = st.columns(4)

total_budget = sum(p.get("budget", 0) for p in projects)
total_spent = sum(p.get("spent", 0) for p in projects)

with col1:
    st.metric("Total Projects", len(projects))
with col2:
    st.metric("Active", len(active))
with col3:
    st.metric("Total Budget", f"${total_budget:,.0f}")
with col4:
    pct_spent = (total_spent / total_budget * 100) if total_budget > 0 else 0
    st.metric("Spent", f"${total_spent:,.0f}", delta=f"{pct_spent:.0f}% of budget")

st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

# Add project button
if st.button("➕ New Project", type="primary"):
    st.session_state.show_project_form = True

# Project form
if st.session_state.show_project_form:
    with st.expander("New Project", expanded=True):
        result = project_form(projects_agent)
        if result:
            if result.get("success"):
                success_toast("Project created!")
                st.session_state.show_project_form = False
                clear_all_caches()
                st.rerun()
            else:
                st.error(result.get("error", "Failed to create project"))
        
        if st.button("Cancel", key="cancel_project"):
            st.session_state.show_project_form = False
            st.rerun()

st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

# Active projects
if active:
    section_header(f"Active Projects ({len(active)})", "🚧", "#f59e0b")
    
    for project in active:
        progress = (project.get("spent", 0) / project.get("budget", 1) * 100) if project.get("budget") else 0
        
        st.markdown(f"""
        <div style="
            background: var(--bg-surface);
            padding: 1.25rem;
            border-radius: 12px;
            border: 1px solid var(--border-default);
            margin-bottom: 1rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                <div>
                    <div style="font-weight: 600; font-size: 1.1rem;">{project.get('name', 'Project')}</div>
                    <div style="color: var(--text-muted); font-size: 0.875rem;">{project.get('description', '')[:100]}</div>
                </div>
                <div style="
                    background: var(--warning-bg);
                    color: var(--warning);
                    padding: 0.25rem 0.75rem;
                    border-radius: 999px;
                    font-size: 0.75rem;
                    font-weight: 600;
                ">{project.get('status', 'active').upper()}</div>
            </div>
            <div style="margin-top: 1rem;">
                <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 0.25rem;">
                    <span>Budget: ${project.get('budget', 0):,.0f}</span>
                    <span>Spent: ${project.get('spent', 0):,.0f} ({progress:.0f}%)</span>
                </div>
                <div style="
                    background: var(--bg-secondary);
                    border-radius: 999px;
                    height: 8px;
                    overflow: hidden;
                ">
                    <div style="
                        background: {'var(--danger)' if progress > 90 else 'var(--warning)' if progress > 70 else 'var(--success)'};
                        height: 100%;
                        width: {min(progress, 100)}%;
                        border-radius: 999px;
                    "></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# All projects
section_header("All Projects", "📁", "#6366f1")

if projects:
    for project in projects:
        if project not in active:
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid var(--border-default);
                margin-bottom: 0.5rem;
                opacity: 0.7;
            ">
                <div style="font-weight: 500;">{project.get('name', 'Project')}</div>
                <div style="color: var(--text-muted); font-size: 0.875rem;">
                    {project.get('status', 'unknown').title()} • ${project.get('budget', 0):,.0f} budget
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    empty_state(
        "No projects yet",
        "🏗️",
        "Start Your First Project",
        "start_project"
    )
