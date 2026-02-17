"""
MyCasa Pro - Settings Page
Unified settings for all system components
"""
import streamlit as st
from pathlib import Path
import sys

APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from components.layout import page_header, section_header, success_toast
from hooks.use_data import clear_all_caches, use_manager

# Page config
st.set_page_config(page_title="Settings - MyCasa Pro", page_icon="⚙️", layout="wide")

# Load CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Header
page_header("Settings", "⚙️", "System configuration and agent settings")

# Load manager once
manager = use_manager()
status = manager.get_status()

# Tabs - organized by domain
tab_agents, tab_finance, tab_personas, tab_system = st.tabs([
    "🤖 Agents", 
    "💰 Finance Manager", 
    "👤 Personas", 
    "🔧 System"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: AGENTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_agents:
    section_header("Agent Status", "🤖", "#6366f1")
    
    # Health overview
    col1, col2, col3 = st.columns(3)
    with col1:
        health = status.get("health", "unknown")
        health_icon = "🟢" if health == "healthy" else "🟡" if health == "degraded" else "🔴"
        st.metric("System Health", f"{health_icon} {health.title()}")
    with col2:
        st.metric("Loaded Agents", len(status.get("loaded_agents", [])))
    with col3:
        st.metric("Total Agents", status.get("total_agents", 0))
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Agent list
    quick = manager.quick_status()
    agents = quick.get("facts", {}).get("agents", {})
    
    for name, info in agents.items():
        state = info.get("state", "unknown")
        icon = "🟢" if state == "online" else "⚪" if state == "not_loaded" else "🔴"
        
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: var(--bg-surface);
            border-radius: 8px;
            border: 1px solid var(--border-default);
            margin-bottom: 0.5rem;
        ">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <span>{icon}</span>
                <span style="font-weight: 500; text-transform: capitalize;">{name}</span>
            </div>
            <span style="color: var(--text-muted); font-size: 0.875rem;">{state}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Status", use_container_width=True):
        clear_all_caches()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: FINANCE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_finance:
    from agents.finance import FinanceAgent
    finance = FinanceAgent()
    
    finance_settings = finance.get_settings()
    intake_complete = finance_settings.get("intake_complete", False)
    
    if not intake_complete:
        # ─────────────────────────────────────────────────────────────────────
        # INTAKE FLOW (First-time setup)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, var(--bg-surface) 100%);
            padding: 2rem;
            border-radius: 16px;
            border: 1px solid var(--accent-primary);
            margin-bottom: 1.5rem;
        ">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="
                    width: 56px; height: 56px;
                    background: var(--accent-primary);
                    border-radius: 12px;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 1.75rem;
                ">💰</div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">Finance Manager Setup</div>
                    <div style="color: var(--text-muted);">Complete this one-time setup to enable all finance features</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("📋 **Required before finance features work:** income source, cost limits, and spend guardrails")
        
        with st.form("finance_intake_form", clear_on_submit=False):
            # Step 1: Income Source
            st.markdown("#### 1️⃣ Primary Income Source")
            st.caption("Where does household cash flow come from?")
            
            col1, col2 = st.columns(2)
            with col1:
                income_name = st.text_input(
                    "Account Name *", 
                    value="J.P. Morgan Brokerage",
                    help="Primary funding source name"
                )
                income_institution = st.text_input(
                    "Institution", 
                    value="J.P. Morgan"
                )
            with col2:
                income_account_type = st.selectbox(
                    "Account Type", 
                    ["brokerage", "checking", "savings", "investment", "other"]
                )
                income_type = st.selectbox(
                    "Income Type", 
                    ["investment", "salary", "mixed", "other"],
                    help="Investment = drawdowns, Salary = regular deposits"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                monthly_min = st.number_input(
                    "Expected Monthly Min ($)", 
                    min_value=0.0, value=5000.0, step=1000.0,
                    help="Rough lower bound"
                )
            with col2:
                monthly_max = st.number_input(
                    "Expected Monthly Max ($)", 
                    min_value=0.0, value=20000.0, step=1000.0,
                    help="Rough upper bound"
                )
            
            st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
            
            # Step 2: System Cost Budget
            st.markdown("#### 2️⃣ System Cost Budget")
            st.caption("MyCasa Pro's own operational costs (AI, hosting, integrations)")
            
            system_budget = st.slider(
                "Monthly Cap ($)", 
                min_value=100, max_value=2000, value=1000, step=50,
                help="Hard limit for MyCasa Pro's running costs"
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div style='text-align:center;color:var(--text-muted);font-size:0.75rem;'>Warn at 70%<br><strong>${int(system_budget * 0.7)}</strong></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='text-align:center;color:var(--warning);font-size:0.75rem;'>Alert at 85%<br><strong>${int(system_budget * 0.85)}</strong></div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div style='text-align:center;color:var(--danger);font-size:0.75rem;'>Critical at 95%<br><strong>${int(system_budget * 0.95)}</strong></div>", unsafe_allow_html=True)
            
            st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
            
            # Step 3: Spend Guardrails
            st.markdown("#### 3️⃣ Spend Guardrails")
            st.caption("Visibility thresholds — warnings, not blocks")
            
            col1, col2 = st.columns(2)
            with col1:
                monthly_limit = st.number_input(
                    "Monthly Target ($)", 
                    min_value=1000.0, value=10000.0, step=500.0,
                    help="Target monthly household spend"
                )
            with col2:
                daily_cap = st.number_input(
                    "Daily Soft Cap ($)", 
                    min_value=10.0, value=150.0, step=10.0,
                    help="Flag days over this amount"
                )
            
            st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
            
            # Step 4: Payment Rails
            st.markdown("#### 4️⃣ Payment Rails")
            st.caption("How money typically moves out")
            
            payment_rails = st.multiselect(
                "Preferred Methods",
                ["card", "ach", "apple_cash", "zelle", "venmo", "check", "cash", "wire"],
                default=["card", "ach", "apple_cash"]
            )
            
            st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
            
            # Submit
            submitted = st.form_submit_button(
                "✅ Complete Setup", 
                type="primary", 
                use_container_width=True
            )
            
            if submitted:
                if not income_name.strip():
                    st.error("Account name is required")
                else:
                    result = finance.complete_intake(
                        primary_income_source={
                            "name": income_name.strip(),
                            "institution": income_institution.strip() or None,
                            "account_type": income_account_type,
                            "income_type": income_type,
                            "expected_monthly_min": monthly_min if monthly_min > 0 else None,
                            "expected_monthly_max": monthly_max if monthly_max > 0 else None
                        },
                        system_cost_budget=float(system_budget),
                        monthly_spend_limit=monthly_limit,
                        daily_soft_cap=daily_cap,
                        preferred_payment_rails=payment_rails
                    )
                    
                    if result.get("success"):
                        success_toast("Finance Manager is ready!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(result.get("error", "Setup failed"))
    
    else:
        # ─────────────────────────────────────────────────────────────────────
        # POST-INTAKE SETTINGS VIEW
        # ─────────────────────────────────────────────────────────────────────
        
        # Status badge
        st.markdown("""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(34, 197, 94, 0.15);
            border: 1px solid #22c55e;
            border-radius: 20px;
            color: #22c55e;
            font-weight: 500;
            font-size: 0.875rem;
            margin-bottom: 1.5rem;
        ">
            <span>✓</span> Finance Manager Active
        </div>
        """, unsafe_allow_html=True)
        
        # ── Income Sources ──────────────────────────────────────────────────
        section_header("Income Sources", "💵", "#22c55e")
        
        income_sources = finance.get_income_sources()
        for src in income_sources:
            is_primary = src.get("is_primary", False)
            badge = '<span style="background:#6366f1;color:white;padding:2px 8px;border-radius:4px;font-size:0.7rem;margin-left:0.5rem;">PRIMARY</span>' if is_primary else ''
            
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1rem 1.25rem;
                border-radius: 10px;
                border: 1px solid {'var(--accent-primary)' if is_primary else 'var(--border-default)'};
                margin-bottom: 0.75rem;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-weight: 600; font-size: 1rem;">{src.get('name')}</span>
                        {badge}
                    </div>
                    <span style="
                        background: var(--bg-secondary);
                        padding: 0.25rem 0.75rem;
                        border-radius: 4px;
                        font-size: 0.75rem;
                        color: var(--text-muted);
                    ">{src.get('income_type', '').upper()}</span>
                </div>
                <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.5rem;">
                    {src.get('institution', '—')} • {src.get('account_type', '').title()}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
        
        # ── System Cost Budget ──────────────────────────────────────────────
        section_header("System Cost Budget", "🖥️", "#6366f1")
        
        system_costs = finance.get_system_costs()
        forecast = finance.forecast_system_costs()
        pct = system_costs.get("pct_used", 0)
        budget = system_costs.get("budget", 1000)
        
        # Visual gauge
        gauge_color = "#22c55e" if pct < 70 else "#f59e0b" if pct < 95 else "#ef4444"
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1.25rem;
                border-radius: 10px;
                border: 1px solid var(--border-default);
            ">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                    <span style="color: var(--text-muted);">This Month</span>
                    <span style="font-weight: 700; font-size: 1.25rem;">${system_costs.get('total', 0):,.0f}</span>
                </div>
                <div style="height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden;">
                    <div style="width: {min(100, pct)}%; height: 100%; background: {gauge_color}; border-radius: 4px;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
                    <span>{pct:.0f}% used</span>
                    <span>${budget:,.0f} budget</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.metric("Remaining", f"${system_costs.get('remaining', 0):,.0f}")
        with col3:
            proj_pct = forecast.get("projected_pct", 0)
            st.metric(
                "EOM Projection", 
                f"${forecast.get('projected_total', 0):,.0f}",
                delta=f"{proj_pct:.0f}%" if proj_pct > 0 else None,
                delta_color="inverse" if proj_pct > 85 else "normal"
            )
        
        if forecast.get("recommendations"):
            for rec in forecast["recommendations"]:
                st.warning(rec)
        
        st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
        
        # ── Spend Guardrails ────────────────────────────────────────────────
        section_header("Spend Guardrails", "🛡️", "#f59e0b")
        
        guardrails = finance.check_spend_guardrails()
        
        col1, col2 = st.columns(2)
        
        with col1:
            today = guardrails.get("today", {})
            today_pct = today.get("pct", 0)
            today_color = "#22c55e" if today_pct < 80 else "#f59e0b" if today_pct < 100 else "#ef4444"
            
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1.25rem;
                border-radius: 10px;
                border: 1px solid var(--border-default);
            ">
                <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Daily</div>
                <div style="font-size: 2rem; font-weight: 700; color: var(--text-primary);">${today.get('spent', 0):,.0f}</div>
                <div style="color: var(--text-muted); font-size: 0.875rem;">of ${today.get('cap', 150):,.0f} soft cap</div>
                <div style="margin-top: 0.75rem; height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden;">
                    <div style="width: {min(100, today_pct)}%; height: 100%; background: {today_color}; border-radius: 3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            month = guardrails.get("month", {})
            month_pct = month.get("pct", 0)
            month_color = "#22c55e" if month_pct < 70 else "#f59e0b" if month_pct < 85 else "#ef4444"
            
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1.25rem;
                border-radius: 10px;
                border: 1px solid var(--border-default);
            ">
                <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Monthly</div>
                <div style="font-size: 2rem; font-weight: 700; color: var(--text-primary);">${month.get('spent', 0):,.0f}</div>
                <div style="color: var(--text-muted); font-size: 0.875rem;">of ${month.get('limit', 10000):,.0f} target</div>
                <div style="margin-top: 0.75rem; height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden;">
                    <div style="width: {min(100, month_pct)}%; height: 100%; background: {month_color}; border-radius: 3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Warnings
        if guardrails.get("warnings"):
            st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
            for warning in guardrails["warnings"]:
                severity = warning.get("severity", "medium")
                if severity == "high":
                    st.error(f"🚨 {warning.get('message')}")
                else:
                    st.warning(f"⚠️ {warning.get('message')}")
        
        st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
        
        # ── Edit Settings ───────────────────────────────────────────────────
        section_header("Adjust Settings", "✏️", "#8b5cf6")
        
        with st.expander("Modify Limits", expanded=False):
            with st.form("update_guardrails"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_system = st.number_input(
                        "System Cost Budget ($)",
                        min_value=100.0,
                        value=float(finance_settings.get("system_cost_budget", 1000)),
                        step=100.0
                    )
                with col2:
                    new_monthly = st.number_input(
                        "Monthly Spend Limit ($)",
                        min_value=1000.0,
                        value=float(finance_settings.get("monthly_spend_limit", 10000)),
                        step=500.0
                    )
                with col3:
                    new_daily = st.number_input(
                        "Daily Soft Cap ($)",
                        min_value=10.0,
                        value=float(finance_settings.get("daily_soft_cap", 150)),
                        step=10.0
                    )
                
                if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                    result = finance.update_settings(
                        system_cost_budget=new_system,
                        monthly_spend_limit=new_monthly,
                        daily_soft_cap=new_daily
                    )
                    if result.get("success"):
                        success_toast("Settings saved!")
                        st.rerun()
        
        # ── Alerts ──────────────────────────────────────────────────────────
        alerts = finance.get_guardrail_alerts(unacknowledged_only=True)
        if alerts:
            st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
            section_header(f"Alerts ({len(alerts)})", "🔔", "#ef4444")
            
            for alert in alerts[:5]:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"""
                    <div style="
                        background: rgba(239, 68, 68, 0.1);
                        padding: 0.75rem 1rem;
                        border-radius: 8px;
                        border-left: 3px solid #ef4444;
                    ">
                        <div style="font-weight: 500; color: var(--text-primary);">{alert.get('message')}</div>
                        <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 0.25rem;">
                            {alert.get('created_at', '')[:10]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Acknowledge", key=f"ack_{alert.get('id')}", type="secondary"):
                        finance.acknowledge_alert(alert.get("id"))
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: PERSONAS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_personas:
    section_header("Persona Management", "👤", "#8b5cf6")
    
    from agents.persona_registry import get_persona_registry
    registry = get_persona_registry()
    
    personas = registry.list_personas(include_disabled=True)
    
    col1, col2 = st.columns(2)
    with col1:
        active_count = len([p for p in personas if p.get("state") == "active"])
        st.metric("Active Personas", active_count)
    with col2:
        st.metric("Total Personas", len(personas))
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    for persona in personas:
        state = persona.get("state", "unknown")
        icon = "🟢" if state == "active" else "⚪" if state == "disabled" else "🔴"
        score = persona.get("effectiveness_score")
        score_str = f"{score:.0%}" if score is not None else "—"
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1rem 1.25rem;
                border-radius: 8px;
                border: 1px solid var(--border-default);
                margin-bottom: 0.5rem;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="margin-right: 0.5rem;">{icon}</span>
                        <span style="font-weight: 600;">{persona.get('name', persona.get('id'))}</span>
                    </div>
                    <span style="color: var(--text-muted); font-size: 0.8rem;">Score: {score_str}</span>
                </div>
                <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 0.25rem;">
                    v{persona.get('version', 1)} • {state}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if state == "active":
                if st.button("Disable", key=f"disable_{persona.get('id')}", type="secondary"):
                    result = manager.disable_persona(persona.get("id"), "Disabled via Settings")
                    if result.get("success"):
                        success_toast(f"Disabled {persona.get('name')}")
                        st.rerun()
            elif state == "disabled":
                if st.button("Enable", key=f"enable_{persona.get('id')}", type="primary"):
                    result = manager.enable_persona(persona.get("id"), "Enabled via Settings")
                    if result.get("success"):
                        success_toast(f"Enabled {persona.get('name')}")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
with tab_system:
    
    # ══════════════════════════════════════════════════════════════════════════
    # MAIN SYSTEM CONTROLS - BIG BUTTONS AT TOP
    # ══════════════════════════════════════════════════════════════════════════
    
    # Check system status
    import subprocess
    try:
        api_check = subprocess.run(["pgrep", "-f", "uvicorn.*api.main"], capture_output=True, text=True)
        system_is_running = api_check.returncode == 0
    except Exception:
        system_is_running = False
    
    # Streamlit is always running if you're seeing this page
    streamlit_running = True
    
    # Overall status
    if system_is_running:
        status_text = "🟢 System Running"
        status_color = "#22c55e"
    else:
        status_text = "🟡 UI Only (API Stopped)"
        status_color = "#f59e0b"
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, var(--bg-surface) 100%);
        padding: 1.5rem;
        border-radius: 16px;
        border: 2px solid var(--accent-primary);
        margin-bottom: 1.5rem;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span style="font-size: 2rem;">🏠</span>
                <div>
                    <div style="font-size: 1.25rem; font-weight: 700;">MyCasa Pro</div>
                    <div style="color: {status_color}; font-weight: 500;">{status_text}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # TWO BIG BUTTONS: Launch / Turn Off - SIDE BY SIDE
    # Using HTML buttons for guaranteed visibility
    
    col_launch, col_off = st.columns(2)
    
    with col_launch:
        if system_is_running:
            st.markdown("""
            <div style="background: #22c55e; color: white; padding: 12px 24px; border-radius: 8px; 
                        text-align: center; font-weight: 600; font-size: 1rem;">
                ✅ System Running
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("🚀 Launch System", type="primary", use_container_width=True, key="main_launch_btn"):
                try:
                    subprocess.Popen(
                        ["python3", "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
                        cwd=str(APP_DIR),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    success_toast("🚀 System launching...")
                    import time
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to launch: {e}")
    
    with col_off:
        # Turn Off button
        if st.button("🛑 Turn Off & Save", type="secondary", use_container_width=True, key="main_off_btn"):
            st.session_state.confirm_turn_off = True
    
    # Turn Off confirmation
    if st.session_state.get("confirm_turn_off"):
        st.markdown("""
        <div style="
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid var(--accent-primary);
            border-radius: 12px;
            padding: 1.25rem;
            margin: 1rem 0;
        ">
            <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;">🛑 Turn Off MyCasa Pro</div>
            <div style="color: var(--text-secondary); font-size: 0.9rem;">This will:</div>
            <ul style="color: var(--text-secondary); font-size: 0.85rem; margin: 0.5rem 0 0 1rem;">
                <li>💾 Save current session to database</li>
                <li>📦 Create automatic backup</li>
                <li>🛑 Shut down the system</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        col_yes, col_no, _ = st.columns([1, 1, 2])
        with col_yes:
            if st.button("✅ Yes, Turn Off", type="primary", use_container_width=True, key="confirm_off_yes"):
                from datetime import datetime
                from database import get_db
                from database.models import AgentLog, Notification
                
                # Progress container
                progress_container = st.container()
                
                with progress_container:
                    st.markdown("### 🔄 Shutting down safely...")
                    
                    # Step 1: Save session
                    with st.spinner("💾 Step 1/3: Saving session..."):
                        try:
                            with get_db() as db:
                                log = AgentLog(
                                    agent="system",
                                    action="session_ended",
                                    details=f"System turned off at {datetime.now().isoformat()}",
                                    status="success"
                                )
                                db.add(log)
                        except Exception as e:
                            st.warning(f"Session log: {e}")
                    st.success("✅ Session saved")
                    
                    # Step 2: Create backup
                    with st.spinner("📦 Step 2/3: Creating backup..."):
                        try:
                            from agents.backup_recovery import BackupRecoveryAgent, BackupType
                            backup_agent = BackupRecoveryAgent()
                            backup_result = backup_agent.create_backup(
                                backup_type=BackupType.FULL,
                                notes=f"Auto-backup on shutdown at {datetime.now().strftime('%Y-%m-%d %I:%M %p')}",
                                created_by="system_shutdown"
                            )
                            backup_id = backup_result.get("id", "unknown")
                            st.success(f"✅ Backup created: {backup_id}")
                        except Exception as e:
                            st.warning(f"Backup skipped: {e}")
                            backup_id = None
                    
                    # Step 3: Create shutdown notification
                    with st.spinner("📝 Step 3/3: Finalizing..."):
                        try:
                            with get_db() as db:
                                notification = Notification(
                                    title="System Shutdown Complete",
                                    message=f"MyCasa Pro shut down at {datetime.now().strftime('%I:%M %p')}. Backup: {backup_id or 'skipped'}",
                                    category="system",
                                    priority="low"
                                )
                                db.add(notification)
                        except Exception:
                            pass
                        
                        # Stop backend API
                        try:
                            subprocess.run(["pkill", "-f", "uvicorn.*api.main"], capture_output=True)
                        except Exception:
                            pass
                    st.success("✅ Finalized")
                
                st.markdown("---")
                st.success("### ✅ All done! Shutting down in 3 seconds...")
                st.balloons()
                
                import time
                time.sleep(3)
                
                import os
                os._exit(0)
        
        with col_no:
            if st.button("❌ Cancel", use_container_width=True, key="confirm_off_no"):
                st.session_state.confirm_turn_off = False
                st.rerun()
    
    st.markdown("<div style='margin: 2rem 0; border-top: 1px solid var(--border-default);'></div>", unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT (more options)
    # ══════════════════════════════════════════════════════════════════════════
    
    section_header("Session Management", "💾", "#6366f1")
    
    # ── End Session & Save ───────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, var(--bg-surface) 100%);
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid var(--accent-primary);
        margin-bottom: 1.5rem;
    ">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
            <span style="font-size: 1.5rem;">💾</span>
            <span style="font-weight: 600; color: var(--text-primary); font-size: 1.1rem;">End Session & Save</span>
        </div>
        <div style="color: var(--text-muted); font-size: 0.85rem;">
            Save all current state to database, log session activity, and optionally shutdown.
            Your data will be preserved and ready when you return.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_save1, col_save2, col_save3 = st.columns([1, 1, 1])
    
    with col_save1:
        if st.button("💾 Save Session", type="primary", use_container_width=True, help="Save state without shutting down"):
            st.session_state.saving_session = True
    
    with col_save2:
        if st.button("💾 Save & Shutdown", use_container_width=True, help="Save state and shutdown"):
            st.session_state.save_and_shutdown = True
    
    with col_save3:
        if st.button("📊 View Session Stats", use_container_width=True, help="View current session info"):
            st.session_state.show_session_stats = True
    
    # Save session logic
    if st.session_state.get("saving_session") or st.session_state.get("save_and_shutdown"):
        from datetime import datetime
        from database import get_db
        from database.models import AgentLog, Notification
        
        with st.spinner("💾 Saving session..."):
            save_results = []
            
            # 1. Flush any pending database writes
            try:
                with get_db() as db:
                    db.commit()
                save_results.append("✅ Database committed")
            except Exception as e:
                save_results.append(f"⚠️ DB commit: {e}")
            
            # 2. Log session end
            try:
                with get_db() as db:
                    log = AgentLog(
                        agent="system",
                        action="session_ended",
                        details=f"Session ended at {datetime.now().isoformat()}",
                        status="success"
                    )
                    db.add(log)
                save_results.append("✅ Session logged")
            except Exception as e:
                save_results.append(f"⚠️ Log: {e}")
            
            # 3. Create session summary notification
            try:
                with get_db() as db:
                    # Get session stats
                    from database.models import MaintenanceTask, Bill, Notification as NotifModel
                    task_count = db.query(MaintenanceTask).filter(MaintenanceTask.status == "pending").count()
                    bill_count = db.query(Bill).filter(Bill.is_paid == False).count()
                    unread_count = db.query(NotifModel).filter(NotifModel.is_read == False).count()
                    
                    notification = Notification(
                        title="Session Saved",
                        message=f"Session saved at {datetime.now().strftime('%I:%M %p')}. Status: {task_count} pending tasks, {bill_count} unpaid bills, {unread_count} unread notifications.",
                        category="system",
                        priority="low"
                    )
                    db.add(notification)
                save_results.append("✅ Session snapshot created")
            except Exception as e:
                save_results.append(f"⚠️ Snapshot: {e}")
            
            # 4. Clear caches to ensure fresh data on reload
            clear_all_caches()
            save_results.append("✅ Caches cleared")
        
        # Show results
        st.success("**Session saved successfully!**")
        for result in save_results:
            st.markdown(f"<div style='font-size: 0.85rem; padding: 0.2rem 0;'>{result}</div>", unsafe_allow_html=True)
        
        # If save & shutdown, proceed to shutdown
        if st.session_state.get("save_and_shutdown"):
            st.info("🛑 Shutting down in 3 seconds...")
            import time
            time.sleep(3)
            import os
            os._exit(0)
        else:
            st.session_state.saving_session = False
            if st.button("✅ Done", use_container_width=True):
                st.rerun()
    
    # Session stats display
    if st.session_state.get("show_session_stats"):
        from datetime import datetime
        from database import get_db
        from database.models import AgentLog, Notification as NotifModel, MaintenanceTask, Bill, PortfolioHolding
        
        with get_db() as db:
            # Get stats
            task_pending = db.query(MaintenanceTask).filter(MaintenanceTask.status == "pending").count()
            task_completed = db.query(MaintenanceTask).filter(MaintenanceTask.status == "completed").count()
            bills_unpaid = db.query(Bill).filter(Bill.is_paid == False).count()
            bills_paid = db.query(Bill).filter(Bill.is_paid == True).count()
            notifications_total = db.query(NotifModel).count()
            notifications_unread = db.query(NotifModel).filter(NotifModel.is_read == False).count()
            agent_logs = db.query(AgentLog).count()
            holdings = db.query(PortfolioHolding).count()
            
            # Last session end
            last_session = db.query(AgentLog).filter(
                AgentLog.action == "session_ended"
            ).order_by(AgentLog.created_at.desc()).first()
            last_session_time = last_session.created_at.strftime('%Y-%m-%d %I:%M %p') if last_session else "Never"
        
        st.markdown(f"""
        <div style="
            background: var(--bg-surface);
            padding: 1.25rem;
            border-radius: 10px;
            border: 1px solid var(--border-default);
            margin: 1rem 0;
        ">
            <div style="font-weight: 600; margin-bottom: 1rem;">📊 Session Statistics</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.9rem;">
                <div>🗓️ Tasks: <strong>{task_pending}</strong> pending / {task_completed} done</div>
                <div>💳 Bills: <strong>{bills_unpaid}</strong> unpaid / {bills_paid} paid</div>
                <div>🔔 Notifications: <strong>{notifications_unread}</strong> unread / {notifications_total} total</div>
                <div>📈 Portfolio: <strong>{holdings}</strong> holdings</div>
                <div>📝 Agent logs: <strong>{agent_logs}</strong></div>
                <div>⏱️ Last save: <strong>{last_session_time}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Close", key="close_stats"):
            st.session_state.show_session_stats = False
            st.rerun()
    
    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
    
    section_header("System Information", "🔧", "#22c55e")
    
    # ── Backend API Controls ───────────────────────────────────────────────
    section_header("Backend API", "🔌", "#8b5cf6")
    
    # Check if backend API is running
    import subprocess
    try:
        result = subprocess.run(["pgrep", "-f", "uvicorn.*api.main"], capture_output=True, text=True)
        backend_running = result.returncode == 0
    except Exception:
        backend_running = False
    
    api_status_color = "#22c55e" if backend_running else "#6b7280"
    api_status_text = "Running" if backend_running else "Stopped"
    api_status_icon = "🟢" if backend_running else "⚪"
    
    st.markdown(f"""
    <div style="
        background: var(--bg-surface);
        padding: 1rem 1.25rem;
        border-radius: 10px;
        border: 1px solid {api_status_color};
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    ">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span>{api_status_icon}</span>
            <div>
                <div style="font-weight: 600;">Backend API</div>
                <div style="color: var(--text-muted); font-size: 0.8rem;">FastAPI @ localhost:8000</div>
            </div>
        </div>
        <span style="
            background: {'rgba(34, 197, 94, 0.15)' if backend_running else 'var(--bg-secondary)'};
            color: {'#22c55e' if backend_running else 'var(--text-muted)'};
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
        ">{api_status_text}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_api1, col_api2, col_api3 = st.columns([1, 1, 1])
    
    with col_api1:
        if not backend_running:
            if st.button("🚀 Launch API", type="primary", use_container_width=True):
                try:
                    import os
                    subprocess.Popen(
                        ["python3", "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
                        cwd=str(APP_DIR),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                    success_toast("Backend API starting...")
                    import time
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start API: {e}")
        else:
            if st.button("🛑 Stop API", use_container_width=True):
                try:
                    subprocess.run(["pkill", "-f", "uvicorn.*api.main"], capture_output=True)
                    success_toast("Backend API stopped")
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to stop API: {e}")
    
    with col_api2:
        if st.button("🔄 Restart API", use_container_width=True, disabled=not backend_running):
            try:
                subprocess.run(["pkill", "-f", "uvicorn.*api.main"], capture_output=True)
                import time
                time.sleep(1)
                subprocess.Popen(
                    ["python3", "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
                    cwd=str(APP_DIR),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                success_toast("Backend API restarting...")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to restart API: {e}")
    
    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════════════════════
    # JANITOR HEALTH REPORT
    # ══════════════════════════════════════════════════════════════════════════
    
    section_header("System Health (Janitor)", "🔍", "#f59e0b")
    
    try:
        from agents.janitor import JanitorAgent
        janitor = JanitorAgent()
        janitor_status = janitor.get_status()
        janitor_metrics = janitor_status.get("metrics", {})
        
        # Health indicator
        health = janitor_status.get("health", "unknown")
        health_colors = {
            "healthy": ("#22c55e", "🟢"),
            "warning": ("#f59e0b", "🟡"),
            "degraded": ("#f97316", "🟠"),
            "critical": ("#ef4444", "🔴"),
            "unknown": ("#6b7280", "⚪")
        }
        health_color, health_icon = health_colors.get(health, health_colors["unknown"])
        
        # Health card
        st.markdown(f"""
        <div style="
            background: var(--bg-surface);
            padding: 1.25rem;
            border-radius: 12px;
            border: 2px solid {health_color};
            margin-bottom: 1rem;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.5rem;">{health_icon}</span>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: {health_color};">
                            System {health.upper()}
                        </div>
                        <div style="color: var(--text-muted); font-size: 0.8rem;">
                            Last audit: {janitor_metrics.get('last_audit', 'Never')[:19] if janitor_metrics.get('last_audit') else 'Never'}
                        </div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Agents Monitored</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">{janitor_metrics.get('agents_monitored', 0)}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics grid
        col_j1, col_j2, col_j3, col_j4 = st.columns(4)
        
        with col_j1:
            incidents = janitor_metrics.get('open_incidents', 0)
            inc_color = "#ef4444" if incidents > 0 else "#22c55e"
            st.markdown(f"""
            <div style="background: var(--bg-surface); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-default); text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700; color: {inc_color};">{incidents}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Open Incidents</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_j2:
            p0 = janitor_metrics.get('p0_incidents', 0)
            p1 = janitor_metrics.get('p1_incidents', 0)
            crit_color = "#ef4444" if p0 > 0 else "#f59e0b" if p1 > 0 else "#22c55e"
            st.markdown(f"""
            <div style="background: var(--bg-surface); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-default); text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700; color: {crit_color};">P0:{p0} P1:{p1}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Critical/Major</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_j3:
            today_cost = janitor_metrics.get('today_cost', 0)
            st.markdown(f"""
            <div style="background: var(--bg-surface); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-default); text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700;">${today_cost:.2f}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Today's Cost</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_j4:
            month_pct = janitor_metrics.get('month_pct', 0)
            month_cost = janitor_metrics.get('month_cost', 0)
            budget_color = "#22c55e" if month_pct < 70 else "#f59e0b" if month_pct < 90 else "#ef4444"
            st.markdown(f"""
            <div style="background: var(--bg-surface); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-default); text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 700; color: {budget_color};">{month_pct:.0f}%</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Monthly Budget (${month_cost:.0f})</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
        
        # Action buttons
        col_audit, col_report, _ = st.columns([1, 1, 2])
        
        with col_audit:
            if st.button("🔍 Run Audit", use_container_width=True, key="run_janitor_audit"):
                with st.spinner("Running system audit..."):
                    audit_result = janitor.run_audit()
                st.session_state.janitor_audit_result = audit_result
                success_toast("Audit complete!")
        
        with col_report:
            if st.button("📊 Full Report", use_container_width=True, key="show_janitor_report"):
                st.session_state.show_janitor_report = True
        
        # Show audit results
        if st.session_state.get("janitor_audit_result"):
            audit = st.session_state.janitor_audit_result
            with st.expander("📋 Audit Results", expanded=True):
                st.markdown(f"**Audit Time:** {audit.get('audit_time', 'N/A')}")
                st.markdown(f"**Agents Checked:** {', '.join(audit.get('agents_checked', []))}")
                
                findings = audit.get("findings", [])
                if findings:
                    st.markdown("**Findings:**")
                    for finding in findings:
                        severity_icon = "🔴" if finding["severity"] == "P0" else "🟠" if finding["severity"] == "P1" else "🟡"
                        st.markdown(f"- {severity_icon} **[{finding['severity']}]** {finding['finding']}")
                else:
                    st.success("✅ No issues found!")
                
                if st.button("Clear", key="clear_audit"):
                    st.session_state.janitor_audit_result = None
                    st.rerun()
        
        # Show full report
        if st.session_state.get("show_janitor_report"):
            with st.expander("📊 Full Health Report", expanded=True):
                report_text = janitor.get_health_report()
                st.code(report_text, language=None)
                
                if st.button("Close Report", key="close_janitor_report"):
                    st.session_state.show_janitor_report = False
                    st.rerun()
    
    except Exception as e:
        st.error(f"Could not load Janitor agent: {e}")
    
    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
    
    # ── Shutdown Controls ───────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: rgba(239, 68, 68, 0.08);
        padding: 1rem 1.25rem;
        border-radius: 10px;
        border: 1px solid rgba(239, 68, 68, 0.3);
        margin-bottom: 1.5rem;
    ">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
            <span style="font-size: 1.25rem;">⚠️</span>
            <span style="font-weight: 600; color: var(--text-primary);">Danger Zone</span>
        </div>
        <div style="color: var(--text-muted); font-size: 0.8rem;">
            Force shutdown without saving. Use "Save & Shutdown" above for safe exit.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_shutdown1, col_shutdown2, col_shutdown3 = st.columns([1, 1, 2])
    with col_shutdown1:
        if st.button("🛑 Force Shutdown", type="secondary", use_container_width=True):
            st.session_state.confirm_shutdown = True
    with col_shutdown2:
        if st.button("🔄 Restart Agents", use_container_width=True):
            st.session_state.confirm_restart = True
    
    # Shutdown confirmation
    if st.session_state.get("confirm_shutdown"):
        st.warning("⚠️ Are you sure you want to shutdown MyCasa Pro?")
        col_yes, col_no, _ = st.columns([1, 1, 4])
        with col_yes:
            if st.button("✅ Yes, Shutdown", type="primary", use_container_width=True):
                import subprocess
                import os
                
                # Stop the backend API
                try:
                    subprocess.run(["pkill", "-f", "uvicorn.*mycasa"], check=False)
                except Exception:
                    pass
                
                # Stop Streamlit (this app)
                st.success("🛑 Shutting down MyCasa Pro...")
                st.balloons()
                
                # Give user time to see the message
                import time
                time.sleep(2)
                
                # Exit the Streamlit app
                os._exit(0)
        with col_no:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.confirm_shutdown = False
                st.rerun()
    
    # Restart confirmation
    if st.session_state.get("confirm_restart"):
        st.info("🔄 This will restart all agents. Continue?")
        col_yes, col_no, _ = st.columns([1, 1, 4])
        with col_yes:
            if st.button("✅ Yes, Restart", type="primary", use_container_width=True, key="confirm_restart_yes"):
                # Clear agent instances to force reload
                try:
                    import sys
                    # Remove cached agent modules to force reimport
                    modules_to_remove = [k for k in sys.modules.keys() if 'agents.' in k]
                    for mod in modules_to_remove:
                        del sys.modules[mod]
                except Exception:
                    pass
                
                clear_all_caches()
                st.session_state.confirm_restart = False
                success_toast("Agents restarted!")
                st.rerun()
        with col_no:
            if st.button("❌ Cancel", use_container_width=True, key="confirm_restart_no"):
                st.session_state.confirm_restart = False
                st.rerun()
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Database")
        db_path = APP_DIR / "data" / "mycasa_pro.db"
        if db_path.exists():
            size_kb = db_path.stat().st_size / 1024
            st.markdown(f"""
            <div style="
                background: var(--bg-surface);
                padding: 1rem;
                border-radius: 8px;
                border: 1px solid var(--border-default);
            ">
                <div style="color: var(--text-muted); font-size: 0.75rem;">PATH</div>
                <div style="font-family: monospace; font-size: 0.8rem; word-break: break-all;">{db_path}</div>
                <div style="margin-top: 0.75rem; color: var(--text-muted); font-size: 0.75rem;">SIZE</div>
                <div style="font-weight: 500;">{size_kb:.1f} KB</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Database not found")
    
    with col2:
        st.markdown("##### Cache TTLs")
        st.markdown("""
        <div style="
            background: var(--bg-surface);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid var(--border-default);
        ">
            <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                <span style="color: var(--text-muted);">Dashboard</span>
                <span>60s</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                <span style="color: var(--text-muted);">Portfolio</span>
                <span>300s</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
                <span style="color: var(--text-muted);">Tasks/Bills</span>
                <span>30s</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin: 0.75rem 0;'></div>", unsafe_allow_html=True)
        
        if st.button("🗑️ Clear All Caches", use_container_width=True):
            clear_all_caches()
            success_toast("Caches cleared!")
            st.rerun()
    
    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
    
    section_header("Galidima Connection", "🤖", "#6366f1")
    
    galidima = status.get("galidima_connected")
    
    st.markdown(f"""
    <div style="
        background: var(--bg-surface);
        padding: 1rem 1.25rem;
        border-radius: 8px;
        border: 1px solid {'#22c55e' if galidima else 'var(--border-default)'};
        display: flex;
        align-items: center;
        gap: 0.75rem;
    ">
        <span style="font-size: 1.5rem;">{'✅' if galidima else '⏳' if galidima is None else '⚠️'}</span>
        <div>
            <div style="font-weight: 500;">{'Connected to Galidima' if galidima else 'Not checked' if galidima is None else 'Not connected'}</div>
            <div style="color: var(--text-muted); font-size: 0.8rem;">Clawdbot AI Assistant</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
