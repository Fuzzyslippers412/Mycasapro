"""
MyCasa Pro - Bank Connector API Routes
=====================================

Endpoints for importing and managing bank data:
- CSV file uploads and imports
- OFX file uploads and imports  
- Transaction management
- Account linking
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import tempfile
import json
from pathlib import Path

from connectors.bank_connector import get_import_service, BankAccount, BankTransaction

router = APIRouter(prefix="/bank", tags=["Bank"])

@router.post("/import/csv")
async def import_csv_transactions(
    file: UploadFile = File(...),
    column_mapping: str = Form(...),
    account_number: str = Form(default=None),
    account_type: str = Form(default="checking"),
    bank_name: str = Form(default="Unknown Bank")
) -> Dict[str, Any]:
    """
    Import transactions from CSV file.
    
    Args:
        file: CSV file containing bank transactions
        column_mapping: JSON string mapping standard fields to CSV columns
                       e.g., {"date": "Date", "amount": "Amount", "description": "Description"}
        account_number: Account number to associate with transactions
        account_type: Type of account (checking, savings, credit_card, investment)
        bank_name: Name of the bank
    
    Returns:
        Import summary with statistics
    """
    try:
        # Parse column mapping
        try:
            column_map = json.loads(column_mapping)
            if not isinstance(column_map, dict):
                raise ValueError("Column mapping must be a JSON object")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in column_mapping")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Validate required mappings
        required_fields = ['date', 'amount', 'description']
        missing_fields = [field for field in required_fields if field not in column_map]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required column mappings: {missing_fields}"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_path = tmp_file.name
        
        try:
            # Create account info if provided
            account_info = None
            if account_number:
                from decimal import Decimal
                account_info = BankAccount(
                    account_number=account_number,
                    account_type=account_type,
                    bank_name=bank_name,
                    current_balance=Decimal('0'),  # Will be calculated from transactions
                    nickname=f"{bank_name} {account_type.title()}"
                )
            
            # Import transactions
            import_service = get_import_service("default")  # Use default tenant for now
            result = import_service.import_csv_transactions(
                temp_path, 
                column_map, 
                account_info
            )
            
            if not result["success"]:
                raise HTTPException(status_code=500, detail=result["error"])
            
            return result
            
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV import failed: {str(e)}")


@router.post("/import/ofx")
async def import_ofx_transactions(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Import transactions from OFX file.
    
    Args:
        file: OFX file containing bank transactions and account information
    
    Returns:
        Import summary with statistics
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ofx") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_path = tmp_file.name
        
        try:
            # Import transactions
            import_service = get_import_service("default")  # Use default tenant for now
            result = import_service.import_ofx_transactions(temp_path)
            
            if not result["success"]:
                raise HTTPException(status_code=500, detail=result["error"])
            
            return result
            
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OFX import failed: {str(e)}")


@router.get("/transactions")
async def list_transactions(
    account_number: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List imported transactions with optional filtering.
    
    Args:
        account_number: Filter by account number
        start_date: Filter by start date (YYYY-MM-DD)
        end_date: Filter by end date (YYYY-MM-DD)  
        category: Filter by category
        limit: Number of transactions to return
        offset: Offset for pagination
    
    Returns:
        List of transactions with pagination info
    """
    try:
        from database import get_db
        from database.models import Transaction
        
        with get_db() as db:
            query = db.query(Transaction).filter_by(tenant_id="default")  # Default tenant
            
            # Apply filters
            if account_number:
                query = query.filter_by(account_number=account_number)
            
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(Transaction.date >= start_dt)
            
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(Transaction.date <= end_dt)
            
            if category:
                query = query.filter(Transaction.category.like(f"%{category}%"))
            
            # Apply ordering and pagination
            transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()
            total = query.count()
            
            # Format results
            result_transactions = []
            for trans in transactions:
                result_transactions.append({
                    "id": trans.id,
                    "account_number": trans.account_number,
                    "date": trans.date.isoformat() if trans.date else None,
                    "amount": trans.amount,
                    "description": trans.description,
                    "category": trans.category,
                    "merchant": trans.merchant,
                    "currency": trans.currency,
                    "tags": trans.tags or [],
                    "created_at": trans.created_at.isoformat() if trans.created_at else None
                })
            
            return {
                "transactions": result_transactions,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + len(result_transactions) < total
            }
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transactions: {str(e)}")


@router.get("/accounts")
async def list_accounts() -> Dict[str, Any]:
    """
    List all imported bank accounts.
    
    Returns:
        List of bank accounts
    """
    try:
        from database import get_db
        from database.models import Account
        
        with get_db() as db:
            accounts = db.query(Account).filter_by(tenant_id="default").all()
            
            result_accounts = []
            for acc in accounts:
                result_accounts.append({
                    "account_number": acc.account_number,
                    "account_type": acc.account_type,
                    "bank_name": acc.bank_name,
                    "current_balance": acc.current_balance,
                    "currency": acc.currency,
                    "nickname": acc.nickname,
                    "status": acc.status,
                    "created_at": acc.created_at.isoformat() if acc.created_at else None,
                    "updated_at": acc.updated_at.isoformat() if acc.updated_at else None
                })
            
            return {
                "accounts": result_accounts,
                "total": len(result_accounts)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve accounts: {str(e)}")


@router.get("/summary")
async def get_financial_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get financial summary including balances, spending, and income.
    
    Args:
        start_date: Start date for summary (YYYY-MM-DD)
        end_date: End date for summary (YYYY-MM-DD)
    
    Returns:
        Financial summary with balances, spending, and income
    """
    try:
        from database import get_db
        from database.models import Transaction, Account
        
        with get_db() as db:
            # Get accounts
            accounts = db.query(Account).filter_by(tenant_id="default").all()
            
            # Build transaction query with date filters
            trans_query = db.query(Transaction).filter_by(tenant_id="default")
            
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                trans_query = trans_query.filter(Transaction.date >= start_dt)
            
            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                trans_query = trans_query.filter(Transaction.date <= end_dt)
            
            transactions = trans_query.all()
            
            # Calculate summary statistics
            total_balance = sum(acc.current_balance for acc in accounts if acc.status == "active")
            
            total_income = 0
            total_spending = 0
            category_breakdown = {}
            
            for trans in transactions:
                amount = trans.amount
                if amount > 0:
                    total_income += amount
                else:
                    total_spending += abs(amount)
                
                # Category breakdown
                cat = trans.category or "Uncategorized"
                if cat not in category_breakdown:
                    category_breakdown[cat] = 0
                category_breakdown[cat] += amount if amount > 0 else abs(amount)
            
            # Top spending categories
            top_categories = sorted(
                [(cat, amt) for cat, amt in category_breakdown.items() if amt > 0],
                key=lambda x: x[1], 
                reverse=True
            )[:5]
            
            # Date range info
            if transactions:
                earliest = min(t.date for t in transactions if t.date)
                latest = max(t.date for t in transactions if t.date)
            else:
                earliest = None
                latest = None
            
            return {
                "summary": {
                    "total_balance": total_balance,
                    "total_income": total_income,
                    "total_spending": total_spending,
                    "net_change": total_income - total_spending,
                    "date_range": {
                        "start": earliest.isoformat() if earliest else None,
                        "end": latest.isoformat() if latest else None
                    }
                },
                "accounts": {
                    "total_accounts": len(accounts),
                    "active_accounts": len([a for a in accounts if a.status == "active"]),
                    "account_types": {acc.account_type: sum(1 for a in accounts if a.account_type == acc.account_type) for acc in accounts}
                },
                "spending": {
                    "total_spending": total_spending,
                    "top_categories": [{"category": cat, "amount": amt} for cat, amt in top_categories],
                    "average_daily_spending": total_spending / (latest - earliest).days if earliest and latest and (latest - earliest).days > 0 else 0
                },
                "income": {
                    "total_income": total_income
                }
            }
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate summary: {str(e)}")


@router.get("/preview/csv")
async def preview_csv_columns(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Preview CSV file structure to help with column mapping.
    
    Args:
        file: CSV file to preview
    
    Returns:
        Sample rows and column names for mapping
    """
    try:
        import pandas as pd
        
        # Read file content
        content = await file.read()
        
        # Create DataFrame from content
        df = pd.read_csv(pd.io.common.StringIO(content.decode('utf-8')))
        
        # Get sample rows
        sample_rows = df.head(3).to_dict('records')
        
        # Get column names
        columns = df.columns.tolist()
        
        # Basic analysis
        analysis = {
            "total_rows": len(df),
            "total_columns": len(columns),
            "columns": columns,
            "sample_data": sample_rows,
            "suggested_mappings": suggest_column_mappings(columns)
        }
        
        return analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview CSV: {str(e)}")


def suggest_column_mappings(columns: List[str]) -> Dict[str, str]:
    """
    Suggest column mappings based on common naming patterns.
    
    Args:
        columns: List of column names from CSV
        
    Returns:
        Suggested mapping of standard fields to column names
    """
    suggestions = {}
    
    # Convert columns to lowercase for comparison
    col_lower = [col.lower() for col in columns]
    
    # Look for date columns
    date_patterns = ['date', 'dt', 'time', 'posted', 'transaction']
    for pattern in date_patterns:
        for i, col in enumerate(col_lower):
            if pattern in col and ('date' in col or 'time' in col or 'dt' in col):
                suggestions['date'] = columns[i]
                break
        if 'date' in suggestions:
            break
    
    # Look for amount columns
    amount_patterns = ['amount', 'amt', 'value', 'price', 'balance', 'change']
    for pattern in amount_patterns:
        for i, col in enumerate(col_lower):
            if pattern in col and 'amount' in col:
                suggestions['amount'] = columns[i]
                break
        if 'amount' in suggestions:
            break
    
    # Look for description columns
    desc_patterns = ['description', 'desc', 'memo', 'notes', 'payee', 'details']
    for pattern in desc_patterns:
        for i, col in enumerate(col_lower):
            if pattern in col:
                suggestions['description'] = columns[i]
                break
        if 'description' in suggestions:
            break
    
    # Look for merchant/columns
    merchant_patterns = ['merchant', 'vendor', 'payee', 'store', 'company']
    for pattern in merchant_patterns:
        for i, col in enumerate(col_lower):
            if pattern in col:
                suggestions['merchant'] = columns[i]
                break
        if 'merchant' in suggestions:
            break
    
    return suggestions