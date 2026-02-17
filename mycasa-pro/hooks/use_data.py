"""
Data fetching hooks with caching for MyCasa Pro
"""
import streamlit as st
from typing import Dict, List, Any


@st.cache_data(ttl=60)
def use_dashboard_data() -> Dict[str, Any]:
    """Fetch dashboard data with 60s cache"""
    from agents.manager import ManagerAgent
    manager = ManagerAgent()
    return manager.get_dashboard_summary()


@st.cache_data(ttl=300)
def use_portfolio_data() -> Dict[str, Any]:
    """Fetch portfolio data with 5-min cache (API calls)"""
    from agents.finance import FinanceAgent
    finance = FinanceAgent()
    return finance.get_portfolio_summary()


@st.cache_data(ttl=30)
def use_tasks_data() -> List[Dict[str, Any]]:
    """Fetch maintenance tasks with 30s cache"""
    from agents.maintenance import MaintenanceAgent
    maintenance = MaintenanceAgent()
    return maintenance.get_pending_tasks()


@st.cache_data(ttl=30)
def use_bills_data() -> List[Dict[str, Any]]:
    """Fetch bills with 30s cache"""
    from agents.finance import FinanceAgent
    finance = FinanceAgent()
    return finance.get_bills()


@st.cache_data(ttl=60)
def use_contractors_data() -> List[Dict[str, Any]]:
    """Fetch contractors with 60s cache"""
    from agents.contractors import ContractorsAgent
    contractors = ContractorsAgent()
    return contractors.get_contractors()


@st.cache_data(ttl=60)
def use_projects_data() -> List[Dict[str, Any]]:
    """Fetch projects with 60s cache"""
    from agents.projects import ProjectsAgent
    projects = ProjectsAgent()
    return projects.get_projects()


@st.cache_resource
def use_manager():
    """Get cached manager instance"""
    from agents.manager import ManagerAgent
    return ManagerAgent()


def clear_all_caches():
    """Clear all data caches"""
    use_dashboard_data.clear()
    use_portfolio_data.clear()
    use_tasks_data.clear()
    use_bills_data.clear()
    use_contractors_data.clear()
    use_projects_data.clear()
