"""
MyCasa Pro - AI-Driven Home Operating System
Main Entry Point (Multipage App)
"""
import streamlit as st
from pathlib import Path

# App root directory
APP_DIR = Path(__file__).parent

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="MyCasa Pro",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# MyCasa Pro\nAI-Driven Home Operating System"
    }
)

# Load custom CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Custom favicon removal and branding
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom favicon via CSS (workaround) */
    [data-testid="stAppViewContainer"] {
        background: var(--bg-primary);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: var(--bg-surface);
        border-right: 1px solid var(--border-default);
    }
    
    /* Style sidebar navigation buttons */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.125rem 0;
        color: var(--text-secondary);
        font-weight: 500;
        transition: all 0.15s ease;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--bg-secondary);
        color: var(--text-primary);
    }
    
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--accent-primary-subtle);
        color: var(--accent-primary);
        border-left: 3px solid var(--accent-primary);
    }
    
    /* Show default page navigation */
    [data-testid="stSidebarNav"] {
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo
    st.markdown("""
    <div style="
        padding: 1rem 0.5rem 1.5rem;
        border-bottom: 1px solid var(--border-default);
        margin-bottom: 1rem;
    ">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 2rem;">🏠</span>
            <div>
                <div style="font-weight: 700; font-size: 1.25rem; color: var(--text-primary);">MyCasa Pro</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Home Operating System</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.markdown('<div style="font-size: 0.7rem; font-weight: 600; color: var(--text-muted); letter-spacing: 0.05em; padding: 0.5rem 0.5rem 0.25rem;">NAVIGATION</div>', unsafe_allow_html=True)
    
    # Navigation items using page links
    pages = [
        ("🎯", "Dashboard", "pages/1_🎯_Dashboard.py"),
        ("🔧", "Maintenance", "pages/2_🔧_Maintenance.py"),
        ("💰", "Finance", "pages/3_💰_Finance.py"),
        ("👷", "Contractors", "pages/4_👷_Contractors.py"),
        ("🏗️", "Projects", "pages/5_🏗️_Projects.py"),
        ("⚙️", "Settings", "pages/6_⚙️_Settings.py"),
    ]
    
    for icon, label, page_path in pages:
        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
            st.switch_page(page_path)
    
    st.markdown("<div style='flex: 1;'></div>", unsafe_allow_html=True)
    
    # System status
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.divider()
    
    try:
        from hooks.use_data import use_manager
        manager = use_manager()
        status = manager.get_status()
        health = status.get("health", "unknown")
        health_icon = "🟢" if health == "healthy" else "🟡" if health == "degraded" else "🔴"
        
        st.markdown(f"""
        <div style="
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            font-size: 0.875rem;
        ">
            <div style="color: var(--text-muted); font-size: 0.7rem; margin-bottom: 0.25rem;">SYSTEM</div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span>{health_icon}</span>
                <span style="font-weight: 500; text-transform: capitalize;">{health}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f"""
        <div style="
            padding: 0.75rem;
            background: var(--danger-bg);
            border-radius: 8px;
            font-size: 0.75rem;
            color: var(--danger);
        ">
            System status unavailable
        </div>
        """, unsafe_allow_html=True)

# Main content - Auto-redirect to Dashboard
try:
    st.switch_page("pages/1_🎯_Dashboard.py")
except Exception:
    # Fallback welcome page if switch fails
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        text-align: center;
    ">
        <span style="font-size: 4rem; margin-bottom: 1rem;">🏠</span>
        <h1 style="margin: 0; color: var(--text-primary);">Welcome to MyCasa Pro</h1>
        <p style="color: var(--text-muted); margin-top: 0.5rem;">Select a page from the sidebar to get started</p>
    </div>
    """, unsafe_allow_html=True)
