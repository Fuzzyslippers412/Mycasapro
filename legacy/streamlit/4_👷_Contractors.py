"""
MyCasa Pro - Contractors Page
"""
import streamlit as st
from pathlib import Path
import sys

APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from components.layout import page_header, empty_state, success_toast
from components.forms import contractor_form
from hooks.use_data import clear_all_caches

# Page config
st.set_page_config(page_title="Contractors - MyCasa Pro", page_icon="👷", layout="wide")

# Load CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Header
page_header("Contractors", "👷", "Service provider directory")

# Initialize session state
if "show_contractor_form" not in st.session_state:
    st.session_state.show_contractor_form = False

# Load data
from agents.contractors import ContractorsAgent
contractors_agent = ContractorsAgent()

with st.spinner("Loading contractors..."):
    contractors = contractors_agent.get_contractors()

# Stats
col1, col2, col3, col4 = st.columns(4)
service_types = list(set(c.get("service_type", "General") for c in contractors))

with col1:
    st.metric("Total Contractors", len(contractors))
with col2:
    st.metric("Service Types", len(service_types))
with col3:
    preferred = len([c for c in contractors if c.get("is_preferred")])
    st.metric("Preferred", preferred)
with col4:
    avg_rating = sum(c.get("rating") or 0 for c in contractors) / len(contractors) if contractors else 0
    st.metric("Avg Rating", f"{avg_rating:.1f}⭐" if avg_rating else "—")

st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

# Filters
col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("🔍 Search contractors", placeholder="Search by name or service...")
with col2:
    type_filter = st.selectbox("Service Type", ["All"] + service_types)

# Add contractor button
if st.button("➕ Add Contractor", type="primary"):
    st.session_state.show_contractor_form = True

# Contractor form
if st.session_state.show_contractor_form:
    with st.expander("New Contractor", expanded=True):
        result = contractor_form(contractors_agent)
        if result:
            if result.get("success"):
                success_toast("Contractor added!")
                st.session_state.show_contractor_form = False
                clear_all_caches()
                st.rerun()
            else:
                st.error(result.get("error", "Failed to add contractor"))
        
        if st.button("Cancel", key="cancel_contractor"):
            st.session_state.show_contractor_form = False
            st.rerun()

st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

# Filter contractors
filtered = contractors
if search:
    filtered = [c for c in filtered if search.lower() in c.get("name", "").lower() or search.lower() in c.get("service_type", "").lower()]
if type_filter != "All":
    filtered = [c for c in filtered if c.get("service_type") == type_filter]

# Contractors list
if filtered:
    for contractor in filtered:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"""
                <div style="
                    background: var(--bg-surface);
                    padding: 1rem;
                    border-radius: 8px;
                    border: 1px solid var(--border-default);
                    margin-bottom: 0.5rem;
                ">
                    <div style="font-weight: 600; font-size: 1rem;">{contractor.get('name', 'Unknown')}</div>
                    <div style="color: var(--text-muted); font-size: 0.875rem;">
                        {contractor.get('service_type', 'General')} • {contractor.get('phone', 'No phone')}
                    </div>
                    {f"<div style='margin-top: 0.5rem;'>{'⭐' * int(contractor.get('rating', 0))} ({contractor.get('rating', 0)})</div>" if contractor.get('rating') else ''}
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if contractor.get("phone"):
                    st.link_button("📞 Call", f"tel:{contractor.get('phone')}")
            
            with col3:
                if contractor.get("email"):
                    st.link_button("✉️ Email", f"mailto:{contractor.get('email')}")
else:
    empty_state(
        "No contractors found" if search or type_filter != "All" else "No contractors added yet",
        "👷",
        "Add Your First Contractor" if not contractors else None,
        "add_first_contractor"
    )
