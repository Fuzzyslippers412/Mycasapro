"""
MyCasa Pro - Finance Page
Bills, portfolio tracking, budgets, and system costs
"""
import streamlit as st
from pathlib import Path
import sys

APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

from datetime import date
from components.layout import page_header, empty_state, section_header, success_toast
from components.cards import bill_card
from components.charts import portfolio_donut, holdings_table, portfolio_performance_chart
from components.forms import bill_form
from hooks.use_data import use_portfolio_data, clear_all_caches

# Page config
st.set_page_config(page_title="Finance - MyCasa Pro", page_icon="💰", layout="wide")

# Load CSS
css_file = APP_DIR / "static" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

# Load Finance Agent
from agents.finance import FinanceAgent
finance = FinanceAgent()

# Check intake status
intake_complete = finance.is_intake_complete()

# Header with status indicator
if intake_complete:
    page_header("Finance", "💰", "Bills, portfolio, and spending")
else:
    page_header("Finance", "💰", "Complete setup to unlock all features")

# ═══════════════════════════════════════════════════════════════════════════════
# INTAKE REQUIRED BANNER
# ═══════════════════════════════════════════════════════════════════════════════
if not intake_complete:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, var(--bg-surface) 100%);
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        border: 1px solid #f59e0b;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    ">
        <span style="font-size: 1.75rem;">⚙️</span>
        <div style="flex: 1;">
            <div style="font-weight: 600; color: var(--text-primary);">Finance Manager Setup Required</div>
            <div style="color: var(--text-muted); font-size: 0.875rem;">
                Complete the one-time setup to enable spend tracking, guardrails, and system cost monitoring
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Complete Setup", type="primary", use_container_width=False):
        st.switch_page("pages/6_⚙️_Settings.py")
    
    st.markdown("<div style='margin: 0.5rem 0;'></div>", unsafe_allow_html=True)
    st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL ALERTS (if intake complete)
# ═══════════════════════════════════════════════════════════════════════════════
if intake_complete:
    guardrails = finance.check_spend_guardrails()
    system_costs = finance.get_system_costs()
    
    # Show combined status bar
    has_warnings = guardrails.get("warnings") or system_costs.get("status") in ["warning", "critical"]
    
    if has_warnings:
        st.markdown("""
        <div style="
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
        ">
        """, unsafe_allow_html=True)
        
        for warning in guardrails.get("warnings", []):
            severity = warning.get("severity", "medium")
            icon = "🚨" if severity == "high" else "⚠️"
            st.markdown(f"<div style='color: #ef4444; font-weight: 500;'>{icon} {warning.get('message')}</div>", unsafe_allow_html=True)
        
        if system_costs.get("status") == "critical":
            st.markdown(f"<div style='color: #ef4444; font-weight: 500;'>🚨 System costs at {system_costs.get('pct_used', 0):.0f}% — approaching budget limit</div>", unsafe_allow_html=True)
        elif system_costs.get("status") == "warning":
            st.markdown(f"<div style='color: #f59e0b; font-weight: 500;'>⚠️ System costs at {system_costs.get('pct_used', 0):.0f}% of monthly budget</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# Initialize session state
if "show_bill_form" not in st.session_state:
    st.session_state.show_bill_form = False

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_bills, tab_portfolio, tab_budgets, tab_costs = st.tabs([
    "💳 Bills", 
    "📈 Portfolio", 
    "📊 Budgets", 
    "🖥️ System Costs"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: BILLS
# ─────────────────────────────────────────────────────────────────────────────
with tab_bills:
    with st.spinner("Loading bills..."):
        bills = finance.get_bills()
        upcoming = finance.get_upcoming_bills(30)
    
    # Stats row
    unpaid = [b for b in bills if not b.get("is_paid")]
    overdue = [b for b in unpaid if b.get("due_date") and date.fromisoformat(b["due_date"]) < date.today()]
    total_due = sum(b.get("amount", 0) for b in unpaid)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Unpaid", len(unpaid))
    with col2:
        st.metric("Overdue", len(overdue), delta=f"{len(overdue)}" if overdue else None, delta_color="inverse")
    with col3:
        st.metric("Due in 30 Days", len(upcoming))
    with col4:
        st.metric("Total Due", f"${total_due:,.0f}")
    
    st.markdown("<div style='margin: 1.25rem 0;'></div>", unsafe_allow_html=True)
    
    # Add bill button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("➕ Add Bill", type="primary", use_container_width=True):
            st.session_state.show_bill_form = True
    
    # Bill form
    if st.session_state.show_bill_form:
        with st.expander("New Bill", expanded=True):
            result = bill_form(finance)
            if result:
                if result.get("success"):
                    success_toast("Bill added!")
                    st.session_state.show_bill_form = False
                    clear_all_caches()
                    st.rerun()
                else:
                    st.error(result.get("error", "Failed to add bill"))
            
            if st.button("Cancel", key="cancel_bill"):
                st.session_state.show_bill_form = False
                st.rerun()
    
    st.markdown("<div style='margin: 1.25rem 0;'></div>", unsafe_allow_html=True)
    
    # Overdue bills
    if overdue:
        section_header(f"Overdue ({len(overdue)})", "🚨", "#ef4444")
        
        for bill in overdue:
            col1, col2 = st.columns([5, 1])
            with col1:
                bill_card(
                    name=bill.get("name", "Bill"),
                    amount=bill.get("amount", 0),
                    due_date=bill.get("due_date"),
                    days_until=bill.get("days_until_due"),
                    is_paid=False,
                    auto_pay=bill.get("auto_pay", False)
                )
            with col2:
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("Pay", key=f"pay_overdue_{bill.get('id')}", type="primary", use_container_width=True):
                    result = finance.pay_bill(bill.get("id"))
                    if result.get("success"):
                        success_toast(f"Paid {bill.get('name')}!")
                        clear_all_caches()
                        st.rerun()
        
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Upcoming bills
    section_header("Upcoming", "📅", "#6366f1")
    upcoming_unpaid = [b for b in upcoming if not b.get("is_paid") and b not in overdue]
    
    if upcoming_unpaid:
        for bill in upcoming_unpaid:
            col1, col2 = st.columns([5, 1])
            with col1:
                bill_card(
                    name=bill.get("name", "Bill"),
                    amount=bill.get("amount", 0),
                    due_date=bill.get("due_date"),
                    days_until=bill.get("days_until_due"),
                    is_paid=False,
                    auto_pay=bill.get("auto_pay", False)
                )
            with col2:
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                if st.button("Pay", key=f"pay_{bill.get('id')}", use_container_width=True):
                    result = finance.pay_bill(bill.get("id"))
                    if result.get("success"):
                        success_toast(f"Paid {bill.get('name')}!")
                        clear_all_caches()
                        st.rerun()
    else:
        empty_state("No upcoming bills", "🎉")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────
with tab_portfolio:
    with st.spinner("Loading portfolio..."):
        portfolio = use_portfolio_data()
    
    if portfolio.get("error"):
        st.warning(f"Portfolio data unavailable: {portfolio.get('error')}")
        st.info("Install yfinance for real-time data: `pip install yfinance`")
    else:
        holdings = portfolio.get("holdings", [])
        total_value = portfolio.get("total_value", 0)
        
        # Portfolio actions
        col_actions1, col_actions2, col_actions3 = st.columns([1, 1, 4])
        with col_actions1:
            if st.button("🗑️ Clear Portfolio", type="secondary", use_container_width=True):
                st.session_state.confirm_clear_portfolio = True
        with col_actions2:
            if st.button("🔄 Refresh", use_container_width=True):
                clear_all_caches()
                st.rerun()
        
        # Confirmation dialog
        if st.session_state.get("confirm_clear_portfolio"):
            st.warning("⚠️ Are you sure you want to clear all portfolio holdings?")
            col_yes, col_no, _ = st.columns([1, 1, 4])
            with col_yes:
                if st.button("✅ Yes, Clear", type="primary", use_container_width=True):
                    result = finance.clear_portfolio()
                    if result.get("success"):
                        success_toast(result.get("message", "Portfolio cleared!"))
                        st.session_state.confirm_clear_portfolio = False
                        clear_all_caches()
                        st.rerun()
                    else:
                        st.error(result.get("error", "Failed to clear portfolio"))
            with col_no:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.confirm_clear_portfolio = False
                    st.rerun()
        
        st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Value", f"${total_value:,.0f}" if total_value else "—")
        with col2:
            st.metric("Positions", len(holdings))
        with col3:
            daily_change = portfolio.get("daily_change_pct", 0)
            st.metric(
                "Today", 
                f"{daily_change:+.2f}%" if daily_change else "—",
                delta=f"{daily_change:+.2f}%" if daily_change else None,
                delta_color="normal" if daily_change and daily_change >= 0 else "inverse"
            )
        
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # Charts side by side
        col1, col2 = st.columns(2)
        
        with col1:
            section_header("Allocation", "🥧", "#8b5cf6")
            if holdings:
                portfolio_donut(holdings)
            else:
                empty_state("No data", "📊")
        
        with col2:
            section_header("Performance", "📈", "#22c55e")
            if holdings:
                portfolio_performance_chart(holdings)
            else:
                empty_state("No data", "📈")
        
        # Holdings table
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        section_header("Holdings", "📋", "#6366f1")
        
        if holdings:
            holdings_table(holdings)
        else:
            empty_state("No holdings to display", "💼")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: BUDGETS
# ─────────────────────────────────────────────────────────────────────────────
with tab_budgets:
    section_header("Budget Tracking", "📊", "#f59e0b")
    
    with st.spinner("Loading budgets..."):
        budgets = finance.get_budget_status()
    
    if budgets:
        from components.charts import budget_bars
        budget_bars(budgets)
    else:
        empty_state(
            "No budgets configured yet",
            "📊",
            "Set Up Budgets",
            "setup_budgets"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: SYSTEM COSTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_costs:
    section_header("MyCasa Pro Operating Costs", "🖥️", "#6366f1")
    
    if not intake_complete:
        empty_state(
            "Complete Finance Manager setup to track system costs",
            "🔒",
            "Complete Setup",
            "go_to_setup"
        )
        if st.session_state.get("go_to_setup"):
            st.switch_page("pages/6_⚙️_Settings.py")
    else:
        # Load data
        system_costs = finance.get_system_costs()
        forecast = finance.forecast_system_costs()
        
        pct = system_costs.get("pct_used", 0)
        budget = system_costs.get("budget", 1000)
        total = system_costs.get("total", 0)
        remaining = system_costs.get("remaining", 0)
        
        # Status indicator
        status_color = "#22c55e" if pct < 70 else "#f59e0b" if pct < 95 else "#ef4444"
        status_text = "On Track" if pct < 70 else "Watch" if pct < 95 else "Critical"
        
        # Stats row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("This Month", f"${total:,.2f}")
        with col2:
            st.metric("Budget", f"${budget:,.0f}")
        with col3:
            st.metric("Remaining", f"${remaining:,.2f}")
        with col4:
            st.metric("Status", f"{pct:.0f}%", delta=status_text, 
                     delta_color="normal" if pct < 70 else "off" if pct < 95 else "inverse")
        
        st.markdown("<div style='margin: 1.25rem 0;'></div>", unsafe_allow_html=True)
        
        # Progress visualization
        st.markdown(f"""
        <div style="
            background: var(--bg-surface);
            padding: 1.25rem;
            border-radius: 10px;
            border: 1px solid var(--border-default);
            margin-bottom: 1.5rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <span style="font-weight: 500;">Budget Usage</span>
                <span style="
                    background: {status_color}20;
                    color: {status_color};
                    padding: 0.25rem 0.75rem;
                    border-radius: 12px;
                    font-size: 0.8rem;
                    font-weight: 600;
                ">{pct:.1f}%</span>
            </div>
            <div style="height: 12px; background: var(--bg-secondary); border-radius: 6px; overflow: hidden;">
                <div style="
                    width: {min(100, pct)}%; 
                    height: 100%; 
                    background: linear-gradient(90deg, {status_color}, {status_color}dd);
                    border-radius: 6px;
                    transition: width 0.3s ease;
                "></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
                <span>$0</span>
                <span>${budget:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Forecast section
        section_header("Projection", "📈", "#8b5cf6")
        
        proj_total = forecast.get("projected_total", 0)
        proj_pct = forecast.get("projected_pct", 0)
        daily_rate = forecast.get("daily_rate", 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Daily Burn Rate", f"${daily_rate:.2f}")
        with col2:
            st.metric(
                "End of Month", 
                f"${proj_total:,.0f}",
                delta=f"{proj_pct:.0f}% of budget",
                delta_color="normal" if proj_pct < 85 else "inverse"
            )
        with col3:
            days_remaining = 30 - forecast.get("days_elapsed", 0)
            st.metric("Days Remaining", days_remaining)
        
        # Recommendations
        if forecast.get("recommendations"):
            st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
            for rec in forecast["recommendations"]:
                st.info(rec)
        
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # Breakdown sections
        col1, col2 = st.columns(2)
        
        with col1:
            by_category = system_costs.get("by_category", {})
            if by_category:
                section_header("By Category", "📊", "#22c55e")
                
                for cat, amount in by_category.items():
                    cat_pct = (amount / total * 100) if total > 0 else 0
                    cat_label = cat.replace('_', ' ').title()
                    
                    st.markdown(f"""
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 0.75rem 1rem;
                        background: var(--bg-surface);
                        border-radius: 8px;
                        margin-bottom: 0.5rem;
                        border: 1px solid var(--border-default);
                    ">
                        <span style="font-weight: 500;">{cat_label}</span>
                        <div style="text-align: right;">
                            <span style="font-weight: 600;">${amount:,.2f}</span>
                            <span style="color: var(--text-muted); margin-left: 0.5rem; font-size: 0.8rem;">({cat_pct:.0f}%)</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            by_service = system_costs.get("by_service", {})
            if by_service:
                section_header("By Service", "🔧", "#f59e0b")
                
                for service, amount in by_service.items():
                    svc_pct = (amount / total * 100) if total > 0 else 0
                    
                    st.markdown(f"""
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 0.75rem 1rem;
                        background: var(--bg-surface);
                        border-radius: 8px;
                        margin-bottom: 0.5rem;
                        border: 1px solid var(--border-default);
                    ">
                        <span style="font-weight: 500;">{service}</span>
                        <div style="text-align: right;">
                            <span style="font-weight: 600;">${amount:,.2f}</span>
                            <span style="color: var(--text-muted); margin-left: 0.5rem; font-size: 0.8rem;">({svc_pct:.0f}%)</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # Add cost entry
        with st.expander("➕ Record System Cost", expanded=False):
            with st.form("add_system_cost", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    cost_amount = st.number_input("Amount ($)", min_value=0.01, step=1.0, format="%.2f")
                    cost_category = st.selectbox(
                        "Category", 
                        ["ai_api", "hosting", "storage", "integrations"],
                        format_func=lambda x: x.replace('_', ' ').title()
                    )
                with col2:
                    cost_service = st.text_input("Service Name", placeholder="e.g., Claude API, AWS")
                    cost_desc = st.text_input("Description", placeholder="Optional notes")
                
                submitted = st.form_submit_button("Add Cost", type="primary", use_container_width=True)
                
                if submitted:
                    if cost_amount <= 0:
                        st.error("Amount must be greater than 0")
                    else:
                        result = finance.add_system_cost(
                            amount=cost_amount,
                            category=cost_category,
                            service_name=cost_service.strip() if cost_service else None,
                            description=cost_desc.strip() if cost_desc else None
                        )
                        if result.get("success"):
                            success_toast("Cost recorded!")
                            clear_all_caches()
                            st.rerun()
                        else:
                            st.error("Failed to record cost")
