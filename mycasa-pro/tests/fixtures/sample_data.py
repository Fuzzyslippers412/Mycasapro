"""
Sample data fixtures for MyCasa Pro tests.

This module provides factory functions and sample data for testing.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any


# ============================================================================
# PROPERTY DATA
# ============================================================================

def sample_property_data(tenant_id: str = "test-tenant") -> Dict[str, Any]:
    """Generate sample property data."""
    return {
        "tenant_id": tenant_id,
        "name": "Sunset Villa",
        "address": "123 Sunset Boulevard",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90001",
        "property_type": "residential",
        "bedrooms": 4,
        "bathrooms": 3,
        "square_feet": 2500,
        "purchase_price": 650000.0,
        "purchase_date": "2020-06-15",
        "current_value": 700000.0,
    }


def sample_properties_list(tenant_id: str = "test-tenant", count: int = 3) -> List[Dict[str, Any]]:
    """Generate a list of sample properties."""
    properties = []
    for i in range(count):
        prop = sample_property_data(tenant_id)
        prop["name"] = f"Property {i+1}"
        prop["address"] = f"{100 + i*10} Main St"
        prop["purchase_price"] = 300000 + (i * 100000)
        properties.append(prop)
    return properties


# ============================================================================
# TASK DATA
# ============================================================================

def sample_task_data(tenant_id: str = "test-tenant", agent: str = "manager") -> Dict[str, Any]:
    """Generate sample task data."""
    return {
        "tenant_id": tenant_id,
        "title": "Review monthly expenses",
        "description": "Analyze spending patterns and identify savings opportunities",
        "priority": "high",
        "status": "pending",
        "agent": agent,
        "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
        "tags": ["finance", "review"],
    }


def sample_tasks_by_priority(tenant_id: str = "test-tenant") -> List[Dict[str, Any]]:
    """Generate tasks with different priorities."""
    return [
        {**sample_task_data(tenant_id), "priority": "high", "title": "Fix water leak"},
        {**sample_task_data(tenant_id), "priority": "medium", "title": "Schedule HVAC maintenance"},
        {**sample_task_data(tenant_id), "priority": "low", "title": "Review property insurance"},
    ]


# ============================================================================
# TRANSACTION DATA
# ============================================================================

def sample_transaction_data(tenant_id: str = "test-tenant") -> Dict[str, Any]:
    """Generate sample transaction data."""
    return {
        "tenant_id": tenant_id,
        "date": "2024-01-15",
        "description": "Electric Company",
        "amount": -125.50,
        "category": "Utilities",
        "account": "Checking",
        "tags": ["recurring", "utility"],
    }


def sample_transactions_monthly(tenant_id: str = "test-tenant") -> List[Dict[str, Any]]:
    """Generate sample monthly transactions."""
    base_date = datetime(2024, 1, 1)
    transactions = []

    categories = [
        ("Mortgage Payment", -2500.0, "Housing"),
        ("Electric Company", -125.0, "Utilities"),
        ("Water & Sewer", -75.0, "Utilities"),
        ("Internet Service", -80.0, "Utilities"),
        ("Property Tax", -300.0, "Taxes"),
        ("Home Insurance", -150.0, "Insurance"),
        ("Grocery Store", -250.0, "Food"),
        ("Hardware Store", -150.0, "Maintenance"),
        ("Rental Income", 2800.0, "Income"),
    ]

    for i, (desc, amount, category) in enumerate(categories):
        transactions.append({
            "tenant_id": tenant_id,
            "date": (base_date + timedelta(days=i * 3)).strftime("%Y-%m-%d"),
            "description": desc,
            "amount": amount,
            "category": category,
            "account": "Checking",
        })

    return transactions


# ============================================================================
# MAINTENANCE DATA
# ============================================================================

def sample_maintenance_item_data(tenant_id: str = "test-tenant", property_id: int = 1) -> Dict[str, Any]:
    """Generate sample maintenance item data."""
    return {
        "tenant_id": tenant_id,
        "property_id": property_id,
        "title": "HVAC Filter Replacement",
        "description": "Replace air filter in main HVAC unit",
        "priority": "medium",
        "status": "pending",
        "frequency": "monthly",
        "last_completed": None,
        "next_due": (datetime.now() + timedelta(days=30)).isoformat(),
        "estimated_cost": 25.0,
    }


def sample_maintenance_schedule(tenant_id: str = "test-tenant", property_id: int = 1) -> List[Dict[str, Any]]:
    """Generate a sample maintenance schedule."""
    items = [
        {
            "title": "HVAC Filter Replacement",
            "frequency": "monthly",
            "priority": "medium",
            "estimated_cost": 25.0,
        },
        {
            "title": "Gutter Cleaning",
            "frequency": "quarterly",
            "priority": "medium",
            "estimated_cost": 150.0,
        },
        {
            "title": "HVAC System Inspection",
            "frequency": "yearly",
            "priority": "high",
            "estimated_cost": 200.0,
        },
        {
            "title": "Roof Inspection",
            "frequency": "yearly",
            "priority": "high",
            "estimated_cost": 300.0,
        },
    ]

    schedule = []
    for item in items:
        data = sample_maintenance_item_data(tenant_id, property_id)
        data.update(item)
        schedule.append(data)

    return schedule


# ============================================================================
# CONTRACTOR DATA
# ============================================================================

def sample_contractor_data(tenant_id: str = "test-tenant") -> Dict[str, Any]:
    """Generate sample contractor data."""
    return {
        "tenant_id": tenant_id,
        "name": "ABC Plumbing Services",
        "specialty": "Plumbing",
        "phone": "555-0100",
        "email": "contact@abcplumbing.com",
        "address": "456 Business Park Dr",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90001",
        "rating": 4.5,
        "reviews_count": 127,
        "is_verified": True,
        "license_number": "PL-12345",
    }


def sample_contractors_by_specialty(tenant_id: str = "test-tenant") -> List[Dict[str, Any]]:
    """Generate contractors with different specialties."""
    specialties = [
        ("ABC Plumbing Services", "Plumbing", 4.5),
        ("Elite HVAC Pros", "HVAC", 4.8),
        ("Quality Electricians", "Electrical", 4.6),
        ("Premier Roofing", "Roofing", 4.7),
        ("General Handyman Services", "General", 4.2),
    ]

    contractors = []
    for i, (name, specialty, rating) in enumerate(specialties):
        contractor = sample_contractor_data(tenant_id)
        contractor["name"] = name
        contractor["specialty"] = specialty
        contractor["rating"] = rating
        contractor["phone"] = f"555-{1000 + i * 100:04d}"
        contractors.append(contractor)

    return contractors


# ============================================================================
# SECONDBRAIN DATA
# ============================================================================

def sample_note_data(tenant_id: str = "test-tenant") -> Dict[str, Any]:
    """Generate sample SecondBrain note data."""
    return {
        "tenant_id": tenant_id,
        "title": "Property Management Best Practices",
        "content": "Key strategies for effective property management...",
        "tags": ["property-management", "best-practices"],
        "note_type": "text",
        "metadata": {
            "source": "research",
            "importance": "high",
        },
    }


def sample_notes_collection(tenant_id: str = "test-tenant") -> List[Dict[str, Any]]:
    """Generate a collection of sample notes."""
    notes = [
        {
            "title": "HVAC Maintenance Schedule",
            "content": "Regular HVAC maintenance should be performed quarterly...",
            "tags": ["maintenance", "hvac"],
        },
        {
            "title": "Energy Efficiency Tips",
            "content": "Ways to reduce energy costs: LED bulbs, smart thermostats...",
            "tags": ["energy", "cost-savings"],
        },
        {
            "title": "Contractor Vetting Checklist",
            "content": "1. Check license, 2. Verify insurance, 3. Read reviews...",
            "tags": ["contractors", "checklist"],
        },
        {
            "title": "Tax Deduction Guide",
            "content": "Property-related tax deductions include: mortgage interest...",
            "tags": ["finance", "taxes"],
        },
    ]

    collection = []
    for note in notes:
        data = sample_note_data(tenant_id)
        data.update(note)
        collection.append(data)

    return collection


# ============================================================================
# INBOX DATA
# ============================================================================

def sample_inbox_message_data(tenant_id: str = "test-tenant") -> Dict[str, Any]:
    """Generate sample inbox message data."""
    return {
        "tenant_id": tenant_id,
        "sender": "contractor@example.com",
        "subject": "Quote for HVAC Repair",
        "body": "Here is the quote you requested for the HVAC repair work...",
        "source": "email",
        "received_at": datetime.now().isoformat(),
        "is_read": False,
        "priority": "medium",
    }


def sample_inbox_messages(tenant_id: str = "test-tenant", count: int = 5) -> List[Dict[str, Any]]:
    """Generate multiple inbox messages."""
    sources = ["email", "whatsapp", "sms"]
    priorities = ["low", "medium", "high"]

    messages = []
    for i in range(count):
        msg = sample_inbox_message_data(tenant_id)
        msg["subject"] = f"Message {i+1}"
        msg["source"] = sources[i % len(sources)]
        msg["priority"] = priorities[i % len(priorities)]
        msg["received_at"] = (datetime.now() - timedelta(hours=i)).isoformat()
        messages.append(msg)

    return messages


# ============================================================================
# CSV/OFX SAMPLE DATA FOR BANK IMPORTS
# ============================================================================

SAMPLE_CSV_TRANSACTIONS = """Date,Description,Amount,Balance
2024-01-01,Opening Balance,0.00,5000.00
2024-01-05,Grocery Store,-125.50,4874.50
2024-01-07,Salary Deposit,3000.00,7874.50
2024-01-10,Electric Bill,-150.00,7724.50
2024-01-12,Restaurant,-45.75,7678.75
2024-01-15,Mortgage Payment,-2500.00,5178.75
2024-01-18,Gas Station,-60.00,5118.75
2024-01-20,Online Shopping,-89.99,5028.76
2024-01-25,Property Insurance,-250.00,4778.76
2024-01-28,Rental Income,2800.00,7578.76
"""

SAMPLE_OFX_DATA = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20240131120000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>USD
<BANKACCTFROM>
<BANKID>123456789
<ACCTID>9876543210
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20240101120000
<DTEND>20240131120000
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240105120000
<TRNAMT>-125.50
<FITID>202401051
<NAME>Grocery Store
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240107120000
<TRNAMT>3000.00
<FITID>202401071
<NAME>Salary Deposit
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240110120000
<TRNAMT>-150.00
<FITID>202401101
<NAME>Electric Bill
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>7724.50
<DTASOF>20240131120000
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_bulk_data(factory_func, count: int = 10, **kwargs) -> List[Dict[str, Any]]:
    """Create bulk test data using a factory function."""
    return [factory_func(**kwargs) for _ in range(count)]


def generate_date_range(start_date: datetime, days: int) -> List[str]:
    """Generate a list of dates in YYYY-MM-DD format."""
    return [
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days)
    ]
