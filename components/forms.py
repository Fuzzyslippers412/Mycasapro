"""
Form Components for MyCasa Pro
"""
import streamlit as st
from datetime import date, timedelta
from typing import List, Dict, Any, Optional


def task_form(
    contractors: List[Dict[str, Any]] = None,
    categories: List[str] = None,
    key_prefix: str = "task"
) -> Optional[Dict[str, Any]]:
    """Task creation form"""
    
    if categories is None:
        categories = ["cleaning", "yard", "plumbing", "electrical", "hvac", 
                     "appliance", "pest_control", "security", "general"]
    
    with st.form(key=f"{key_prefix}_form"):
        st.subheader("📋 New Task")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Title*", placeholder="e.g., Clean gutters")
            category = st.selectbox("Category", categories)
            priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"], index=1)
        
        with col2:
            scheduled_date = st.date_input("Scheduled Date", value=date.today())
            due_date = st.date_input("Due Date", value=date.today() + timedelta(days=7))
            recurrence = st.selectbox(
                "Recurrence", 
                ["none", "daily", "weekly", "biweekly", "monthly", "quarterly", "yearly"]
            )
        
        description = st.text_area("Description", placeholder="Task details...")
        
        col3, col4 = st.columns(2)
        with col3:
            estimated_cost = st.number_input("Estimated Cost ($)", min_value=0.0, step=10.0)
        with col4:
            if contractors:
                contractor_options = {c["name"]: c["id"] for c in contractors}
                contractor_name = st.selectbox("Assign Contractor", ["None"] + list(contractor_options.keys()))
                contractor_id = contractor_options.get(contractor_name) if contractor_name != "None" else None
            else:
                contractor_id = None
                st.info("No contractors available")
        
        notes = st.text_input("Notes", placeholder="Additional notes...")
        
        submitted = st.form_submit_button("✅ Create Task", use_container_width=True)
        
        if submitted and title:
            return {
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "scheduled_date": scheduled_date,
                "due_date": due_date,
                "recurrence": recurrence,
                "estimated_cost": estimated_cost if estimated_cost > 0 else None,
                "contractor_id": contractor_id,
                "notes": notes
            }
    
    return None


def bill_form(key_prefix: str = "bill") -> Optional[Dict[str, Any]]:
    """Bill creation form"""
    
    categories = ["utilities", "insurance", "subscription", "mortgage", "rent", 
                 "phone", "internet", "credit_card", "tax", "other"]
    
    with st.form(key=f"{key_prefix}_form"):
        st.subheader("💳 New Bill")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Bill Name*", placeholder="e.g., Electric Bill")
            category = st.selectbox("Category", categories)
            payee = st.text_input("Payee", placeholder="e.g., PSE")
        
        with col2:
            amount = st.number_input("Amount ($)*", min_value=0.01, step=10.0)
            due_date = st.date_input("Due Date*", value=date.today() + timedelta(days=14))
            payment_method = st.text_input("Payment Method", placeholder="e.g., Credit Card")
        
        col3, col4 = st.columns(2)
        with col3:
            is_recurring = st.checkbox("Recurring Bill")
        with col4:
            auto_pay = st.checkbox("Auto-Pay Enabled")
        
        if is_recurring:
            recurrence = st.selectbox(
                "Recurrence Frequency",
                ["weekly", "biweekly", "monthly", "quarterly", "yearly"],
                index=2
            )
        else:
            recurrence = None
        
        notes = st.text_input("Notes", placeholder="Additional notes...")
        
        submitted = st.form_submit_button("✅ Add Bill", use_container_width=True)
        
        if submitted and name and amount > 0:
            return {
                "name": name,
                "amount": amount,
                "due_date": due_date,
                "category": category,
                "payee": payee,
                "is_recurring": is_recurring,
                "recurrence": recurrence,
                "auto_pay": auto_pay,
                "payment_method": payment_method,
                "notes": notes
            }
    
    return None


def contractor_form(key_prefix: str = "contractor") -> Optional[Dict[str, Any]]:
    """Contractor creation form"""
    
    service_types = ["cleaning", "yard", "plumbing", "electrical", "hvac", 
                    "appliance", "pest_control", "pool", "security", "general"]
    
    with st.form(key=f"{key_prefix}_form"):
        st.subheader("👷 New Contractor")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name*", placeholder="e.g., Juan")
            company = st.text_input("Company", placeholder="e.g., ABC Services")
            service_type = st.selectbox("Service Type", service_types)
        
        with col2:
            phone = st.text_input("Phone", placeholder="+1 234 567 8900")
            email = st.text_input("Email", placeholder="email@example.com")
            hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.0, step=5.0)
        
        notes = st.text_area("Notes", placeholder="Special skills, availability, etc.")
        
        submitted = st.form_submit_button("✅ Add Contractor", use_container_width=True)
        
        if submitted and name:
            return {
                "name": name,
                "company": company,
                "phone": phone,
                "email": email,
                "service_type": service_type,
                "hourly_rate": hourly_rate if hourly_rate > 0 else None,
                "notes": notes
            }
    
    return None


def project_form(key_prefix: str = "project") -> Optional[Dict[str, Any]]:
    """Project creation form"""
    
    categories = ["renovation", "improvement", "repair", "addition", "landscaping", "other"]
    
    with st.form(key=f"{key_prefix}_form"):
        st.subheader("🏗️ New Project")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Project Name*", placeholder="e.g., Kitchen Renovation")
            category = st.selectbox("Category", categories)
            budget = st.number_input("Budget ($)", min_value=0.0, step=100.0)
        
        with col2:
            start_date = st.date_input("Start Date", value=date.today())
            target_end_date = st.date_input("Target End Date", value=date.today() + timedelta(days=90))
        
        description = st.text_area("Description", placeholder="Project details, scope, etc.")
        
        submitted = st.form_submit_button("✅ Create Project", use_container_width=True)
        
        if submitted and name:
            return {
                "name": name,
                "description": description,
                "category": category,
                "budget": budget if budget > 0 else None,
                "start_date": start_date,
                "target_end_date": target_end_date
            }
    
    return None


def reading_form(key_prefix: str = "reading") -> Optional[Dict[str, Any]]:
    """Home reading/measurement form"""
    
    reading_types = ["water_quality", "energy_kwh", "water_gallons", "temperature", "humidity", "other"]
    locations = ["kitchen", "bathroom", "basement", "garage", "outdoor", "whole_house", "other"]
    
    with st.form(key=f"{key_prefix}_form"):
        st.subheader("📊 Log Reading")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            reading_type = st.selectbox("Type", reading_types)
        
        with col2:
            value = st.number_input("Value*", step=0.1)
        
        with col3:
            unit = st.text_input("Unit", placeholder="e.g., ppm, kWh, °F")
        
        col4, col5 = st.columns(2)
        
        with col4:
            location = st.selectbox("Location", locations)
        
        with col5:
            notes = st.text_input("Notes", placeholder="Any observations...")
        
        submitted = st.form_submit_button("✅ Log Reading", use_container_width=True)
        
        if submitted:
            return {
                "reading_type": reading_type,
                "value": value,
                "unit": unit,
                "location": location,
                "notes": notes
            }
    
    return None


def command_input(key: str = "command") -> Optional[str]:
    """Command input for Galidima"""
    
    command = st.text_input(
        "🤖 Command",
        placeholder="Ask Galidima anything... (e.g., 'show me upcoming bills', 'add a task')",
        key=key,
        label_visibility="collapsed"
    )
    
    return command if command else None
