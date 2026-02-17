"""
MyCasa Pro - Bank Connector
==========================

Universal bank connector for importing financial data from various sources:
- CSV exports from banks
- OFX files from financial institutions
- Direct API integration (future)

Handles:
- Transaction import and categorization
- Balance tracking
- Spending analysis
- Integration with Finance Agent
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
import csv
import logging
from pathlib import Path
import pandas as pd
import io
from decimal import Decimal

from database import get_db
from database.models import Transaction, Account, BudgetCategory

logger = logging.getLogger("mycasa.bank_connector")


@dataclass
class BankTransaction:
    """Standardized transaction format for all bank connectors"""
    date: date
    amount: Decimal
    description: str
    category: Optional[str] = None
    merchant: Optional[str] = None
    account_number: Optional[str] = None
    transaction_id: Optional[str] = None
    currency: str = "USD"
    balance_after: Optional[Decimal] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class BankAccount:
    """Standardized account format"""
    account_number: str
    account_type: str  # checking, savings, credit_card, investment
    bank_name: str
    current_balance: Decimal
    currency: str = "USD"
    nickname: Optional[str] = None
    status: str = "active"  # active, closed, frozen


class BankConnector(ABC):
    """Abstract base class for all bank connectors"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(f"mycasa.bank_connector.{self.__class__.__name__}")
    
    @abstractmethod
    def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to bank service using provided credentials"""
        pass
    
    @abstractmethod
    def get_accounts(self) -> List[BankAccount]:
        """Get list of accounts"""
        pass
    
    @abstractmethod
    def get_transactions(self, 
                       account_number: str, 
                       start_date: date, 
                       end_date: date) -> List[BankTransaction]:
        """Get transactions for a specific account in date range"""
        pass
    
    def normalize_amount(self, amount_str: str) -> Decimal:
        """Normalize amount string to Decimal"""
        if not amount_str:
            return Decimal('0')
        
        # Remove currency symbols and extra whitespace
        normalized = amount_str.strip().replace('$', '').replace(',', '')
        
        # Handle negative amounts (some banks use parentheses)
        if '(' in normalized and ')' in normalized:
            normalized = '-' + normalized.replace('(', '').replace(')', '')
        
        try:
            return Decimal(normalized)
        except:
            self.logger.warning(f"Could not parse amount: {amount_str}")
            return Decimal('0')
    
    def categorize_transaction(self, description: str, amount: Decimal) -> str:
        """Basic transaction categorization"""
        description_lower = description.lower()
        
        # Fixed expense categories
        fixed_categories = {
            'rent', 'mortgage', 'insurance', 'loan', 'car payment',
            'utilities', 'internet', 'phone', 'subscription'
        }
        
        # Variable expense categories
        variable_categories = {
            'groceries', 'dining', 'gas', 'shopping', 'entertainment',
            'travel', 'medical', 'education', 'gifts'
        }
        
        # Income categories
        income_categories = {
            'salary', 'paycheck', 'dividend', 'interest', 'refund',
            'payment', 'transfer'
        }
        
        # Try to match categories
        for cat in fixed_categories:
            if cat in description_lower:
                return f"Fixed: {cat.title()}"
        
        for cat in variable_categories:
            if cat in description_lower:
                return f"Variable: {cat.title()}"
        
        for cat in income_categories:
            if cat in description_lower:
                return f"Income: {cat.title()}"
        
        # Default categories based on amount sign
        if amount < 0:
            return "Variable: Other Expenses"
        else:
            return "Income: Other Income"


class CSVBankConnector(BankConnector):
    """Connector for importing bank data from CSV files"""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.supported_columns = {
            'date', 'amount', 'description', 'merchant', 'category',
            'account', 'balance', 'transaction_id', 'currency'
        }
    
    def connect(self, credentials: Dict[str, Any]) -> bool:
        """CSV connector doesn't need online connection"""
        return True
    
    def get_accounts(self) -> List[BankAccount]:
        """For CSV, accounts are determined from imported data"""
        # This would typically come from a configuration file or previous imports
        return []
    
    def get_transactions(self, 
                       account_number: str, 
                       start_date: date, 
                       end_date: date) -> List[BankTransaction]:
        """Import transactions from CSV file"""
        raise NotImplementedError("Use import_from_csv method instead")
    
    def import_from_csv(self, 
                       csv_file_path: str, 
                       column_mapping: Dict[str, str],
                       account_info: Optional[BankAccount] = None) -> List[BankTransaction]:
        """
        Import transactions from CSV file with column mapping
        
        Args:
            csv_file_path: Path to CSV file
            column_mapping: Dict mapping standard fields to CSV columns
                           e.g., {'date': 'Date', 'amount': 'Amount', 'description': 'Description'}
            account_info: Optional account information
        
        Returns:
            List of imported transactions
        """
        transactions = []
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            
            # Validate required columns
            required_fields = ['date', 'amount', 'description']
            missing_fields = [field for field in required_fields 
                            if field not in column_mapping and 
                               not any(col.lower() == field for col in df.columns)]
            
            if missing_fields:
                raise ValueError(f"Missing required columns: {missing_fields}")
            
            # Process each row
            for _, row in df.iterrows():
                try:
                    # Extract data using column mapping
                    trans_data = {}
                    
                    # Map date
                    date_col = self._find_column(column_mapping, 'date', row.index)
                    if date_col:
                        trans_data['date'] = self._parse_date(str(row[date_col]))
                    
                    # Map amount
                    amount_col = self._find_column(column_mapping, 'amount', row.index)
                    if amount_col:
                        amount_str = str(row[amount_col]).strip()
                        trans_data['amount'] = self.normalize_amount(amount_str)
                    
                    # Map description
                    desc_col = self._find_column(column_mapping, 'description', row.index)
                    if desc_col:
                        trans_data['description'] = str(row[desc_col])
                    
                    # Map optional fields
                    optional_mappings = {
                        'merchant': 'merchant',
                        'category': 'category', 
                        'account_number': 'account',
                        'transaction_id': 'transaction_id',
                        'currency': 'currency',
                        'balance_after': 'balance'
                    }
                    
                    for field, mapped_field in optional_mappings.items():
                        col = self._find_column(column_mapping, mapped_field, row.index)
                        if col and pd.notna(row[col]):
                            if field == 'balance_after' or field == 'amount':
                                trans_data[field] = self.normalize_amount(str(row[col]))
                            else:
                                trans_data[field] = str(row[col])
                    
                    # Set default account if provided
                    if account_info and 'account_number' not in trans_data:
                        trans_data['account_number'] = account_info.account_number
                    
                    # Create transaction object
                    trans = BankTransaction(**trans_data)
                    
                    # Auto-categorize if no category provided
                    if not trans.category:
                        trans.category = self.categorize_transaction(
                            trans.description, trans.amount
                        )
                    
                    transactions.append(trans)
                    
                except Exception as e:
                    self.logger.warning(f"Skipping row due to error: {e}")
                    continue
            
            self.logger.info(f"Imported {len(transactions)} transactions from {csv_file_path}")
            return transactions
            
        except Exception as e:
            self.logger.error(f"Error importing CSV file {csv_file_path}: {e}")
            raise
    
    def _find_column(self, column_mapping: Dict[str, str], field: str, available_columns: List[str]) -> Optional[str]:
        """Find the appropriate column for a given field"""
        # Check mapping first
        if field in column_mapping:
            mapped_name = column_mapping[field]
            # Case-insensitive search for mapped name
            for col in available_columns:
                if str(col).lower() == mapped_name.lower():
                    return str(col)
        
        # If not in mapping, search for common variations
        variations = {
            'date': ['date', 'transaction_date', 'posted_date', 'dt'],
            'amount': ['amount', 'amt', 'transaction_amount', 'value', 'price'],
            'description': ['description', 'desc', 'memo', 'notes', 'transaction_description'],
            'merchant': ['merchant', 'vendor', 'payee', 'store'],
            'category': ['category', 'cat', 'type', 'transaction_type'],
            'account': ['account', 'account_number', 'acc_num'],
            'transaction_id': ['id', 'transaction_id', 'trans_id', 'ref'],
            'currency': ['currency', 'cur', 'ccy'],
            'balance': ['balance', 'running_balance', 'end_balance']
        }
        
        if field in variations:
            for variation in variations[field]:
                for col in available_columns:
                    if str(col).lower() == variation.lower():
                        return str(col)
        
        return None
    
    def _parse_date(self, date_str: str) -> date:
        """Parse date string in various formats"""
        date_str = date_str.strip()
        
        # Common date formats
        formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%m/%d/%y', '%d/%m/%y', '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M', '%d/%m/%Y %H:%M'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date()
            except ValueError:
                continue
        
        # If no format matches, raise error
        raise ValueError(f"Unable to parse date: {date_str}")


class OFXBankConnector(BankConnector):
    """Connector for importing bank data from OFX files"""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.ofx_parser = None
    
    def connect(self, credentials: Dict[str, Any]) -> bool:
        """OFX connector doesn't need online connection"""
        return True
    
    def get_accounts(self) -> List[BankAccount]:
        """Parse accounts from OFX data"""
        raise NotImplementedError("Use import_from_ofx method instead")
    
    def get_transactions(self, 
                       account_number: str, 
                       start_date: date, 
                       end_date: date) -> List[BankTransaction]:
        """Get transactions for date range"""
        raise NotImplementedError("Use import_from_ofx method instead")
    
    def import_from_ofx(self, ofx_file_path: str) -> List[Tuple[BankAccount, List[BankTransaction]]]:
        """
        Import accounts and transactions from OFX file
        
        Args:
            ofx_file_path: Path to OFX file
            
        Returns:
            List of (account, transactions) tuples
        """
        try:
            import ofxparse
            
            with open(ofx_file_path, 'rb') as f:
                ofx_data = ofxparse.OfxParser.parse(f)
            
            results = []
            
            # Process each account
            for account in ofx_data.accounts:
                bank_account = BankAccount(
                    account_number=account.number or "unknown",
                    account_type=account.type.lower() if account.type else "checking",
                    bank_name=ofx_data.institution.name if ofx_data.institution else "Unknown Bank",
                    current_balance=Decimal(str(account.balance)) if account.balance else Decimal('0'),
                    currency="USD"  # OFX typically uses USD
                )
                
                # Convert OFX transactions to standard format
                transactions = []
                for ofx_trans in account.statement.transactions:
                    trans = BankTransaction(
                        date=ofx_trans.date.date() if ofx_trans.date else date.today(),
                        amount=Decimal(str(ofx_trans.amount)) if ofx_trans.amount else Decimal('0'),
                        description=ofx_trans.payee or ofx_trans.memo or "Unknown",
                        merchant=ofx_trans.payee,
                        category=ofx_trans.type if ofx_trans.type else None,
                        transaction_id=ofx_trans.id if ofx_trans.id else None,
                        account_number=bank_account.account_number
                    )
                    
                    # Auto-categorize if no category provided
                    if not trans.category:
                        trans.category = self.categorize_transaction(
                            trans.description, trans.amount
                        )
                    
                    transactions.append(trans)
                
                results.append((bank_account, transactions))
            
            self.logger.info(f"Imported {len(results)} accounts from {ofx_file_path}")
            return results
            
        except ImportError:
            raise ImportError("ofxparse library required for OFX support. Install with: pip install ofxparse")
        except Exception as e:
            self.logger.error(f"Error importing OFX file {ofx_file_path}: {e}")
            raise


class BankImportService:
    """Service to coordinate bank data imports"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.csv_connector = CSVBankConnector(tenant_id)
        self.ofx_connector = OFXBankConnector(tenant_id)
        self.logger = logging.getLogger(f"mycasa.bank_import_service")
    
    def import_csv_transactions(self, 
                              file_path: str, 
                              column_mapping: Dict[str, str],
                              account_info: Optional[BankAccount] = None) -> Dict[str, Any]:
        """
        Import transactions from CSV file
        
        Returns:
            Import summary with statistics
        """
        try:
            transactions = self.csv_connector.import_from_csv(
                file_path, column_mapping, account_info
            )
            
            # Save to database
            with get_db() as db:
                imported_count = 0
                for trans in transactions:
                    # Check if transaction already exists
                    existing = db.query(Transaction).filter_by(
                        tenant_id=self.tenant_id,
                        transaction_id=trans.transaction_id,
                        date=trans.date,
                        amount=trans.amount
                    ).first()
                    
                    if not existing:
                        db_trans = Transaction(
                            tenant_id=self.tenant_id,
                            account_number=trans.account_number,
                            date=trans.date,
                            amount=float(trans.amount),
                            description=trans.description,
                            category=trans.category,
                            merchant=trans.merchant,
                            currency=trans.currency,
                            tags=trans.tags
                        )
                        
                        if trans.transaction_id:
                            db_trans.transaction_id = trans.transaction_id
                        
                        db.add(db_trans)
                        imported_count += 1
                
                db.commit()
            
            return {
                "success": True,
                "total_found": len(transactions),
                "imported": imported_count,
                "skipped_duplicates": len(transactions) - imported_count,
                "file_path": file_path
            }
            
        except Exception as e:
            self.logger.error(f"Error importing CSV transactions: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def import_ofx_transactions(self, file_path: str) -> Dict[str, Any]:
        """
        Import transactions from OFX file
        
        Returns:
            Import summary with statistics
        """
        try:
            account_transactions = self.ofx_connector.import_from_ofx(file_path)
            
            total_transactions = 0
            imported_count = 0
            
            with get_db() as db:
                for account, transactions in account_transactions:
                    # Save account info
                    existing_account = db.query(Account).filter_by(
                        tenant_id=self.tenant_id,
                        account_number=account.account_number
                    ).first()
                    
                    if not existing_account:
                        db_account = Account(
                            tenant_id=self.tenant_id,
                            account_number=account.account_number,
                            account_type=account.account_type,
                            bank_name=account.bank_name,
                            current_balance=float(account.current_balance),
                            currency=account.currency,
                            nickname=account.nickname,
                            status=account.status
                        )
                        db.add(db_account)
                    
                    # Save transactions
                    for trans in transactions:
                        existing = db.query(Transaction).filter_by(
                            tenant_id=self.tenant_id,
                            transaction_id=trans.transaction_id,
                            date=trans.date,
                            amount=float(trans.amount)
                        ).first()
                        
                        if not existing:
                            db_trans = Transaction(
                                tenant_id=self.tenant_id,
                                account_number=trans.account_number,
                                date=trans.date,
                                amount=float(trans.amount),
                                description=trans.description,
                                category=trans.category,
                                merchant=trans.merchant,
                                currency=trans.currency,
                                tags=trans.tags
                            )
                            
                            if trans.transaction_id:
                                db_trans.transaction_id = trans.transaction_id
                            
                            db.add(db_trans)
                            imported_count += 1
                        
                        total_transactions += 1
                
                db.commit()
            
            return {
                "success": True,
                "accounts_processed": len(account_transactions),
                "total_transactions_found": total_transactions,
                "imported": imported_count,
                "skipped_duplicates": total_transactions - imported_count,
                "file_path": file_path
            }
            
        except Exception as e:
            self.logger.error(f"Error importing OFX transactions: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }


# Global registry for bank connectors
CONNECTOR_REGISTRY = {
    'csv': CSVBankConnector,
    'ofx': OFXBankConnector,
}


def get_bank_connector(connector_type: str, tenant_id: str) -> BankConnector:
    """Get a bank connector instance by type"""
    if connector_type not in CONNECTOR_REGISTRY:
        raise ValueError(f"Unknown connector type: {connector_type}")
    
    return CONNECTOR_REGISTRY[connector_type](tenant_id)


def get_import_service(tenant_id: str) -> BankImportService:
    """Get bank import service instance"""
    return BankImportService(tenant_id)