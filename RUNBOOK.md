# MyCasa Pro Runbook

## Quick Start

### One Command Boot (macOS)

```bash
# Start everything
cd /path/to/mycasa-pro && ./start_all.sh

# Or start individually:
mycasa backend start
mycasa ui start
```

### One Command Boot (Windows)

```powershell
# Start backend
cd C:\path\to\mycasa-pro
python -m uvicorn api.main:app --host 127.0.0.1 --port 6709 --reload

# In another terminal, start frontend
cd C:\path\to\mycasa-pro\frontend
npm run dev
```

## Service URLs

| Service | URL |
|---------|-----|
| API | http://localhost:6709 |
| API Docs | http://localhost:6709/docs |
| UI | http://localhost:3000 |

## CLI Commands

### Backend Management

```bash
# Start/stop backend
mycasa backend start
mycasa backend stop
mycasa backend status

# Start/stop UI
mycasa ui start
mycasa ui stop
```

### System Setup

```bash
# Run intake (first-time setup)
mycasa intake \
  --income-name "J.P. Morgan Brokerage" \
  --income-type brokerage \
  --institution "J.P. Morgan" \
  --monthly-limit 10000 \
  --daily-limit 150 \
  --system-limit 1000
```

### Tasks

```bash
# List tasks
mycasa tasks list
mycasa tasks list --status pending
mycasa tasks list --status completed

# Create task
mycasa tasks create "Check smoke detectors" --category maintenance --priority medium

# Complete task
mycasa tasks complete 1 --evidence "All detectors tested OK"
```

### Transactions

```bash
# List transactions
mycasa transactions list --days 7
mycasa transactions list --category groceries

# Get summary
mycasa transactions summary --days 30
```

### Contractor Jobs

```bash
# List jobs
mycasa jobs list
mycasa jobs list --status proposed

# Create job
mycasa jobs create "Deck repair" --contractor "Juan" --cost 800
```

### Cost Tracking

```bash
# View cost summary
mycasa cost summary --period today
mycasa cost summary --period month

# Check budgets
mycasa cost budget
```

### Backup

```bash
# Export backup
mycasa backup export --notes "Before major update"

# List backups
mycasa backup list

# Restore (with verification)
mycasa backup restore backups/mycasa_backup_20260128_153000_abc123.zip

# Verify only (dry run)
mycasa backup restore backups/mycasa_backup_20260128_153000_abc123.zip --dry-run
```

### Status & Events

```bash
# Full system status
mycasa status

# Recent events
mycasa events --limit 20
```

## Running Tests

```bash
# Run all tests
cd /path/to/mycasa-pro
python -m pytest backend/tests/ -v

# Run specific test file
python -m pytest backend/tests/test_workflow.py -v

# Run with coverage
python -m pytest backend/tests/ -v --cov=backend
```

## Running Demo

```bash
# Full demo workflow
cd /path/to/mycasa-pro
python -m backend.demo

# This will:
# 1. Run system intake
# 2. Ingest sample transactions
# 3. Create contractor job
# 4. Schedule with Rakia
# 5. Finance approval
# 6. Complete job
# 7. Export backup
# 8. Verify backup
```

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /status` - Full system status

### Intake
- `GET /intake` - Check intake status
- `POST /intake` - Complete intake

### Settings
- `GET /settings/{manager_id}` - Get manager settings
- `PUT /settings/{manager_id}` - Update manager settings

### Transactions
- `GET /transactions` - List transactions
- `GET /transactions/summary` - Spending summary
- `POST /transactions/ingest` - Bulk ingest

### Tasks
- `GET /tasks` - List tasks
- `POST /tasks` - Create task
- `PATCH /tasks/{id}` - Update task
- `PATCH /tasks/{id}/complete` - Complete task

### Contractor Jobs
- `GET /jobs` - List jobs
- `POST /jobs` - Create job
- `PATCH /jobs/{id}/schedule` - Schedule job
- `PATCH /jobs/{id}/approve-cost` - Approve cost
- `PATCH /jobs/{id}/complete` - Complete job

### Cost Tracking
- `GET /cost` - Cost summary
- `POST /cost` - Record cost
- `GET /cost/budget` - Budget status

### Events
- `GET /events` - List events

### Backup
- `POST /backup/export` - Export backup
- `POST /backup/restore` - Restore backup
- `GET /backup/list` - List backups

### Inbox
- `GET /inbox/messages` - List messages
- `GET /inbox/unread-count` - Unread counts
- `POST /inbox/ingest` - Sync messages
- `PATCH /inbox/messages/{id}/read` - Mark read

## Troubleshooting

### Backend won't start

```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f "uvicorn.*api.main"

# Check Python path
which python
python --version
```

### Database issues

```bash
# Reset database (WARNING: deletes all data)
rm data/mycasa.db
mycasa backend start  # Will recreate tables
```

### Frontend issues

```bash
# Clear Next.js cache
cd frontend
rm -rf .next
npm run dev
```

### Connector issues

```bash
# Test Gmail connector
gog gmail search "newer_than:1d" --max 5 --json

# Test WhatsApp connector
wacli doctor
wacli chats list --limit 5 --json
```

## File Structure

```
mycasa-pro/
├── backend/
│   ├── api/           # FastAPI endpoints
│   ├── agents/        # Manager personas
│   ├── cli/           # CLI commands
│   ├── connectors/    # Gmail/WhatsApp
│   ├── core/          # Schemas, utils
│   ├── storage/       # Database, models
│   └── tests/         # Test suite
├── frontend/          # Next.js UI
├── data/              # Database files
├── backups/           # Backup exports
└── RUNBOOK.md         # This file
```

## Budget Configuration

Default budgets:
- Monthly Spend: $10,000
- Daily Spend: $150
- System Cost: $1,000/month

Warning thresholds: 70%, 85%, 100%

To modify:
```bash
# Via API
curl -X PUT http://localhost:8000/settings/finance \
  -H "Content-Type: application/json" \
  -d '{"monthly_limit": 15000, "daily_limit": 200}'
```

## Contacts

Known contractors in system:
- Juan: +1 253-431-2046 (WhatsApp) - Carpentry, deck work
- Rakia Baldé: +33 782-826-145 (WhatsApp) - House assistant, cleaning
