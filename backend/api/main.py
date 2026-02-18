"""
MyCasa Pro API
FastAPI backend serving CLI and UI
"""
import time
import asyncio
import uuid
import pandas as pd
from datetime import datetime, date
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from ..core.schemas import (
    APIResponse, HealthStatus, TaskCreate, TaskUpdate, TransactionIngest, ContractorJobCreate,
    CostRecord, CostSummary, IntakeRequest, IntakeStatus,
    BackupRestore
)
from ..core.utils import generate_correlation_id, log_action
from ..storage.database import get_db_session, init_db, get_db_status
from ..storage.repository import Repository

# Startup time for uptime calculation
START_TIME = time.time()

# Background sync task reference
_sync_task: asyncio.Task | None = None
_sync_enabled: bool = False  # User must explicitly enable via Settings > Launch
_last_sync_at: Optional[str] = None
_last_sync_result: Optional[dict] = None

# Sync interval (15 minutes)
SYNC_INTERVAL_SECONDS = 15 * 60

# Manager message queue
_manager_messages: list = []
_message_id_counter: int = 0


def queue_manager_message(text: str):
    """Queue a message from Manager to be shown in the chat UI"""
    global _manager_messages, _message_id_counter
    _message_id_counter += 1
    _manager_messages.append({
        "id": f"mgr_{_message_id_counter}",
        "text": text,
        "timestamp": datetime.utcnow().isoformat()
    })


async def _run_inbox_sync():
    """Run inbox sync (called from background task or manual trigger)"""
    from ..connectors import gmail_connector, whatsapp_connector
    from ..storage.models import InboxMessageDB
    global _last_sync_at, _last_sync_result
    
    try:
        db = get_db_session()
        repo = Repository(db)
        
        # Gmail: only unread emails from last 7 days
        gmail_result = gmail_connector.fetch_messages(days_back=7, max_results=30, unread_only=True)
        
        # WhatsApp: only whitelisted contacts
        whatsapp_result = whatsapp_connector.fetch_messages(limit=20)
        
        # Store new messages
        new_count = 0
        for msg in gmail_result + whatsapp_result:
            existing = repo.db.query(InboxMessageDB).filter(
                InboxMessageDB.external_id == msg["external_id"]
            ).first()
            
            if not existing:
                db_msg = InboxMessageDB(**msg)
                repo.db.add(db_msg)
                new_count += 1
        
        repo.db.commit()
        db.close()

        result = {"gmail": len(gmail_result), "whatsapp": len(whatsapp_result), "new": new_count}
        _last_sync_at = datetime.utcnow().isoformat()
        _last_sync_result = result
        return result
    except Exception as e:
        print(f"[SYNC] Error during inbox sync: {e}")
        _last_sync_result = {"error": str(e)}
        return {"error": str(e)}


async def _periodic_sync():
    """Background task that runs inbox sync periodically (only when enabled)"""
    global _sync_enabled
    
    while True:
        if _sync_enabled:
            print(f"[SYNC] Running periodic inbox sync...")
            result = await _run_inbox_sync()
            print(f"[SYNC] Periodic sync complete: {result}")
            log_action("inbox_sync", {"trigger": "periodic", "result": result})
        
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global _sync_task
    
    # Startup
    print("[API] Initializing MyCasa Pro Backend...")
    init_db()
    log_action("api_started", {"version": "1.0.0"})
    
    # Start background sync task (but it won't sync until user enables it)
    print("[API] Background sync task ready (disabled until user launches from Settings)")
    _sync_task = asyncio.create_task(_periodic_sync())
    
    yield
    
    # Shutdown
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
    log_action("api_stopped", {})


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="MyCasa Pro API",
        description="Backend API for MyCasa Pro Home Operating System",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS - allow all localhost ports for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000", 
            "http://localhost:3001", 
            "http://localhost:3002",
            "http://127.0.0.1:3000", 
            "http://127.0.0.1:3001",
            "http://localhost:8501",
            "http://localhost:8505",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from .system_routes import router as system_router, api_router as system_api_router
    from .approval_routes import router as approval_router
    from .routes.teams import router as teams_router
    from .routes.chat import router as chat_router
    from .routes.janitor import router as janitor_router
    from .routes.finance import router as finance_router
    from .routes.polymarket import router as polymarket_router
    from .routes.edgelab import router as edgelab_router

    app.include_router(system_router)
    app.include_router(system_api_router)  # /api/system/live endpoint
    app.include_router(approval_router)
    app.include_router(teams_router)
    app.include_router(chat_router)
    app.include_router(janitor_router)
    app.include_router(finance_router)
    app.include_router(polymarket_router)
    app.include_router(edgelab_router)  # Browser scraping + Polymarket APIs

    return app


app = create_app()


# Dependency
def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def get_repo(db: Session = Depends(get_db)) -> Repository:
    return Repository(db)


# ============ HEALTH ============

@app.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check(repo: Repository = Depends(get_repo)):
    """Health check endpoint"""
    db_status = get_db_status()
    
    # Check connector status
    from ..connectors import gmail_connector, whatsapp_connector
    
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        uptime_seconds=round(time.time() - START_TIME, 2),
        db_status=db_status.get("status", "unknown"),
        queue_status="idle",
        active_tasks=len(repo.get_tasks(status="in_progress")),
        connectors={
            "gmail": gmail_connector.get_status().value,
            "whatsapp": whatsapp_connector.get_status().value,
        }
    )


@app.get("/status", tags=["Health"])
async def get_status(repo: Repository = Depends(get_repo)):
    """Quick status for dashboard"""
    db_status = get_db_status()
    tasks = repo.get_tasks(limit=10)
    events = repo.get_recent_events(limit=10)
    cost = repo.get_cost_summary("month")
    budgets = repo.get_all_budgets()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "db": db_status,
        "tasks": {
            "pending": len([t for t in tasks if t.status == "pending"]),
            "in_progress": len([t for t in tasks if t.status == "in_progress"]),
            "recent": [{"id": t.id, "title": t.title, "status": t.status} for t in tasks[:5]]
        },
        "events": {
            "recent": [{"id": e.id, "type": e.event_type, "action": e.action} for e in events[:5]]
        },
        "cost": {
            "today": repo.get_cost_summary("today").total_cost,
            "month": cost.total_cost,
            "budget_pct": cost.budget_used_pct
        },
        "budgets": [
            {
                "name": b.name,
                "type": b.budget_type,
                "limit": b.limit_amount,
                "current": b.current_spend,
                "pct": round((b.current_spend / b.limit_amount) * 100, 1) if b.limit_amount > 0 else 0
            }
            for b in budgets
        ]
    }


# ============ INTAKE ============

@app.get("/intake", response_model=IntakeStatus, tags=["Intake"])
async def get_intake_status(repo: Repository = Depends(get_repo)):
    """Get intake/setup status"""
    settings = repo.get_user_settings()
    primary_income = repo.get_primary_income_source()
    budgets = repo.get_all_budgets()
    
    missing = []
    if not primary_income:
        missing.append("primary_income_source")
    if not budgets:
        missing.append("budgets")
    
    return IntakeStatus(
        intake_complete=settings.intake_complete if settings else False,
        intake_completed_at=settings.intake_completed_at if settings else None,
        primary_income_configured=primary_income is not None,
        budgets_configured=len(budgets) > 0,
        connectors_configured=True,  # Stubs always available
        missing_items=missing
    )


@app.post("/intake", response_model=APIResponse, tags=["Intake"])
async def complete_intake(request: IntakeRequest, repo: Repository = Depends(get_repo)):
    """Complete initial system intake/setup"""
    correlation_id = generate_correlation_id()
    
    try:
        # Create primary income source
        request.primary_income_source.is_primary = True
        repo.create_income_source(request.primary_income_source)
        
        # Update budgets
        from ..storage.models import BudgetPolicyDB
        repo.db.query(BudgetPolicyDB).filter(BudgetPolicyDB.name == "Monthly Spend").update(
            {"limit_amount": request.monthly_spend_limit}
        )
        repo.db.query(BudgetPolicyDB).filter(BudgetPolicyDB.name == "Daily Spend").update(
            {"limit_amount": request.daily_spend_limit}
        )
        repo.db.query(BudgetPolicyDB).filter(BudgetPolicyDB.name == "System Cost").update(
            {"limit_amount": request.system_cost_limit}
        )
        repo.db.commit()
        
        # Mark intake complete
        repo.update_user_settings(
            intake_complete=True,
            intake_completed_at=datetime.utcnow(),
            notification_channels=request.notification_channels
        )
        
        # Log event
        repo.create_event(
            event_type="intake_completed",
            action="System intake completed",
            details={
                "income_source": request.primary_income_source.name,
                "monthly_limit": request.monthly_spend_limit,
                "daily_limit": request.daily_spend_limit
            },
            correlation_id=correlation_id
        )
        
        return APIResponse(
            status="success",
            correlation_id=correlation_id,
            data={"message": "Intake completed successfully"},
            next_steps=["Create tasks", "Ingest transactions", "Configure connectors"]
        )
    
    except Exception as e:
        return APIResponse(
            status="error",
            correlation_id=correlation_id,
            errors=[str(e)]
        )


# ============ SETTINGS ============

@app.get("/settings/{manager_id}", tags=["Settings"])
async def get_manager_settings(manager_id: str, repo: Repository = Depends(get_repo)):
    """Get settings for a specific manager"""
    settings = repo.get_manager_settings(manager_id)
    if not settings:
        raise HTTPException(status_code=404, detail=f"Manager {manager_id} not found")
    
    return {
        "manager_id": settings.manager_id,
        "enabled": settings.enabled,
        "config": settings.config,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    }


@app.put("/settings/{manager_id}", response_model=APIResponse, tags=["Settings"])
async def update_manager_settings(
    manager_id: str,
    config: dict,
    repo: Repository = Depends(get_repo)
):
    """Update settings for a specific manager"""
    import json
    
    correlation_id = generate_correlation_id()
    settings = repo.update_manager_settings(manager_id, config=json.dumps(config))
    
    repo.create_event(
        event_type="settings_updated",
        action=f"Updated settings for {manager_id}",
        agent=manager_id,
        correlation_id=correlation_id
    )
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={"manager_id": manager_id, "config": config}
    )


# ============ TRANSACTIONS ============

@app.post("/transactions/ingest", response_model=APIResponse, tags=["Transactions"])
async def ingest_transactions(
    request: TransactionIngest,
    repo: Repository = Depends(get_repo)
):
    """Bulk ingest transactions"""
    correlation_id = generate_correlation_id()
    
    result = repo.ingest_transactions(request)
    
    # Update spend budgets
    total_spend = sum(t.amount for t in request.transactions if not t.is_internal_transfer)
    if total_spend > 0:
        repo.update_budget_spend("monthly", total_spend)
        
        # Check daily (simplified - just add to daily too)
        repo.update_budget_spend("daily", total_spend)
    
    repo.create_event(
        event_type="transactions_ingested",
        action=f"Ingested {result['created']} transactions",
        details=result,
        correlation_id=correlation_id
    )
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data=result
    )


@app.get("/transactions", tags=["Transactions"])
async def list_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    repo: Repository = Depends(get_repo)
):
    """List transactions with filters"""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    
    transactions = repo.get_transactions(
        start_date=start,
        end_date=end,
        category=category,
        limit=limit
    )
    
    return {
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "merchant": t.merchant,
                "date": t.date.isoformat(),
                "category": t.consumption_category,
                "funding_source": t.funding_source,
                "payment_rail": t.payment_rail
            }
            for t in transactions
        ],
        "count": len(transactions)
    }


@app.get("/transactions/summary", tags=["Transactions"])
async def get_spend_summary(days: int = 7, repo: Repository = Depends(get_repo)):
    """Get spending summary"""
    return repo.get_spend_summary(days=days)


# ============ TASKS ============

@app.post("/tasks", response_model=APIResponse, tags=["Tasks"])
async def create_task(task: TaskCreate, repo: Repository = Depends(get_repo)):
    """Create a new task"""
    correlation_id = generate_correlation_id()
    
    db_task = repo.create_task(task)
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={
            "task_id": db_task.id,
            "title": db_task.title,
            "status": db_task.status
        }
    )


@app.get("/tasks", tags=["Tasks"])
async def list_tasks(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    repo: Repository = Depends(get_repo)
):
    """List tasks with filters"""
    tasks = repo.get_tasks(status=status, category=category, limit=limit)
    
    return {
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "estimated_cost": t.estimated_cost,
                "actual_cost": t.actual_cost
            }
            for t in tasks
        ],
        "total": len(tasks)
    }


@app.patch("/tasks/{task_id}", response_model=APIResponse, tags=["Tasks"])
async def update_task(task_id: int, update: TaskUpdate, repo: Repository = Depends(get_repo)):
    """Update a task"""
    correlation_id = generate_correlation_id()
    
    task = repo.update_task(task_id, update)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={"task_id": task.id, "status": task.status}
    )


@app.patch("/tasks/{task_id}/complete", response_model=APIResponse, tags=["Tasks"])
async def complete_task(
    task_id: int,
    evidence: Optional[str] = None,
    actual_cost: Optional[float] = None,
    repo: Repository = Depends(get_repo)
):
    """Mark a task as complete"""
    correlation_id = generate_correlation_id()
    
    task = repo.complete_task(task_id, evidence=evidence, actual_cost=actual_cost)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={"task_id": task.id, "status": "completed"}
    )


# ============ EVENTS ============

@app.get("/events", tags=["Events"])
async def list_events(
    event_type: Optional[str] = None,
    limit: int = 50,
    repo: Repository = Depends(get_repo)
):
    """List system events"""
    events = repo.get_events(event_type=event_type, limit=limit)
    
    return {
        "events": [
            {
                "id": e.id,
                "correlation_id": e.correlation_id,
                "event_type": e.event_type,
                "action": e.action,
                "agent": e.agent,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": e.details,
                "timestamp": e.timestamp.isoformat()
            }
            for e in events
        ],
        "count": len(events)
    }


# ============ COST ============

@app.post("/cost", response_model=APIResponse, tags=["Cost"])
async def record_cost(cost: CostRecord, repo: Repository = Depends(get_repo)):
    """Record an AI/system cost"""
    correlation_id = generate_correlation_id()
    
    db_cost = repo.record_cost(cost)
    
    # Check budget warnings
    budget_status = repo.check_budget_status("system", 0)
    warnings = budget_status.get("warnings", [])
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={
            "cost_id": db_cost.id,
            "estimated_cost": db_cost.estimated_cost,
            "budget_warnings": warnings
        }
    )


@app.get("/cost", response_model=CostSummary, tags=["Cost"])
async def get_cost_summary(period: str = "month", repo: Repository = Depends(get_repo)):
    """Get cost summary for a period (today, month, all)"""
    return repo.get_cost_summary(period=period)


@app.get("/cost/budget", tags=["Cost"])
async def get_budget_status(repo: Repository = Depends(get_repo)):
    """Get all budget statuses"""
    budgets = repo.get_all_budgets()
    
    return {
        "budgets": [
            {
                **repo.check_budget_status(b.budget_type),
                "name": b.name
            }
            for b in budgets
        ]
    }


# ============ PORTFOLIO ============

@app.get("/portfolio", tags=["Portfolio"])
async def get_portfolio():
    """Get portfolio holdings with current prices"""
    import yfinance as yf
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    db = get_db_session()
    
    try:
        # Get holdings from database
        holdings = db.execute(
            text("SELECT ticker, shares, asset_type FROM portfolio_holdings WHERE portfolio_name = 'Lamido Main'")
        ).fetchall()
        
        # Get cash
        cash_row = db.execute(
            text("SELECT amount FROM cash_holdings WHERE account_name = 'Checking' LIMIT 1")
        ).fetchone()
        cash = float(cash_row[0]) if cash_row else 0.0
        
        if not holdings:
            return {"holdings": [], "total_value": cash, "cash": cash}
        
        # Fetch current prices
        tickers = [h[0] for h in holdings]
        prices = {}
        
        try:
            data = yf.download(tickers, period="1d", progress=False)
            if 'Close' in data.columns:
                for ticker in tickers:
                    if ticker in data['Close'].columns:
                        price = data['Close'][ticker].iloc[-1]
                        if not pd.isna(price):
                            prices[ticker] = float(price)
            elif len(tickers) == 1:
                price = data['Close'].iloc[-1]
                if not pd.isna(price):
                    prices[tickers[0]] = float(price)
        except Exception as e:
            print(f"[Portfolio] Price fetch error: {e}")
        
        # Build response
        result = []
        total_value = cash
        
        for ticker, shares, asset_type in holdings:
            shares_f = float(shares)  # Convert Decimal to float
            price = prices.get(ticker, 0)
            value = shares_f * price
            total_value += value
            
            result.append({
                "ticker": ticker,
                "shares": shares_f,
                "asset_type": asset_type,
                "price": round(price, 2),
                "value": round(value, 2),
            })
        
        return {
            "holdings": result,
            "total_value": round(total_value, 2),
            "cash": round(cash, 2),
        }
    finally:
        db.close()


@app.post("/portfolio/holdings", tags=["Portfolio"])
async def add_or_update_holding(request: dict):
    """Add or update a portfolio holding"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    ticker = request.get("ticker", "").upper()
    shares = request.get("shares", 0)
    asset_type = request.get("asset_type", "stock")
    
    if not ticker or shares <= 0:
        return {"success": False, "error": "Invalid ticker or shares"}
    
    db = get_db_session()
    try:
        # Check if exists
        existing = db.execute(
            text("SELECT id FROM portfolio_holdings WHERE ticker = :ticker AND portfolio_name = 'Lamido Main'"),
            {"ticker": ticker}
        ).fetchone()
        
        if existing:
            db.execute(
                text("UPDATE portfolio_holdings SET shares = :shares, asset_type = :asset_type, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                {"shares": shares, "asset_type": asset_type, "id": existing[0]}
            )
        else:
            db.execute(
                text("INSERT INTO portfolio_holdings (portfolio_name, ticker, shares, asset_type) VALUES ('Lamido Main', :ticker, :shares, :asset_type)"),
                {"ticker": ticker, "shares": shares, "asset_type": asset_type}
            )
        
        db.commit()
        return {"success": True, "ticker": ticker, "shares": shares}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@app.delete("/portfolio/holdings/{ticker}", tags=["Portfolio"])
async def delete_holding(ticker: str):
    """Remove a holding from portfolio"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    db = get_db_session()
    try:
        db.execute(
            text("DELETE FROM portfolio_holdings WHERE ticker = :ticker AND portfolio_name = 'Lamido Main'"),
            {"ticker": ticker.upper()}
        )
        db.commit()
        return {"success": True, "deleted": ticker.upper()}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@app.delete("/portfolio/clear", tags=["Portfolio"])
async def clear_portfolio():
    """Clear all holdings from portfolio"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    db = get_db_session()
    try:
        # Count before deleting
        count = db.execute(
            text("SELECT COUNT(*) FROM portfolio_holdings WHERE portfolio_name = 'Lamido Main'")
        ).scalar()
        
        # Delete all holdings
        db.execute(
            text("DELETE FROM portfolio_holdings WHERE portfolio_name = 'Lamido Main'")
        )
        
        # Also clear cash
        db.execute(
            text("DELETE FROM cash_holdings WHERE account_name = 'Checking'")
        )
        
        db.commit()
        return {"success": True, "deleted_count": count, "message": f"Cleared {count} holdings"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@app.put("/portfolio/cash", tags=["Portfolio"])
async def update_cash(request: dict):
    """Update cash holdings"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    amount = request.get("amount", 0)
    
    db = get_db_session()
    try:
        # Check if exists
        exists = db.execute(
            text("SELECT id FROM cash_holdings WHERE account_name = 'Checking'")
        ).fetchone()
        
        if exists:
            db.execute(
                text("UPDATE cash_holdings SET amount = :amount, updated_at = CURRENT_TIMESTAMP WHERE account_name = 'Checking'"),
                {"amount": amount}
            )
        else:
            db.execute(
                text("INSERT INTO cash_holdings (account_name, amount) VALUES ('Checking', :amount)"),
                {"amount": amount}
            )
        
        db.commit()
        return {"success": True, "cash": amount}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ============ AGENT SYSTEM MONITORING ============

# Global agent instances (singleton pattern)
_agents = {}

def get_agent(name: str):
    """Get or create agent instance"""
    global _agents
    if name not in _agents:
        try:
            from ..agents import (
                FinanceAgent, MaintenanceAgent, ContractorsAgent,
                ProjectsAgent, SecurityManagerAgent, JanitorAgent, ManagerAgent
            )
            
            agent_map = {
                "finance": FinanceAgent,
                "maintenance": MaintenanceAgent,
                "contractors": ContractorsAgent,
                "projects": ProjectsAgent,
                "janitor": JanitorAgent,
                "security-manager": SecurityManagerAgent,
                "security": SecurityManagerAgent,  # alias
                "manager": ManagerAgent,
            }
            
            AgentClass = agent_map.get(name)
            if AgentClass:
                _agents[name] = AgentClass()
            else:
                print(f"[Agents] Unknown agent: {name}")
                return None
        except Exception as e:
            print(f"[Agents] Failed to load {name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    return _agents.get(name)


@app.post("/system/startup", tags=["System"])
async def system_startup():
    """
    Initialize and start all agents.
    Called when user clicks "Turn On System" button.
    Updates both the real agents AND the _agent_states dict used by monitoring.
    """
    from datetime import datetime
    from .system_routes import _agent_states
    
    started_agents = []
    failed_agents = []
    now = datetime.now().isoformat()
    
    agent_names = ["manager", "finance", "maintenance", "contractors", "projects", "security", "janitor"]
    
    # Map API names to _agent_states keys
    # No mapping needed - agent names match _agent_states keys
    state_key_map = {}
    
    for name in agent_names:
        try:
            agent = get_agent(name)
            if agent:
                # Ensure agent is started
                if agent.status != "running":
                    agent.start()
                
                # Update the _agent_states dict that the UI reads
                state_key = state_key_map.get(name, name)
                if state_key in _agent_states:
                    _agent_states[state_key]["state"] = "running"
                    _agent_states[state_key]["loaded_at"] = now
                    _agent_states[state_key]["error_count"] = 0
                
                started_agents.append({
                    "id": name,
                    "name": agent.name,
                    "emoji": agent.emoji,
                    "status": agent.status
                })
            else:
                failed_agents.append({"id": name, "error": "Agent not found"})
        except Exception as e:
            failed_agents.append({"id": name, "error": str(e)})
    
    return {
        "success": len(failed_agents) == 0,
        "started": started_agents,
        "failed": failed_agents,
        "message": f"Started {len(started_agents)} agents" + (f", {len(failed_agents)} failed" if failed_agents else "")
    }


@app.post("/system/shutdown", tags=["System"])
async def system_shutdown():
    """Stop all agents gracefully"""
    from .system_routes import _agent_states
    
    stopped_agents = []
    
    agent_names = ["finance", "maintenance", "contractors", "projects", "security", "janitor", "manager"]
    state_key_map = {}  # No mapping needed
    
    for name in agent_names:
        try:
            agent = get_agent(name)
            if agent and agent.status == "running":
                agent.stop()
                stopped_agents.append(name)
            
            # Update _agent_states
            state_key = state_key_map.get(name, name)
            if state_key in _agent_states:
                _agent_states[state_key]["state"] = "stopped"
                _agent_states[state_key]["loaded_at"] = None
        except Exception:
            pass
    
    return {
        "success": True,
        "stopped": stopped_agents,
        "message": f"Stopped {len(stopped_agents)} agents"
    }


@app.get("/system/monitor", tags=["System"])
async def get_system_monitor():
    """Get real-time system monitoring data from actual agents"""
    import psutil
    
    agent_names = ["finance", "maintenance", "contractors", "projects", "janitor", "security", "manager"]
    processes = []
    agents_active = 0
    
    for name in agent_names:
        agent = get_agent(name)
        proc_data = {
            "id": name,
            "name": name.replace("-", " ").replace("_", " ").title() + " Agent",
            "state": "not_loaded",
            "uptime": 0,
            "memory_mb": 0,
            "cpu_percent": 0,
            "pending_tasks": 0,
            "error_count": 0,
            "last_heartbeat": "never",
            "metrics": {},
            "recent_logs": [],
        }
        
        if agent:
            try:
                status = agent.get_status()
                pending = agent.get_pending_tasks()
                logs = agent.get_recent_logs(20)
                
                proc_data["state"] = status.get("status", "unknown")
                proc_data["pending_tasks"] = len(pending)
                proc_data["error_count"] = sum(1 for log in logs if log.get("status") == "error")
                proc_data["last_heartbeat"] = status.get("last_check", datetime.now().isoformat())
                proc_data["metrics"] = status.get("metrics", {})
                proc_data["recent_logs"] = logs
                
                if proc_data["state"] in ["active", "running"]:
                    agents_active += 1
            except Exception as e:
                proc_data["state"] = "error"
                proc_data["error"] = str(e)
                proc_data["error_count"] = 1
        
        processes.append(proc_data)
    
    # Get system resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
    except Exception:
        cpu_percent = 0
        memory_percent = 0
    
    return {
        "processes": processes,
        "resources": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "agents_active": agents_active,
            "agents_total": len(agent_names),
            "cost_today": 0,
        },
        "_debug_timestamp": datetime.now().isoformat(),
        "_debug_proc_count": len(processes),
        "_debug_first_proc_keys": list(processes[0].keys()) if processes else [],
    }


@app.get("/agents", tags=["Agents"])
async def list_agents():
    """List all agents with their current status"""
    agent_names = ["finance", "maintenance", "contractors", "projects", "janitor", "security", "manager"]
    agents = []
    
    for name in agent_names:
        agent = get_agent(name)
        if agent:
            try:
                status = agent.get_status()
                pending = agent.get_pending_tasks()
                agents.append({
                    "id": name,
                    "name": name.title().replace("_", " ") + " Agent",
                    "status": status,
                    "pending_tasks": pending,
                    "task_count": len(pending),
                })
            except Exception as e:
                agents.append({
                    "id": name,
                    "name": name.title().replace("_", " ") + " Agent",
                    "error": str(e),
                    "status": {"status": "error"},
                })
    
    return {"agents": agents}


@app.get("/agents/{agent_id}", tags=["Agents"])
async def get_agent_detail(agent_id: str):
    """Get detailed status for a specific agent"""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    try:
        status = agent.get_status()
        pending = agent.get_pending_tasks()
        logs = agent.get_recent_logs(20)
        soul = agent.get_soul()
        memory = agent.get_memory()
        
        return {
            "id": agent_id,
            "name": agent_id.title().replace("_", " ") + " Agent",
            "status": status,
            "pending_tasks": pending,
            "recent_logs": logs,
            "soul": soul[:500] + "..." if len(soul) > 500 else soul,  # Truncate
            "memory_preview": memory[:500] + "..." if len(memory) > 500 else memory,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_id}/execute", tags=["Agents"])
async def execute_agent_task(agent_id: str, request: dict):
    """Execute a task on a specific agent"""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    task_id = request.get("task_id")
    action = request.get("action", "execute")
    
    try:
        if action == "execute" and task_id:
            result = agent.execute_task(task_id)
        else:
            result = {"error": "Invalid action or missing task_id"}
        
        return {
            "agent": agent_id,
            "task_id": task_id,
            "action": action,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/{agent_id}/chat", tags=["Agents"])
async def chat_with_agent(agent_id: str, request: dict):
    """
    Chat directly with a specific agent.
    Each agent has its own personality and domain expertise.
    """
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    message = request.get("message", "").strip()
    if not message:
        return {"response": "No message provided", "success": False}
    
    try:
        response = await agent.chat(message)
        return {
            "response": response,
            "success": True,
            "agent_id": agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
        }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "success": False,
            "agent_id": agent_id,
        }


@app.get("/api/agents/{agent_id}/activity", tags=["Agents"])
async def get_agent_activity(agent_id: str, limit: int = 20):
    """
    Get recent activity logs for a specific agent.
    Returns real activity data from the agent's log.
    """
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    try:
        logs = agent.get_recent_logs(limit)
        # Format for frontend
        activity = [
            {
                "timestamp": log.get("timestamp", ""),
                "action": log.get("details", log.get("action", "")),
                "details": None,  # Could add more context here
            }
            for log in logs
        ]
        return {
            "activity": activity,
            "agent_id": agent_id,
            "agent_name": agent.name,
        }
    except Exception as e:
        return {"activity": [], "error": str(e)}


@app.get("/api/agent-activity/{agent_id}/activity", tags=["Agents"])
async def get_rich_agent_activity(agent_id: str):
    """
    Get rich activity data for HYPERCONTEXT-style dashboard.
    Returns files touched, tools used, decisions, questions, heat map, etc.
    """
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    try:
        # Get activity data from agent
        activity_data = agent.get_rich_activity()
        return activity_data
    except Exception as e:
        # Return empty but valid structure on error
        return {
            "agent_id": agent_id,
            "session_id": None,
            "period_start": datetime.now().isoformat(),
            "period_end": datetime.now().isoformat(),
            "total_files": 0,
            "files_modified": 0,
            "files_read": 0,
            "tool_usage": {},
            "systems": {},
            "decisions_count": 0,
            "open_questions_count": 0,
            "files_touched": [],
            "decisions": [],
            "questions": [],
            "threads": [],
            "heat_map": [],
            "context_percent": 0,
            "context_used": 0,
            "context_limit": 200000,
            "runway_tokens": 200000,
            "velocity": 0,
            "error": str(e),
        }


@app.post("/api/agents/{agent_id}/log", tags=["Agents"])
async def log_agent_action(agent_id: str, request: dict):
    """
    Log an action to a specific agent (used by frontend for tracking).
    Primarily used by Janitor for system-wide action logging.
    """
    agent = get_agent(agent_id)
    if not agent:
        # Create a minimal response even if agent not loaded
        return {"success": False, "reason": "agent_not_loaded"}
    
    action = request.get("action", "unknown")
    details = request.get("details", "")
    status = request.get("status", "success")
    
    try:
        agent.log_action(action, details, status)
        return {
            "success": True,
            "agent_id": agent_id,
            "logged": {"action": action, "details": details},
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/agents/{agent_id}/notify", tags=["Agents"])
async def notify_agent(agent_id: str, request: dict):
    """
    Send a notification to a specific agent.
    The agent will log it and potentially take action.
    """
    agent = get_agent(agent_id)
    if not agent:
        return {"success": False, "reason": "agent_not_loaded"}
    
    message = request.get("message", "")
    priority = request.get("priority", "normal")
    
    try:
        agent.log_action(f"notification_{priority}", message, "info")
        return {
            "success": True,
            "agent_id": agent_id,
            "notified": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ CONTRACTORS ============

@app.get("/contractors", tags=["Contractors"])
async def list_contractors():
    """List all contractors from the directory"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    db = get_db_session()
    try:
        # Get contractors from the contractors table
        contractors = db.execute(
            text("SELECT id, name, company, phone, email, service_type, hourly_rate, rating, notes, last_service_date FROM contractors ORDER BY name")
        ).fetchall()
        
        return {
            "contractors": [
                {
                    "id": c[0],
                    "name": c[1],
                    "company": c[2],
                    "phone": c[3],
                    "email": c[4],
                    "service_type": c[5],
                    "hourly_rate": float(c[6]) if c[6] else None,
                    "rating": c[7],
                    "notes": c[8],
                    "last_service_date": c[9].isoformat() if c[9] else None,
                }
                for c in contractors
            ],
            "count": len(contractors)
        }
    except Exception as e:
        return {"contractors": [], "count": 0, "error": str(e)}
    finally:
        db.close()


@app.post("/contractors", tags=["Contractors"])
async def add_contractor(request: dict):
    """Add a new contractor to the directory"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    name = request.get("name", "").strip()
    if not name:
        return {"success": False, "error": "Name is required"}
    
    db = get_db_session()
    try:
        db.execute(
            text("""INSERT INTO contractors (name, company, phone, email, service_type, hourly_rate, rating, notes) 
                    VALUES (:name, :company, :phone, :email, :service_type, :hourly_rate, :rating, :notes)"""),
            {
                "name": name,
                "company": request.get("company"),
                "phone": request.get("phone"),
                "email": request.get("email"),
                "service_type": request.get("service_type", "General"),
                "hourly_rate": request.get("hourly_rate"),
                "rating": request.get("rating"),
                "notes": request.get("notes"),
            }
        )
        db.commit()
        return {"success": True, "message": f"Added contractor: {name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@app.delete("/contractors/{contractor_id}", tags=["Contractors"])
async def delete_contractor(contractor_id: int):
    """Remove a contractor from the directory"""
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    db = get_db_session()
    try:
        db.execute(text("DELETE FROM contractors WHERE id = :id"), {"id": contractor_id})
        db.commit()
        return {"success": True, "deleted": contractor_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ============ CONTRACTOR JOBS ============

@app.post("/jobs", response_model=APIResponse, tags=["Contractor Jobs"])
async def create_contractor_job(
    job: ContractorJobCreate,
    repo: Repository = Depends(get_repo)
):
    """Create a contractor job (proposed status)"""
    correlation_id = generate_correlation_id()
    
    db_job = repo.create_contractor_job(job)
    
    next_steps = ["Contact contractor to schedule"]
    if job.estimated_cost:
        next_steps.append("Submit cost for finance approval")
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={
            "job_id": db_job.id,
            "status": db_job.status,
            "description": db_job.description
        },
        next_steps=next_steps
    )


@app.get("/jobs", tags=["Contractor Jobs"])
async def list_contractor_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    repo: Repository = Depends(get_repo)
):
    """List contractor jobs"""
    jobs = repo.get_contractor_jobs(status=status, limit=limit)
    
    return {
        "jobs": [
            {
                "id": j.id,
                "description": j.description,
                "contractor_name": j.contractor_name,
                "status": j.status,
                "estimated_cost": j.estimated_cost,
                "approved_cost": j.approved_cost,
                "actual_cost": j.actual_cost,
                "proposed_start": j.proposed_start.isoformat() if j.proposed_start else None,
                "confirmed_start": j.confirmed_start.isoformat() if j.confirmed_start else None
            }
            for j in jobs
        ],
        "total": len(jobs)
    }


@app.patch("/jobs/{job_id}/schedule", response_model=APIResponse, tags=["Contractor Jobs"])
async def schedule_job(
    job_id: int,
    confirmed_start: str,
    confirmed_end: str,
    contractor_name: Optional[str] = None,
    repo: Repository = Depends(get_repo)
):
    """Schedule a contractor job"""
    correlation_id = generate_correlation_id()
    
    job = repo.update_contractor_job(
        job_id,
        status="scheduled",
        confirmed_start=date.fromisoformat(confirmed_start),
        confirmed_end=date.fromisoformat(confirmed_end),
        contractor_name=contractor_name
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={"job_id": job.id, "status": "scheduled"},
        next_steps=["Submit cost for approval", "Wait for job to start"]
    )


@app.patch("/jobs/{job_id}/approve-cost", response_model=APIResponse, tags=["Contractor Jobs"])
async def approve_job_cost(
    job_id: int,
    amount: float,
    repo: Repository = Depends(get_repo)
):
    """Finance manager approves job cost"""
    correlation_id = generate_correlation_id()
    
    # Check budget
    budget_status = repo.check_budget_status("monthly", amount)
    
    if not budget_status["can_proceed"]:
        repo.update_contractor_job(
            job_id,
            cost_status="rejected",
            notes=budget_status.get("block_reason", "Budget exceeded")
        )
        
        return APIResponse(
            status="error",
            correlation_id=correlation_id,
            errors=[budget_status.get("block_reason", "Budget exceeded")],
            data={"job_id": job_id, "cost_status": "rejected"}
        )
    
    # Approve
    job = repo.update_contractor_job(
        job_id,
        approved_cost=amount,
        cost_status="approved"
    )
    
    # Update budget
    repo.update_budget_spend("monthly", amount)
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={
            "job_id": job_id,
            "cost_status": "approved",
            "approved_cost": amount,
            "budget_warnings": budget_status.get("warnings", [])
        }
    )


@app.patch("/jobs/{job_id}/complete", response_model=APIResponse, tags=["Contractor Jobs"])
async def complete_job(
    job_id: int,
    actual_cost: Optional[float] = None,
    evidence: Optional[str] = None,
    repo: Repository = Depends(get_repo)
):
    """Complete a contractor job"""
    correlation_id = generate_correlation_id()
    
    job = repo.update_contractor_job(
        job_id,
        status="completed",
        actual_end=date.today(),
        actual_cost=actual_cost,
        evidence=evidence
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={"job_id": job.id, "status": "completed", "actual_cost": actual_cost}
    )


# ============ BACKUP ============

@app.post("/backup/export", response_model=APIResponse, tags=["Backup"])
async def export_backup(notes: Optional[str] = None, repo: Repository = Depends(get_repo)):
    """Export database backup"""
    from ..agents.backup import BackupAgent
    
    correlation_id = generate_correlation_id()
    backup_agent = BackupAgent(repo)
    
    result = backup_agent.export_backup(notes=notes)
    
    return APIResponse(
        status="success" if result.get("success") else "error",
        correlation_id=correlation_id,
        data=result,
        errors=result.get("errors")
    )


@app.post("/backup/restore", response_model=APIResponse, tags=["Backup"])
async def restore_backup(request: BackupRestore, repo: Repository = Depends(get_repo)):
    """Restore from backup"""
    from ..agents.backup import BackupAgent
    
    correlation_id = generate_correlation_id()
    backup_agent = BackupAgent(repo)
    
    result = backup_agent.restore_backup(
        backup_path=request.backup_path,
        verify_checksum=request.verify_checksum,
        dry_run=request.dry_run
    )
    
    return APIResponse(
        status="success" if result.get("success") else "error",
        correlation_id=correlation_id,
        data=result,
        errors=result.get("errors")
    )


@app.get("/backup/list", tags=["Backup"])
async def list_backups():
    """List available backups"""
    from pathlib import Path
    
    backup_dir = Path(__file__).parent.parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    backups = []
    for f in backup_dir.glob("*.zip"):
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": f.stat().st_size,
            "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat()
        })
    
    return {"backups": sorted(backups, key=lambda x: x["created"], reverse=True)}


@app.get("/database/stats", tags=["Database"])
async def get_database_stats():
    """Get database size and backup info"""
    from pathlib import Path
    
    # Get database file size
    db_path = Path(__file__).parent.parent.parent / "data" / "mycasa_pro.db"
    db_size_bytes = 0
    if db_path.exists():
        db_size_bytes = db_path.stat().st_size
    
    # Format size
    if db_size_bytes < 1024:
        db_size_str = f"{db_size_bytes} B"
    elif db_size_bytes < 1024 * 1024:
        db_size_str = f"{db_size_bytes / 1024:.1f} KB"
    else:
        db_size_str = f"{db_size_bytes / (1024 * 1024):.1f} MB"
    
    # Get last backup
    backup_dir = Path(__file__).parent.parent.parent / "backups"
    last_backup = None
    if backup_dir.exists():
        backups = list(backup_dir.glob("*.zip"))
        if backups:
            latest = max(backups, key=lambda f: f.stat().st_ctime)
            last_backup = datetime.fromtimestamp(latest.stat().st_ctime).isoformat()
    
    return {
        "size_bytes": db_size_bytes,
        "size_formatted": db_size_str,
        "last_backup": last_backup,
        "path": str(db_path)
    }


@app.post("/database/reset", tags=["Database"])
async def reset_database():
    """Reset database to defaults (DANGER)"""
    from pathlib import Path
    import shutil
    
    db_path = Path(__file__).parent.parent.parent / "data" / "mycasa_pro.db"
    
    # Create backup first
    if db_path.exists():
        backup_dir = Path(__file__).parent.parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"pre_reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(db_path, backup_path)
        
        # Delete the database
        db_path.unlink()
    
    # Re-initialize
    from ..storage.database import init_db
    init_db()
    
    return {
        "success": True,
        "message": "Database reset to defaults. Previous data backed up.",
    }


@app.post("/database/clear", tags=["Database"])
async def clear_database(repo: Repository = Depends(get_repo)):
    """Clear all data from database (DANGER)"""
    from ..storage.models import (
        TaskDB, TransactionDB, ContractorJobDB, EventDB, 
        CostRecordDB, InboxMessageDB, ApprovalDB
    )
    
    # Clear tables (keep settings)
    repo.db.query(TaskDB).delete()
    repo.db.query(TransactionDB).delete()
    repo.db.query(ContractorJobDB).delete()
    repo.db.query(EventDB).delete()
    repo.db.query(CostRecordDB).delete()
    repo.db.query(InboxMessageDB).delete()
    repo.db.query(ApprovalDB).delete()
    repo.db.commit()
    
    return {
        "success": True,
        "message": "All data cleared. Settings preserved.",
    }


# ============ WHATSAPP CONNECTOR ============

@app.get("/api/connectors/whatsapp/status", tags=["Connectors"])
async def get_whatsapp_status():
    """Get WhatsApp connection status"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["wacli", "auth", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            import json
            status_data = json.loads(result.stdout)
            # wacli returns { success: true, data: { authenticated: true }, error: null }
            data = status_data.get("data", status_data)  # Handle both formats
            is_authenticated = data.get("authenticated", False)
            return {
                "connected": is_authenticated,
                "phone": data.get("phone", None),
                "status": "connected" if is_authenticated else "disconnected",
            }
    except FileNotFoundError:
        return {
            "connected": False,
            "phone": None,
            "status": "not_installed",
            "error": "wacli not installed. Run: npm install -g @nicholasoxford/wacli"
        }
    except Exception as e:
        pass
    
    return {
        "connected": False,
        "phone": None,
        "status": "unknown",
        "error": "Could not check status"
    }


@app.get("/api/connectors/whatsapp/qr", tags=["Connectors"])
async def get_whatsapp_qr():
    """
    Generate WhatsApp QR code for linking.
    Checks wacli status first, provides manual instructions if needed.
    """
    import subprocess
    
    try:
        # First check if already authenticated via wacli
        status_result = subprocess.run(
            ["wacli", "auth", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if status_result.returncode == 0:
            import json
            try:
                status_data = json.loads(status_result.stdout)
                # wacli returns { success: true, data: { authenticated: true }, error: null }
                data = status_data.get("data", status_data)  # Handle both formats
                if data.get("authenticated"):
                    return {
                        "success": True,
                        "already_connected": True,
                        "phone": data.get("phone"),
                        "message": "WhatsApp is already connected via wacli"
                    }
            except Exception as e:
                pass
        
        # wacli not authenticated - provide instructions
        # QR generation requires interactive terminal, so we give instructions
        return {
            "success": False,
            "needs_manual_setup": True,
            "error": "WhatsApp requires terminal setup",
            "instructions": [
                "1. Open Terminal",
                "2. Install wacli: npm install -g @nicholasoxford/wacli",
                "3. Run: wacli auth",
                "4. Scan QR code with WhatsApp",
                "5. Return here and click 'Check Again'"
            ],
            "hint": "Run 'npm install -g @nicholasoxford/wacli && wacli auth' in terminal"
        }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout checking status",
            "hint": "Try running 'wacli auth status' in terminal"
        }
    except FileNotFoundError:
        return {
            "success": False,
            "needs_manual_setup": True,
            "error": "wacli not installed",
            "instructions": [
                "1. Open Terminal",
                "2. Install wacli: npm install -g @nicholasoxford/wacli",
                "3. Run: wacli auth",
                "4. Scan QR code with WhatsApp",
                "5. Return here and click 'Check Again'"
            ],
            "hint": "Install with: npm install -g @nicholasoxford/wacli"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============ INBOX (for compatibility with existing frontend) ============

@app.get("/inbox/messages", tags=["Inbox"])
async def get_inbox_messages(
    source: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    repo: Repository = Depends(get_repo)
):
    """Get inbox messages"""
    messages = repo.get_inbox_messages(source=source, unread_only=unread_only, limit=limit)
    
    return {
        "messages": [
            {
                "id": m.id,
                "source": m.source,
                "sender": m.sender_name,
                "sender_name": m.sender_name,
                "sender_id": m.sender_id,
                "subject": m.subject,
                "body": m.preview or "",
                "timestamp": m.timestamp.isoformat(),
                "domain": m.domain,
                "is_read": m.is_read,
                "linked_task_id": m.linked_task_id
            }
            for m in messages
        ],
        "count": len(messages)
    }


@app.get("/inbox/unread-count", tags=["Inbox"])
async def get_unread_count(repo: Repository = Depends(get_repo)):
    """Get unread message counts"""
    return repo.get_unread_counts()


@app.patch("/inbox/messages/{message_id}/read", tags=["Inbox"])
async def mark_message_read(message_id: int, repo: Repository = Depends(get_repo)):
    """Mark a message as read"""
    msg = repo.mark_message_read(message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"success": True, "message_id": message_id}


@app.patch("/inbox/mark-all-read", tags=["Inbox"])
async def mark_all_messages_read(
    source: Optional[str] = None,
    repo: Repository = Depends(get_repo)
):
    """Mark all messages as read, optionally filtered by source (gmail/whatsapp)"""
    from ..storage.models import InboxMessageDB
    
    query = repo.db.query(InboxMessageDB).filter(InboxMessageDB.is_read == False)
    
    if source:
        query = query.filter(InboxMessageDB.source == source)
    
    count = query.count()
    query.update({"is_read": True})
    repo.db.commit()
    
    return {
        "success": True,
        "marked_read": count,
        "message": f"Marked {count} messages as read"
    }


@app.delete("/inbox/clear", tags=["Inbox"])
async def clear_inbox(
    source: Optional[str] = None,
    repo: Repository = Depends(get_repo)
):
    """Clear all inbox messages, optionally filtered by source"""
    from ..storage.models import InboxMessageDB
    
    query = repo.db.query(InboxMessageDB)
    
    if source:
        query = query.filter(InboxMessageDB.source == source)
    
    count = query.count()
    query.delete()
    repo.db.commit()
    
    return {
        "success": True,
        "deleted": count,
        "message": f"Cleared {count} messages"
    }


@app.post("/inbox/ingest", tags=["Inbox"])
async def sync_inbox(repo: Repository = Depends(get_repo)):
    """Sync inbox from Gmail (unread only) and WhatsApp (whitelisted contacts only)"""
    from ..connectors import gmail_connector, whatsapp_connector
    
    # Gmail: only unread emails from last 7 days
    gmail_result = gmail_connector.fetch_messages(days_back=7, max_results=30, unread_only=True)
    
    # WhatsApp: only whitelisted contacts
    whatsapp_result = whatsapp_connector.fetch_messages(limit=20)
    
    # Store new messages
    new_count = 0
    from ..storage.models import InboxMessageDB
    
    for msg in gmail_result + whatsapp_result:
        existing = repo.db.query(InboxMessageDB).filter(
            InboxMessageDB.external_id == msg["external_id"]
        ).first()
        
        if not existing:
            db_msg = InboxMessageDB(**msg)
            repo.db.add(db_msg)
            new_count += 1
    
    repo.db.commit()
    
    return {
        "success": True,
        "gmail_count": len(gmail_result),
        "whatsapp_count": len(whatsapp_result),
        "new_messages": new_count
    }


# ============ INBOX SYNC CONTROL ============

@app.get("/inbox/sync-status", tags=["Inbox"])
async def get_sync_status():
    """Get background sync status"""
    global _sync_task, _sync_enabled
    
    return {
        "enabled": _sync_enabled,
        "sync_task_running": _sync_task is not None and not _sync_task.done(),
        "sync_interval_seconds": SYNC_INTERVAL_SECONDS,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "last_sync_at": _last_sync_at,
        "last_sync_result": _last_sync_result,
    }


@app.post("/inbox/launch", tags=["Inbox"])
async def launch_inbox_sync(repo: Repository = Depends(get_repo)):
    """
    Launch inbox sync - FRESH START.
    Clears existing messages, fetches everything fresh, generates Manager report.
    """
    global _sync_enabled
    from ..storage.models import InboxMessageDB
    
    _sync_enabled = True
    log_action("inbox_sync_enabled", {"trigger": "user_launch"})
    
    # Clear existing messages for fresh start
    print("[SYNC] Clearing existing inbox messages for fresh start...")
    deleted_count = repo.db.query(InboxMessageDB).delete()
    repo.db.commit()
    print(f"[SYNC] Cleared {deleted_count} existing messages")
    
    # Run fresh sync
    print("[SYNC] User launched inbox sync - fetching fresh...")
    result = await _run_inbox_sync()
    log_action("inbox_sync", {"trigger": "launch_fresh", "result": result, "cleared": deleted_count})
    
    # Generate Manager report
    manager_report = _generate_launch_report(result, deleted_count)
    
    # Queue report to Manager chat
    queue_manager_message(manager_report["text"])
    
    return {
        "success": "error" not in result,
        "enabled": True,
        "fresh_start": True,
        "cleared_messages": deleted_count,
        "manager_report": manager_report,
        **result
    }


def _generate_launch_report(sync_result: dict, cleared: int) -> dict:
    """Generate Manager's launch report"""
    gmail_count = sync_result.get("gmail", 0)
    whatsapp_count = sync_result.get("whatsapp", 0)
    new_count = sync_result.get("new", 0)
    
    # Build report text
    report_lines = [
        "📬 **Inbox Launch Report**",
        "",
        f"🔄 Fresh sync completed:",
        f"  • Cleared {cleared} old messages",
        f"  • Gmail: {gmail_count} messages fetched",
        f"  • WhatsApp: {whatsapp_count} messages fetched", 
        f"  • Total new: {new_count}",
        "",
        "⏰ Auto-sync enabled (every 15 min)",
    ]
    
    # Add summary of what needs attention
    if new_count > 0:
        report_lines.append(f"")
        report_lines.append(f"📋 {new_count} messages ready for review in Inbox")
    
    return {
        "text": "\n".join(report_lines),
        "gmail_count": gmail_count,
        "whatsapp_count": whatsapp_count,
        "new_count": new_count,
        "cleared": cleared,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/inbox/stop", tags=["Inbox"])
async def stop_inbox_sync():
    """Stop periodic inbox sync"""
    global _sync_enabled
    
    _sync_enabled = False
    log_action("inbox_sync_disabled", {"trigger": "user_stop"})
    
    return {
        "success": True,
        "enabled": False,
        "message": "Inbox sync stopped."
    }


@app.post("/inbox/sync", tags=["Inbox"])
async def trigger_sync():
    """Manually trigger a one-time inbox sync (does not enable periodic sync)"""
    result = await _run_inbox_sync()
    log_action("inbox_sync", {"trigger": "manual", "result": result})
    return {
        "success": "error" not in result,
        **result
    }


# ============ MANAGER CHAT (FULL CLAWDBOT POWER) ============

from fastapi import WebSocket, WebSocketDisconnect
from ..core.clawdbot_runner import (
    get_runner, ExecutionContext
)

# Active WebSocket connections
_ws_connections: dict = {}


@app.get("/manager/messages", tags=["Manager"])
async def get_manager_messages():
    """Get pending manager messages for the chat UI"""
    global _manager_messages
    return {"messages": _manager_messages}


@app.post("/manager/messages/ack", tags=["Manager"])
async def ack_manager_messages():
    """Acknowledge (clear) manager messages after they've been displayed"""
    global _manager_messages
    _manager_messages = []
    return {"success": True}


def _detect_intent(message: str) -> tuple:
    """
    Detect intent from message to route to appropriate agent.
    Returns (agent, action, entities) or (None, None, None) for general Clawdbot.
    """
    import re
    msg_lower = message.lower()
    
    # Check for ticker pattern (TICKER — number) - strong signal for portfolio
    ticker_pattern = r'[A-Z]{1,5}\s*[—\-:]\s*[\d,]+(?:\.\d+)?'
    has_tickers = bool(re.search(ticker_pattern, message.upper()))
    
    # Portfolio-related intents
    portfolio_keywords = ["portfolio", "holdings", "shares", "stock", "position", "investment", "holding"]
    add_keywords = ["add", "ad", "update", "set", "put", "record", "enter", "save", "store", "track"]
    
    # If message has ticker patterns, it's likely portfolio-related
    if has_tickers:
        if any(kw in msg_lower for kw in add_keywords + portfolio_keywords):
            return ("finance", "update_portfolio", message)
        # Default to update if we see tickers
        return ("finance", "update_portfolio", message)
    
    # Cash-related intents
    if "cash" in msg_lower:
        if any(kw in msg_lower for kw in ["add", "set", "update"]):
            return ("finance", "update_cash", message)
        if any(kw in msg_lower for kw in ["clear", "remove", "delete"]):
            return ("finance", "clear_cash", message)
    
    if any(kw in msg_lower for kw in portfolio_keywords):
        # Clear/delete portfolio
        if any(kw in msg_lower for kw in ["clear", "delete all", "remove all", "reset", "wipe", "empty"]):
            return ("finance", "clear_portfolio", message)
        # Remove specific ticker
        if any(kw in msg_lower for kw in ["remove", "delete", "sell"]):
            return ("finance", "remove_holding", message)
        if any(kw in msg_lower for kw in add_keywords):
            return ("finance", "update_portfolio", message)
        # Analysis actions
        if any(kw in msg_lower for kw in ["projection", "forecast", "future", "predict"]):
            return ("finance", "projections", message)
        if any(kw in msg_lower for kw in ["recommend", "suggest", "advice", "should i"]):
            return ("finance", "recommend", message)
        if any(kw in msg_lower for kw in ["rebalance", "balance", "reallocate"]):
            return ("finance", "rebalance", message)
        if any(kw in msg_lower for kw in ["analyze", "analysis", "breakdown", "examine"]):
            return ("finance", "analyze", message)
        if any(kw in msg_lower for kw in ["show", "view", "what", "check", "status", "how much", "value"]):
            return ("finance", "show_portfolio", message)
    
    # Bill-related intents
    if any(kw in msg_lower for kw in ["bill", "payment", "due", "pay"]):
        return ("finance", "bills", message)
    
    # Task/maintenance intents
    if any(kw in msg_lower for kw in ["task", "maintenance", "repair", "fix"]):
        return ("maintenance", "tasks", message)
    
    # Contractor intents
    if any(kw in msg_lower for kw in ["contractor", "juan", "plumber", "electrician"]):
        return ("contractors", "jobs", message)
    
    return (None, None, None)


async def _handle_finance_intent(action: str, message: str) -> str:
    """Handle finance agent intents using the REAL Finance Agent."""
    import re
    from sqlalchemy import text
    from ..storage.database import get_db_session
    
    # Get the real Finance Agent
    finance_agent = get_agent("finance")
    if not finance_agent:
        return "❌ Finance Agent not available"
    
    # Log that we're handling a task
    finance_agent.log_action(f"chat_intent_{action}", message[:100], "started")
    
    try:
        if action == "update_portfolio":
            # Parse holdings from message
            pattern = r'([A-Z]{1,5})\s*[—\-:]\s*([\d,]+(?:\.\d+)?)'
            matches = re.findall(pattern, message.upper())
            
            if not matches:
                finance_agent.log_action("update_portfolio", "No tickers found", "failed")
                return "❌ Couldn't parse holdings. Use format: TICKER — quantity (e.g., GOOGL — 1500.32)"
            
            db = get_db_session()
            results = []
            
            try:
                for ticker, qty in matches:
                    qty_clean = float(qty.replace(",", ""))
                    
                    existing = db.execute(
                        text("SELECT id, shares FROM portfolio_holdings WHERE ticker = :ticker AND portfolio_name = 'Lamido Main'"),
                        {"ticker": ticker}
                    ).fetchone()
                    
                    if existing:
                        db.execute(
                            text("UPDATE portfolio_holdings SET shares = :shares, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                            {"shares": qty_clean, "id": existing[0]}
                        )
                        results.append(f"✅ {ticker}: updated to {qty_clean:,.2f} shares")
                    else:
                        db.execute(
                            text("INSERT INTO portfolio_holdings (portfolio_name, ticker, shares, asset_type) VALUES ('Lamido Main', :ticker, :shares, 'stock')"),
                            {"ticker": ticker, "shares": qty_clean}
                        )
                        results.append(f"✅ {ticker}: added {qty_clean:,.2f} shares")
                
                db.commit()
                finance_agent.log_action("update_portfolio", f"Updated {len(matches)} holdings", "success")
                finance_agent.append_memory("Portfolio Updates", f"Added/updated: {', '.join([m[0] for m in matches])}")
            except Exception as e:
                finance_agent.log_action("update_portfolio", str(e), "error")
                results.append(f"❌ Error: {str(e)}")
            finally:
                db.close()
            
            response = "📊 **Finance Agent — Portfolio Update**\n\n"
            response += "\n".join(results)
            response += "\n\n💡 Finance page will update on next refresh."
            return response
        
        elif action == "show_portfolio":
            # Use the agent's portfolio methods
            try:
                portfolio_data = finance_agent._get_portfolio_data() if hasattr(finance_agent, '_get_portfolio_data') else None
                
                # Fallback to API fetch
                import subprocess
                cmd = 'cd ~/clawd/skills/stock-analysis && uv run scripts/portfolio.py show --portfolio "Lamido Main"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                
                finance_agent.log_action("show_portfolio", "Portfolio displayed", "success")
                
                if result.returncode == 0:
                    return f"📊 **Finance Agent — Portfolio**\n\n```\n{result.stdout}\n```"
                else:
                    return f"❌ Error fetching portfolio: {result.stderr}"
            except Exception as e:
                finance_agent.log_action("show_portfolio", str(e), "error")
                return f"❌ Error: {str(e)}"
        
        elif action == "bills":
            # Use the agent's bill methods
            try:
                bills = finance_agent.get_bills(include_paid=False)
                finance_agent.log_action("show_bills", f"Found {len(bills)} unpaid bills", "success")
                
                if not bills:
                    return "📋 **Finance Agent — Bills**\n\nNo unpaid bills. 🎉"
                
                response = "📋 **Finance Agent — Bills**\n\n"
                for b in bills:
                    days = b.get("days_until_due")
                    status = "🔴 OVERDUE" if days and days < 0 else "🟡 Due soon" if days and days <= 7 else "🟢"
                    response += f"{status} **{b['name']}**: ${b['amount']:.2f}"
                    if b.get('due_date'):
                        response += f" (due {b['due_date']})"
                    response += "\n"
                return response
            except Exception as e:
                finance_agent.log_action("show_bills", str(e), "error")
                return f"❌ Error fetching bills: {str(e)}"
    
        elif action == "clear_portfolio":
            db = get_db_session()
            try:
                # Count holdings
                count = db.execute(
                    text("SELECT COUNT(*) FROM portfolio_holdings WHERE portfolio_name = 'Lamido Main'")
                ).fetchone()[0]
                
                # Get cash amount
                cash_row = db.execute(text("SELECT amount FROM cash_holdings LIMIT 1")).fetchone()
                cash_amount = cash_row[0] if cash_row else 0
                
                if count == 0 and cash_amount == 0:
                    db.close()
                    return "📊 **Finance Agent — Clear Portfolio**\n\n⚠️ Portfolio is already empty."
                
                # Clear holdings
                db.execute(text("DELETE FROM portfolio_holdings WHERE portfolio_name = 'Lamido Main'"))
                # Clear cash
                db.execute(text("DELETE FROM cash_holdings"))
                db.commit()
                
                cleared_items = []
                if count > 0:
                    cleared_items.append(f"{count} holdings")
                if cash_amount > 0:
                    cleared_items.append(f"${cash_amount:,.2f} cash")
                
                finance_agent.log_action("clear_portfolio", f"Cleared {', '.join(cleared_items)}", "success")
                finance_agent.append_memory("Portfolio Updates", f"Cleared entire portfolio ({', '.join(cleared_items)})")
                
                return f"📊 **Finance Agent — Clear Portfolio**\n\n✅ Cleared {', '.join(cleared_items)} from portfolio.\n\n💡 The Finance page will update on next refresh."
            except Exception as e:
                finance_agent.log_action("clear_portfolio", str(e), "error")
                return f"❌ Error clearing portfolio: {str(e)}"
            finally:
                db.close()
        
        elif action == "remove_holding":
            ticker_match = re.search(r'\b([A-Z]{1,5})\b', message.upper())
            if not ticker_match:
                return "❌ Couldn't find ticker to remove. Try: 'remove GOOGL from portfolio'"
            
            ticker = ticker_match.group(1)
            skip_words = {"THE", "FROM", "MY", "ALL", "AND", "FOR", "REMOVE", "DELETE", "SELL"}
            if ticker in skip_words:
                all_tickers = re.findall(r'\b([A-Z]{1,5})\b', message.upper())
                valid_tickers = [t for t in all_tickers if t not in skip_words]
                if valid_tickers:
                    ticker = valid_tickers[0]
                else:
                    return "❌ Couldn't find ticker to remove. Try: 'remove GOOGL from portfolio'"
            
            db = get_db_session()
            try:
                existing = db.execute(
                    text("SELECT shares FROM portfolio_holdings WHERE ticker = :ticker AND portfolio_name = 'Lamido Main'"),
                    {"ticker": ticker}
                ).fetchone()
                
                if not existing:
                    db.close()
                    return f"📊 **Finance Agent — Remove Holding**\n\n⚠️ {ticker} not found in portfolio."
                
                shares = existing[0]
                db.execute(
                    text("DELETE FROM portfolio_holdings WHERE ticker = :ticker AND portfolio_name = 'Lamido Main'"),
                    {"ticker": ticker}
                )
                db.commit()
                
                finance_agent.log_action("remove_holding", f"Removed {ticker} ({shares} shares)", "success")
                finance_agent.append_memory("Portfolio Updates", f"Removed {ticker} ({shares:,.2f} shares)")
                
                return f"📊 **Finance Agent — Remove Holding**\n\n✅ Removed {ticker} ({shares:,.2f} shares) from portfolio.\n\n💡 The Finance page will update on next refresh."
            except Exception as e:
                finance_agent.log_action("remove_holding", str(e), "error")
                return f"❌ Error removing holding: {str(e)}"
            finally:
                db.close()
        
        elif action == "update_cash":
            # Parse cash amount from message
            amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', message)
            if not amount_match:
                return "❌ Couldn't parse cash amount. Try: 'set cash to $25,000' or 'add cash 25000'"
            
            amount = float(amount_match.group(1).replace(",", ""))
            
            db = get_db_session()
            try:
                # Update or insert cash
                existing = db.execute(text("SELECT id FROM cash_holdings LIMIT 1")).fetchone()
                if existing:
                    db.execute(
                        text("UPDATE cash_holdings SET amount = :amount, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                        {"amount": amount, "id": existing[0]}
                    )
                else:
                    db.execute(
                        text("INSERT INTO cash_holdings (account_name, institution, amount) VALUES ('Checking', 'JPMorgan Chase', :amount)"),
                        {"amount": amount}
                    )
                db.commit()
                
                finance_agent.log_action("update_cash", f"Set cash to ${amount:,.2f}", "success")
                return f"📊 **Finance Agent — Update Cash**\n\n✅ Cash set to ${amount:,.2f}\n\n💡 Finance page will update on next refresh."
            except Exception as e:
                finance_agent.log_action("update_cash", str(e), "error")
                return f"❌ Error updating cash: {str(e)}"
            finally:
                db.close()
        
        elif action == "clear_cash":
            db = get_db_session()
            try:
                db.execute(text("DELETE FROM cash_holdings"))
                db.commit()
                finance_agent.log_action("clear_cash", "Cleared cash", "success")
                return "📊 **Finance Agent — Clear Cash**\n\n✅ Cash cleared.\n\n💡 Finance page will update on next refresh."
            except Exception as e:
                finance_agent.log_action("clear_cash", str(e), "error")
                return f"❌ Error clearing cash: {str(e)}"
            finally:
                db.close()
        
        elif action in ["projections", "recommend", "rebalance", "analyze"]:
            # These need AI analysis - route to Clawdbot
            from ..core.clawdbot_runner import run_clawdbot_message
            
            holdings = finance_agent.get_holdings_from_db()
            
            if not holdings:
                return f"📊 **Finance Agent**\n\n⚠️ No holdings in portfolio. Add some positions first!"
            
            holdings_text = "\n".join([f"- {h['ticker']}: {h['shares']:,.2f} shares ({h.get('type', 'stock')})" for h in holdings])
            
            prompts = {
                "projections": f"Project the growth of this portfolio over the next year. Give realistic scenarios (bull/bear/base):\n\nHoldings:\n{holdings_text}",
                "recommend": f"Analyze this portfolio and give specific buy/sell/hold recommendations for each position:\n\nHoldings:\n{holdings_text}",
                "rebalance": f"Suggest how to rebalance this portfolio. Consider sector exposure, concentration risk, and correlation:\n\nHoldings:\n{holdings_text}",
                "analyze": f"Provide detailed analysis of each position in this portfolio. Include recent performance, outlook, and risks:\n\nHoldings:\n{holdings_text}",
            }
            
            prompt = prompts.get(action, message)
            
            try:
                finance_agent.log_action(action, f"Sending to AI: {len(holdings)} holdings", "started")
                response = await run_clawdbot_message(prompt, session_id="mycasa_finance")
                finance_agent.log_action(action, "AI response received", "success")
                return response or "No response from AI"
            except Exception as e:
                finance_agent.log_action(action, str(e), "error")
                return f"❌ Error: {str(e)}"
        
        return "❌ Unknown finance action"
        
    except Exception as e:
        if finance_agent:
            finance_agent.log_action(f"intent_{action}", str(e), "error")
        return f"❌ Finance Agent error: {str(e)}"


async def _handle_maintenance_intent(action: str, message: str) -> str:
    """Handle maintenance agent intents using REAL Maintenance Agent."""
    from ..storage.database import get_db_session
    from ..storage.models import TaskDB
    
    # Get the real Maintenance Agent
    maintenance_agent = get_agent("maintenance")
    if not maintenance_agent:
        return "❌ Maintenance Agent not available"
    
    maintenance_agent.log_action(f"chat_intent_{action}", message[:100], "started")
    
    try:
        db = get_db_session()
        
        if action == "tasks":
            # Check if adding or viewing
            add_keywords = ["add", "create", "schedule", "need to", "fix", "repair"]
            msg_lower = message.lower()
            
            if any(kw in msg_lower for kw in add_keywords):
                # Extract task description (basic parsing)
                task_text = message
                for kw in ["add task", "create task", "add a task", "need to"]:
                    if kw in msg_lower:
                        idx = msg_lower.find(kw) + len(kw)
                        task_text = message[idx:].strip()
                        break
                
                # Create the task
                new_task = TaskDB(
                    title=task_text[:100],  # Truncate if too long
                    description=task_text,
                    status="pending",
                    priority="medium",
                    category="maintenance"
                )
                db.add(new_task)
                db.commit()
                
                response = f"🔧 **Maintenance Agent — Task Created**\n\n"
                response += f"✅ Created: {task_text[:100]}\n"
                response += f"📋 Status: Pending\n"
                response += f"🔢 ID: {new_task.id}"
                db.close()
                return response
            
            # Show tasks
            tasks = db.query(TaskDB).filter(
                TaskDB.status.in_(["pending", "in_progress"])
            ).order_by(TaskDB.created_at.desc()).limit(10).all()
            db.close()
            
            if not tasks:
                return "🔧 **Maintenance Agent — Tasks**\n\nNo open tasks. House is looking good! 🏠"
            
            response = "🔧 **Maintenance Agent — Tasks**\n\n"
            for t in tasks:
                status_emoji = "⏳" if t.status == "pending" else "🔄"
                response += f"{status_emoji} **{t.title}**\n"
                if t.description and t.description != t.title:
                    response += f"   {t.description[:50]}...\n" if len(t.description) > 50 else f"   {t.description}\n"
            return response
            
    except Exception as e:
        return f"❌ Maintenance error: {str(e)}"
    
    return "🔧 **Maintenance Agent**\n\nI can help with tasks and repairs. Try:\n• Show tasks\n• Add task: fix the leaky faucet"


async def _handle_contractors_intent(action: str, message: str) -> str:
    """Handle contractors agent intents."""
    from ..storage.database import get_db_session
    from ..storage.models import ContractorDB, ContractorJobDB
    
    try:
        db = get_db_session()
        
        if action == "jobs":
            # Show contractor jobs
            jobs = db.query(ContractorJobDB).filter(
                ContractorJobDB.status.in_(["pending", "scheduled", "in_progress"])
            ).order_by(ContractorJobDB.created_at.desc()).limit(10).all()
            
            contractors = {c.id: c for c in db.query(ContractorDB).all()}
            db.close()
            
            if not jobs:
                return "👷 **Contractors Agent — Jobs**\n\nNo active contractor jobs."
            
            response = "👷 **Contractors Agent — Jobs**\n\n"
            for j in jobs:
                contractor = contractors.get(j.contractor_id)
                contractor_name = contractor.name if contractor else "Unknown"
                status_emoji = {"pending": "⏳", "scheduled": "📅", "in_progress": "🔨"}.get(j.status, "❓")
                response += f"{status_emoji} **{j.description[:50]}**\n"
                response += f"   Contractor: {contractor_name}\n"
            return response
            
    except Exception as e:
        return f"❌ Contractors error: {str(e)}"
    
    return "👷 **Contractors Agent**\n\nI manage contractor relationships. Try:\n• Show jobs\n• Check on Juan"


# ============ COMMAND HANDLERS (CRUD with DB sync) ============

async def _handle_maintenance_command(cmd: str, message: str) -> str:
    """Handle maintenance commands with database sync."""
    from ..storage.database import get_db_session
    from ..storage.models import TaskDB
    from datetime import datetime
    
    parts = cmd.split(maxsplit=1)
    cmd_base = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    db = get_db_session()
    
    try:
        if cmd_base == "tasks":
            tasks = db.query(TaskDB).filter(
                TaskDB.status.in_(["pending", "in_progress"])
            ).order_by(TaskDB.priority.desc(), TaskDB.created_at.desc()).limit(15).all()
            
            if not tasks:
                return "🔧 **Tasks**\n\n✨ No open tasks. House is looking good!"
            
            response = "🔧 **Maintenance Tasks**\n\n"
            for t in tasks:
                status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(t.status, "❓")
                priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(t.priority, "⚪")
                response += f"{status_emoji} **[{t.id}]** {t.title}\n"
                response += f"   {priority_emoji} {t.priority} • {t.category or 'general'}\n"
            response += "\n💡 Use `/addtask TITLE` to create, `/completetask ID` to complete"
            return response
        
        elif cmd_base == "addtask":
            if not args:
                return "❌ Usage: `/addtask Task title here`"
            
            # Parse priority if specified (e.g., "fix leak !high")
            priority = "medium"
            title = args
            for p in ["!urgent", "!high", "!medium", "!low"]:
                if p in args.lower():
                    priority = p[1:]
                    title = args.lower().replace(p, "").strip()
                    break
            
            new_task = TaskDB(
                title=title[:200],
                description=title,
                status="pending",
                priority=priority,
                category="maintenance",
                created_at=datetime.utcnow()
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            
            return f"✅ **Task Created**\n\n📋 **{new_task.title}**\n🆔 ID: {new_task.id}\n📊 Priority: {priority}\n\n💡 View on Maintenance page or use `/tasks`"
        
        elif cmd_base == "completetask":
            if not args or not args.isdigit():
                return "❌ Usage: `/completetask ID` (e.g., `/completetask 5`)"
            
            task_id = int(args)
            task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
            
            if not task:
                return f"❌ Task #{task_id} not found"
            
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            db.commit()
            
            return f"✅ **Task Completed**\n\n📋 ~~{task.title}~~\n🆔 ID: {task.id}\n\n🎉 Nice work!"
        
        elif cmd_base == "deletetask":
            if not args or not args.isdigit():
                return "❌ Usage: `/deletetask ID`"
            
            task_id = int(args)
            task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
            
            if not task:
                return f"❌ Task #{task_id} not found"
            
            title = task.title
            db.delete(task)
            db.commit()
            
            return f"🗑️ **Task Deleted**\n\n📋 {title}"
        
        elif cmd_base == "overdue":
            from datetime import date
            tasks = db.query(TaskDB).filter(
                TaskDB.status.in_(["pending", "in_progress"]),
                TaskDB.due_date < date.today()
            ).all()
            
            if not tasks:
                return "🔧 **Overdue Tasks**\n\n✨ Nothing overdue!"
            
            response = "🔧 **Overdue Tasks**\n\n"
            for t in tasks:
                days = (date.today() - t.due_date).days
                response += f"🔴 **[{t.id}]** {t.title} ({days}d overdue)\n"
            return response
        
        elif cmd_base == "schedule":
            from datetime import date, timedelta
            next_week = date.today() + timedelta(days=7)
            tasks = db.query(TaskDB).filter(
                TaskDB.status == "pending",
                TaskDB.due_date <= next_week
            ).order_by(TaskDB.due_date).all()
            
            if not tasks:
                return "🔧 **Upcoming Schedule**\n\n📅 Nothing scheduled this week"
            
            response = "🔧 **Maintenance Schedule (7 days)**\n\n"
            for t in tasks:
                response += f"📅 **{t.due_date}** — {t.title}\n"
            return response
        
        return "🔧 Unknown maintenance command. Try `/help`"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        db.close()


async def _handle_finance_command(cmd: str, message: str) -> str:
    """Handle finance CRUD commands with database sync."""
    from ..storage.database import get_db_session
    from agents.finance import FinanceAgent
    from datetime import date
    
    parts = cmd.split(maxsplit=2)
    cmd_base = parts[0].lower()
    
    finance = FinanceAgent()
    db = get_db_session()
    
    try:
        if cmd_base == "addholding":
            # /addholding TICKER SHARES [TYPE]
            if len(parts) < 3:
                return "❌ Usage: `/addholding TICKER SHARES [TYPE]`\nExample: `/addholding AAPL 100 Tech`"
            
            ticker = parts[1].upper()
            try:
                shares = float(parts[2].split()[0].replace(",", ""))
            except Exception:
                return "❌ Invalid shares number"
            
            asset_type = parts[2].split()[1] if len(parts[2].split()) > 1 else "stock"
            
            result = finance.add_holding(ticker, shares, asset_type)
            
            action = "Updated" if result.get("action") == "updated" else "Added"
            return f"✅ **{action} Holding**\n\n📈 **{ticker}**: {shares:,.2f} shares\n📁 Type: {asset_type}\n\n💡 Portfolio page will refresh automatically"
        
        elif cmd_base == "removeholding":
            if len(parts) < 2:
                return "❌ Usage: `/removeholding TICKER`"
            
            ticker = parts[1].upper()
            result = finance.remove_holding(ticker)
            
            if not result.get("success"):
                return f"❌ {result.get('error', 'Failed to remove')}"
            
            return f"🗑️ **Removed Holding**\n\n📉 {ticker} removed from portfolio"
        
        elif cmd_base == "clearportfolio":
            result = finance.clear_portfolio()
            return f"🗑️ **Portfolio Cleared**\n\n{result.get('message', 'Done')}"
        
        elif cmd_base == "addbill":
            # /addbill NAME AMOUNT [DUE_DATE]
            if len(parts) < 2:
                return "❌ Usage: `/addbill NAME AMOUNT`\nExample: `/addbill Electric 150`"
            
            # Parse: "Electric 150" or "Electric Bill 150"
            args = parts[1] if len(parts) > 1 else ""
            words = args.split()
            
            # Find the amount (last number in the string)
            amount = None
            name_parts = []
            for i, w in enumerate(words):
                try:
                    amount = float(w.replace("$", "").replace(",", ""))
                    name_parts = words[:i]
                    break
                except Exception:
                    name_parts.append(w)
            
            if not amount or not name_parts:
                return "❌ Usage: `/addbill NAME AMOUNT`\nExample: `/addbill Electric 150`"
            
            name = " ".join(name_parts)
            due_date = date.today().replace(day=28)  # Default to 28th
            
            from database.models import Bill
            from database import get_db
            with get_db() as bill_db:
                bill = Bill(
                    name=name,
                    amount=amount,
                    due_date=due_date,
                    category="general",
                    is_recurring=False
                )
                bill_db.add(bill)
                bill_db.commit()
                bill_db.refresh(bill)
                bill_id = bill.id
            
            return f"✅ **Bill Added**\n\n💳 **{name}**: ${amount:,.2f}\n📅 Due: {due_date}\n🆔 ID: {bill_id}\n\n💡 View on Finance page"
        
        elif cmd_base == "paybill":
            if len(parts) < 2 or not parts[1].isdigit():
                return "❌ Usage: `/paybill ID`"
            
            bill_id = int(parts[1])
            result = finance.pay_bill(bill_id)
            
            if not result.get("success"):
                return f"❌ {result.get('error', 'Failed to pay bill')}"
            
            bill = result.get("bill", {})
            return f"✅ **Bill Paid**\n\n💳 ~~{bill.get('name', 'Bill')}~~: ${bill.get('amount', 0):,.2f}\n\n🎉 One less thing to worry about!"
        
        return "💰 Unknown finance command. Try `/help`"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        db.close()


async def _handle_manager_command(cmd: str, message: str) -> str:
    """Handle manager/system commands."""
    from agents.manager import ManagerAgent
    from ..storage.database import get_db_session
    from ..storage.models import TaskDB
    
    parts = cmd.split()
    cmd_base = parts[0].lower()
    
    try:
        manager = ManagerAgent()
        
        if cmd_base == "status":
            status = manager.quick_status()
            facts = status.get("facts", {})
            tasks = facts.get("tasks", {})
            agents = facts.get("agents", {})
            
            response = "🏠 **MyCasa Status**\n\n"
            
            # Agents
            response += "**Agents**\n"
            for agent_name, agent_status in agents.items():
                emoji = "🟢" if agent_status == "active" else "🔴"
                response += f"{emoji} {agent_name.title()}\n"
            
            # Tasks
            response += f"\n**Tasks**\n"
            response += f"📋 Pending: {tasks.get('pending', 0)}\n"
            response += f"⚠️ Overdue: {tasks.get('overdue', 0)}\n"
            
            # Alerts
            alerts = facts.get("alerts", [])
            if alerts:
                response += f"\n**Alerts ({len(alerts)})**\n"
                for a in alerts[:3]:
                    response += f"⚠️ {a.get('title', 'Alert')}\n"
            
            return response
        
        elif cmd_base == "summary":
            # Daily summary
            from agents.finance import FinanceAgent
            finance = FinanceAgent()
            
            holdings = finance.get_holdings_from_db()
            bills = finance.get_upcoming_bills(7)
            
            db = get_db_session()
            pending_tasks = db.query(TaskDB).filter(TaskDB.status == "pending").count()
            db.close()
            
            response = "📊 **Daily Summary**\n\n"
            response += f"**Portfolio**: {len(holdings)} positions\n"
            response += f"**Bills Due (7d)**: {len(bills)}\n"
            response += f"**Pending Tasks**: {pending_tasks}\n"
            
            if bills:
                total_due = sum(b.get("amount", 0) for b in bills)
                response += f"\n💳 ${total_due:,.0f} due this week"
            
            return response
        
        elif cmd_base == "alerts":
            status = manager.quick_status()
            alerts = status.get("facts", {}).get("alerts", [])
            
            if not alerts:
                return "🔔 **Alerts**\n\n✨ No active alerts!"
            
            response = "🔔 **Active Alerts**\n\n"
            for a in alerts:
                severity = a.get("severity", "medium")
                emoji = "🔴" if severity in ["high", "urgent"] else "🟡"
                response += f"{emoji} **{a.get('title', 'Alert')}**\n"
                if a.get("message"):
                    response += f"   {a['message']}\n"
            
            return response
        
        elif cmd_base == "agents":
            status = manager.quick_status()
            agents = status.get("facts", {}).get("agents", {})
            
            response = "🤖 **Agent Status**\n\n"
            for name, state in agents.items():
                emoji = "🟢" if state == "active" else "⚪" if state == "idle" else "🔴"
                response += f"{emoji} **{name.title()}** — {state}\n"
            
            return response
        
        return "🏠 Unknown manager command. Try `/help`"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def _handle_contractors_command(cmd: str, message: str) -> str:
    """Handle contractors commands with database sync."""
    from ..storage.database import get_db_session
    from ..storage.models import ContractorDB, ContractorJobDB
    from datetime import datetime
    
    parts = cmd.split(maxsplit=1)
    cmd_base = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    db = get_db_session()
    
    try:
        if cmd_base == "contractors":
            contractors = db.query(ContractorDB).limit(20).all()
            
            if not contractors:
                return "👷 **Contractors**\n\n📭 No contractors yet. Add some on the Contractors page."
            
            response = "👷 **Contractors**\n\n"
            for c in contractors:
                rating = "⭐" * (c.rating or 0) if c.rating else "No rating"
                response += f"**{c.name}**\n"
                response += f"   📞 {c.phone or 'No phone'} • {c.specialty or 'General'}\n"
            
            return response
        
        elif cmd_base == "addjob":
            if not args:
                return "❌ Usage: `/addjob Job description here`"
            
            job = ContractorJobDB(
                description=args[:500],
                status="pending",
                created_at=datetime.utcnow()
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            return f"✅ **Job Created**\n\n📝 {args[:100]}...\n🆔 ID: {job.id}\nStatus: Pending\n\n💡 Assign a contractor on the Contractors page"
        
        elif cmd_base in ["hire", "reviews"]:
            return "👷 **Find Contractors**\n\nVisit the Contractors page to search and hire.\n\n💡 Or try `/contractors` to see your existing contacts."
        
        return "👷 Unknown contractor command. Try `/help`"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        db.close()


@app.post("/manager/chat", tags=["Manager"])
async def send_to_manager(request: dict):
    """
    Send a message to Manager with FULL CLAWDBOT POWER + Smart Agent Routing.
    
    The Manager detects intent and routes to appropriate agents:
    - @AgentName mentions route directly to that agent
    - Finance Agent: portfolio, bills, spending
    - Maintenance Agent: tasks, repairs
    - Contractors Agent: jobs, contractors
    - Raw "/" commands go directly to Clawdbot CLI
    - Everything else goes to Clawdbot agent
    """
    import re
    from ..core.clawdbot_runner import run_clawdbot_message, run_clawdbot_command
    
    message = request.get("message", "").strip()
    thinking = request.get("thinking", "low")
    target_agent = request.get("target_agent")  # Optional explicit agent target

    if not message:
        return {"response": "No message provided", "success": False}

    try:
        # ============ PARSE @MENTIONS ============
        # Handle @AgentName mentions - route directly to that agent
        agent_map = {
            "mamadou": ("finance", "Mamadou", "💰"),
            "ousmane": ("maintenance", "Ousmane", "🔧"),
            "aïcha": ("security", "Aïcha", "🛡️"),
            "aicha": ("security", "Aïcha", "🛡️"),
            "malik": ("contractors", "Malik", "👷"),
            "zainab": ("projects", "Zainab", "🏗️"),
            "salimata": ("janitor", "Salimata", "✨"),
            "galidima": ("manager", "Galidima", "🏠"),
        }
        
        # Check for @mention at start of message
        mention_match = re.match(r'^@(\w+)\s*(.*)', message, re.IGNORECASE)
        if mention_match:
            mentioned_name = mention_match.group(1).lower()
            remaining_message = mention_match.group(2).strip() or "hi"
            
            if mentioned_name in agent_map:
                agent_id, agent_name, agent_emoji = agent_map[mentioned_name]
                
                # Get the agent and call its chat method directly
                agent = get_agent(agent_id)
                if agent:
                    response = await agent.chat(remaining_message)
                    return {
                        "response": response,
                        "success": True,
                        "is_command": False,
                        "routed_to": f"{agent_id}_agent",
                        "agent_name": agent_name,
                        "agent_emoji": agent_emoji
                    }
        
        # Also handle explicit target_agent from frontend
        if target_agent and target_agent in ["finance", "maintenance", "security", "contractors", "projects", "janitor"]:
            agent = get_agent(target_agent)
            if agent:
                response = await agent.chat(message)
                names = {"finance": "Mamadou", "maintenance": "Ousmane", "security": "Aïcha", 
                         "contractors": "Malik", "projects": "Zainab", "janitor": "Salimata"}
                emojis = {"finance": "💰", "maintenance": "🔧", "security": "🛡️",
                          "contractors": "👷", "projects": "🏗️", "janitor": "✨"}
                return {
                    "response": response,
                    "success": True,
                    "is_command": False,
                    "routed_to": f"{target_agent}_agent",
                    "agent_name": names.get(target_agent, target_agent),
                    "agent_emoji": emojis.get(target_agent, "🤖")
                }
        
        # Handle "/" commands — route to agents first, fallback to Clawdbot CLI
        if message.startswith("/"):
            cmd = message[1:].strip().lower()
            
            if not cmd:
                return {"response": "Empty command. Try /status or /help", "success": False}
            
            # Finance Agent commands - route to actual AI
            finance_ai_commands = ["analyze", "recommend", "project", "projections", "rebalance", "sectors"]
            finance_data_commands = ["portfolio", "bills", "budget", "spending"]
            
            cmd_base = cmd.split()[0]  # Get first word
            
            # Commands that need AI analysis
            if cmd_base in finance_ai_commands:
                # Build context with portfolio data for the AI
                from agents.finance import FinanceAgent
                finance = FinanceAgent()
                holdings = finance.get_holdings_from_db()
                
                holdings_text = "\n".join([f"- {h['ticker']}: {h['shares']:,.2f} shares ({h.get('type', 'stock')})" for h in holdings])
                
                # Create prompt for AI with context
                ai_prompts = {
                    "analyze": f"Analyze my portfolio positions and provide insights:\n\nHoldings:\n{holdings_text}\n\nProvide analysis on each position.",
                    "recommend": f"Based on my current portfolio, what changes would you recommend?\n\nHoldings:\n{holdings_text}\n\nGive specific buy/sell/hold recommendations.",
                    "project": f"Project the growth of my portfolio over the next year:\n\nHoldings:\n{holdings_text}\n\nProvide projections and scenarios.",
                    "projections": f"Project the growth of my portfolio over the next year:\n\nHoldings:\n{holdings_text}\n\nProvide projections and scenarios.",
                    "rebalance": f"Suggest how I should rebalance my portfolio:\n\nHoldings:\n{holdings_text}\n\nProvide specific rebalancing recommendations.",
                    "sectors": f"Analyze the sector exposure of my portfolio:\n\nHoldings:\n{holdings_text}\n\nBreak down by sector and identify risks.",
                }
                
                prompt = ai_prompts.get(cmd_base, f"Help with: {message}")
                
                # Send to Clawdbot AI
                response = await run_clawdbot_message(prompt, session_id="mycasa_finance")
                
                return {
                    "response": response or "No response from AI",
                    "success": True,
                    "is_command": True,
                    "routed_to": "clawdbot_ai",
                    "agent_name": "Finance Agent (AI)",
                    "agent_emoji": "💰"
                }
            
            # Commands that just need data (no AI)
            if cmd_base in finance_data_commands:
                action_map = {"portfolio": "show_portfolio", "bills": "bills", "budget": "bills", "spending": "bills"}
                response = await _handle_finance_intent(action_map.get(cmd_base, "show_portfolio"), message)
                return {
                    "response": response,
                    "success": True,
                    "is_command": True,
                    "routed_to": "finance_agent",
                    "agent_name": "Finance Agent",
                    "agent_emoji": "💰"
                }
            
            # ============ MAINTENANCE COMMANDS (CRUD) ============
            if cmd_base in ["tasks", "addtask", "completetask", "deletetask", "overdue", "schedule"]:
                response = await _handle_maintenance_command(cmd, message)
                return {
                    "response": response,
                    "success": True,
                    "is_command": True,
                    "routed_to": "maintenance_agent",
                    "agent_name": "Maintenance Agent",
                    "agent_emoji": "🔧"
                }
            
            # ============ FINANCE CRUD COMMANDS ============
            if cmd_base in ["addholding", "removeholding", "clearportfolio", "addbill", "paybill"]:
                response = await _handle_finance_command(cmd, message)
                return {
                    "response": response,
                    "success": True,
                    "is_command": True,
                    "routed_to": "finance_agent",
                    "agent_name": "Finance Agent",
                    "agent_emoji": "💰"
                }
            
            # ============ MANAGER COMMANDS ============
            if cmd_base in ["status", "summary", "alerts", "agents"]:
                response = await _handle_manager_command(cmd, message)
                return {
                    "response": response,
                    "success": True,
                    "is_command": True,
                    "routed_to": "manager",
                    "agent_name": "Manager",
                    "agent_emoji": "🏠"
                }
            
            # Contractors commands
            if cmd_base in ["contractors", "hire", "reviews", "addjob"]:
                response = await _handle_contractors_command(cmd, message)
                return {
                    "response": response,
                    "success": True,
                    "is_command": True,
                    "routed_to": "contractors_agent",
                    "agent_name": "Contractors Agent",
                    "agent_emoji": "👷"
                }
            
            # Help command
            if cmd_base == "help":
                help_text = """📚 **MyCasa Commands**

**🏠 Manager**
• `/status` — System overview
• `/summary` — Daily summary
• `/alerts` — Active alerts
• `/agents` — Agent status

**💰 Finance**
• `/portfolio` — View holdings
• `/addholding TICKER SHARES` — Add position
• `/removeholding TICKER` — Remove position
• `/clearportfolio` — Clear all holdings
• `/bills` — View bills
• `/addbill NAME AMOUNT` — Add bill
• `/paybill ID` — Mark bill paid
• `/analyze` — AI portfolio analysis
• `/recommend` — AI recommendations
• `/rebalance` — AI rebalancing tips

**🔧 Maintenance**
• `/tasks` — View all tasks
• `/addtask TITLE` — Create task
• `/completetask ID` — Complete task
• `/deletetask ID` — Delete task
• `/overdue` — Overdue items

**👷 Contractors**
• `/contractors` — List contractors
• `/addjob DESCRIPTION` — Create job

💡 Changes sync to UI automatically."""
                return {"response": help_text, "success": True, "is_command": True, "routed_to": "system"}
            
            # Fallback to Clawdbot CLI for unknown commands
            result = await run_clawdbot_command(cmd, session_id="mycasa_manager")
            
            output = result.get("stdout", "")
            if result.get("stderr"):
                output += f"\n[stderr] {result['stderr']}"
            if result.get("error"):
                output += f"\n[error] {result['error']}"
            
            return {
                "response": output or "(no output)",
                "success": result.get("success", False),
                "is_command": True,
                "exit_code": result.get("exit_code", 0),
                "routed_to": "clawdbot_cli"
            }
        
        # Detect intent and route to appropriate agent
        agent, action, _ = _detect_intent(message)
        
        if agent == "finance":
            response = await _handle_finance_intent(action, message)
            return {
                "response": response,
                "success": True,
                "is_command": False,
                "routed_to": "finance_agent",
                "agent_name": "Finance Agent",
                "agent_emoji": "💰"
            }
        
        if agent == "maintenance":
            response = await _handle_maintenance_intent(action, message)
            return {
                "response": response,
                "success": True,
                "is_command": False,
                "routed_to": "maintenance_agent",
                "agent_name": "Maintenance Agent",
                "agent_emoji": "🔧"
            }
        
        if agent == "contractors":
            response = await _handle_contractors_intent(action, message)
            return {
                "response": response,
                "success": True,
                "is_command": False,
                "routed_to": "contractors_agent",
                "agent_name": "Contractors Agent",
                "agent_emoji": "👷"
            }
        
        # Default: send to Clawdbot agent for general tasks
        response = await run_clawdbot_message(
            message, 
            session_id="mycasa_manager",
            thinking_level=thinking
        )
        
        return {
            "response": response or "(no response)",
            "success": True,
            "is_command": False,
            "routed_to": "clawdbot_agent"
        }
    
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "success": False,
            "error": str(e)
        }


@app.websocket("/manager/ws")
async def manager_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for streaming Manager chat.
    
    Full terminal power with real-time streaming.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    _ws_connections[connection_id] = websocket
    
    runner = get_runner()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            
            if msg_type == "message":
                message = data.get("message", "")
                thinking = data.get("thinking", "low")
                
                if not message.strip():
                    await websocket.send_json({
                        "type": "error",
                        "error": "Empty message"
                    })
                    continue
                
                # Check if raw command
                if message.startswith("/"):
                    cmd = message[1:].strip()
                    context = ExecutionContext(session_id="mycasa_manager")
                    
                    async for event in runner.run_raw(cmd, context):
                        await websocket.send_json({
                            "type": "event",
                            **event.to_dict()
                        })
                else:
                    # Regular message to agent
                    context = ExecutionContext(
                        session_id="mycasa_manager",
                        thinking_level=thinking
                    )
                    
                    async for event in runner.run_message(message, context):
                        await websocket.send_json({
                            "type": "event",
                            **event.to_dict()
                        })
            
            elif msg_type == "cancel":
                command_id = data.get("command_id")
                if command_id:
                    cancelled = await runner.cancel(command_id)
                    await websocket.send_json({
                        "type": "cancelled",
                        "command_id": command_id,
                        "success": cancelled
                    })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        if connection_id in _ws_connections:
            del _ws_connections[connection_id]


@app.get("/manager/commands", tags=["Manager"])
async def list_manager_commands():
    """
    List available commands for Manager chat.
    
    Manager has FULL access to all Clawdbot commands.
    """
    return {
        "info": "Manager has full Clawdbot CLI power. Prefix with / for raw commands.",
        "examples": [
            {"input": "Check my inbox", "desc": "Natural language request"},
            {"input": "What's the weather?", "desc": "Ask anything"},
            {"input": "Send WhatsApp to Erika saying hi", "desc": "Send messages"},
            {"input": "/status", "desc": "Run clawdbot status"},
            {"input": "/sessions", "desc": "List sessions"},
            {"input": "/health", "desc": "Gateway health"},
            {"input": "/cron list", "desc": "List cron jobs"},
            {"input": "/skills list", "desc": "List skills"},
            {"input": "/browser tabs", "desc": "List browser tabs"},
            {"input": "/message send --to '+1234' --message 'hi'", "desc": "Raw message"},
        ],
        "capabilities": [
            "✅ Full agent conversation",
            "✅ All CLI commands via / prefix",
            "✅ Browser control",
            "✅ Message sending",
            "✅ Cron management",
            "✅ Memory access",
            "✅ File operations",
            "✅ Web search",
            "✅ All tools available"
        ]
    }


@app.get("/manager/status", tags=["Manager"])
async def get_manager_status():
    """Get Manager execution status"""
    runner = get_runner()
    status = await runner.get_status()
    
    return {
        **status,
        "ws_connections": len(_ws_connections),
        "pending_messages": len(_manager_messages)
    }


# ============ WHATSAPP WHITELIST ============

@app.get("/contacts/whitelist", tags=["Contacts"])
async def get_whatsapp_whitelist():
    """Get WhatsApp whitelisted contacts"""
    from core.settings_typed import get_settings_store
    settings = get_settings_store().get()
    contacts = []
    for contact in getattr(settings.agents.mail, "whatsapp_contacts", []) or []:
        try:
            name = getattr(contact, "name", "") or ""
            phone = getattr(contact, "phone", "") or ""
        except Exception:
            name = (contact or {}).get("name") or ""
            phone = (contact or {}).get("phone") or ""
        if phone:
            contacts.append({"phone": phone, "name": name})
    return {"contacts": contacts}


@app.post("/contacts/whitelist", response_model=APIResponse, tags=["Contacts"])
async def add_to_whitelist(phone: str, name: str):
    """Add a contact to WhatsApp whitelist"""
    from core.settings_typed import get_settings_store
    
    correlation_id = generate_correlation_id()
    store = get_settings_store()
    settings = store.get()
    phone_clean = ''.join(c for c in phone if c.isdigit())
    if phone_clean:
        contacts = list(getattr(settings.agents.mail, "whatsapp_contacts", []) or [])
        contacts.append({"name": name or "", "phone": phone_clean})
        settings.agents.mail.whatsapp_contacts = contacts
        allowlist = set(getattr(settings.agents.mail, "whatsapp_allowlist", []) or [])
        allowlist.add(phone_clean)
        settings.agents.mail.whatsapp_allowlist = sorted(allowlist)
        store.save(settings)
    
    return APIResponse(
        status="success",
        correlation_id=correlation_id,
        data={"phone": phone, "name": name, "message": f"Added {name} to whitelist"}
    )


@app.delete("/contacts/whitelist/{phone}", response_model=APIResponse, tags=["Contacts"])
async def remove_from_whitelist(phone: str):
    """Remove a contact from WhatsApp whitelist"""
    from core.settings_typed import get_settings_store
    
    correlation_id = generate_correlation_id()
    phone_clean = ''.join(c for c in phone if c.isdigit())
    store = get_settings_store()
    settings = store.get()
    contacts = list(getattr(settings.agents.mail, "whatsapp_contacts", []) or [])
    remaining = [c for c in contacts if (getattr(c, "phone", None) or (c or {}).get("phone")) != phone_clean]
    if len(remaining) != len(contacts):
        settings.agents.mail.whatsapp_contacts = remaining
    allowlist = set(getattr(settings.agents.mail, "whatsapp_allowlist", []) or [])
    if phone_clean in allowlist:
        allowlist.discard(phone_clean)
        settings.agents.mail.whatsapp_allowlist = sorted(allowlist)
        store.save(settings)
        return APIResponse(
            status="success",
            correlation_id=correlation_id,
            data={"phone": phone_clean, "message": "Removed from whitelist"}
        )
    return APIResponse(
        status="error",
        correlation_id=correlation_id,
        errors=["Contact not found in whitelist"]
    )


# Run with: uvicorn backend.api.main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

@app.get("/debug/agent-test", tags=["Debug"])
async def debug_agent_test():
    """Debug endpoint to test agent loading"""
    agent = get_agent("finance")
    if not agent:
        return {"error": "Agent not loaded"}
    
    try:
        status = agent.get_status()
        logs = agent.get_recent_logs(5)
        return {
            "status": status,
            "logs": logs,
            "logs_count": len(logs),
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/monitor-test", tags=["Debug"])
async def debug_monitor_test():
    """Debug - call get_system_monitor and check output"""
    result = await get_system_monitor()
    first_proc = result.get("processes", [{}])[0]
    return {
        "first_proc_keys": list(first_proc.keys()),
        "has_recent_logs": "recent_logs" in first_proc,
        "recent_logs_count": len(first_proc.get("recent_logs", [])),
    }

@app.get("/debug/monitor-detailed", tags=["Debug"])
async def debug_monitor_detailed():
    """Debug - show what's happening with agents"""
    results = []
    agent_names = ["finance", "maintenance"]
    
    for name in agent_names:
        agent = get_agent(name)
        result = {"name": name, "agent_loaded": agent is not None}
        
        if agent:
            try:
                status = agent.get_status()
                logs = agent.get_recent_logs(5)
                result["status_ok"] = True
                result["status_state"] = status.get("status")
                result["logs_count"] = len(logs)
                result["first_log"] = logs[0] if logs else None
            except Exception as e:
                result["status_ok"] = False
                result["error"] = str(e)
        
        results.append(result)
    
    return {"agents": results}
