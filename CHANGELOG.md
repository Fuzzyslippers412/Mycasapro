# Changelog

All notable changes to MyCasa Pro.

## [1.0.2] - 2026-01-29

### Added

#### Enhanced Agent Coordination System

**Team Orchestration** (`agents/teams.py`)
- 8 pre-configured teams for different workflows:
  - 💰 Finance Review (sequential)
  - 🔧 Maintenance Dispatch (hierarchical)
  - 🚨 Security Response (sequential)
  - 📋 Project Planning (consensus)
  - 🏥 System Health (sequential)
  - 🏠 Full House Review (parallel)
  - ⚡ Emergency Response (hierarchical)
  - 💵 Budget Decision (consensus)
- 5 execution modes: `sequential`, `parallel`, `consensus`, `hierarchical`, `round_robin`
- Consensus voting with configurable thresholds
- Task result merging and synthesis
- Auto-escalation to manager on failure

**Event Bus (Pub/Sub)** (`agents/coordination.py`)
- 12 event types: task_created, task_completed, task_failed, message_received, alert_triggered, budget_warning, security_incident, maintenance_due, contractor_needed, system_health_change, user_request, schedule_trigger
- Subscribe/publish pattern for reactive coordination
- Priority levels: critical, high, normal, low
- Event history and consumption tracking

**Workflow Engine** (`agents/coordination.py`)
- Multi-step workflows with dependencies
- Step-level timeout and retry configuration
- Workflow context passed between steps
- On-complete and on-failure event triggers
- Parallel step execution when dependencies allow

**Intent-Based Routing** (`agents/coordination.py`)
- Smart routing using keywords + regex patterns
- Context-aware routing (conversation continuity boost)
- Multi-agent detection for complex requests
- Team suggestion for requests spanning domains
- Routing confidence scores
- Routing history for analysis

**Circuit Breaker**
- Track agent failures (3+ in 5 minutes = open circuit)
- Auto-recovery on successful operations
- Prevents cascade failures

**Shared Context**
- Global key-value store for cross-agent context
- Source tracking (which agent set a value)
- Context clear/get/set operations

**Enhanced Messaging**
- Priority-based message queues
- Reply-to message threading
- Broadcast to all agents
- TTL (time-to-live) for auto-expiring messages

**Teams API Routes** (`api/routes/teams.py` - 22 new endpoints)
- `GET /api/teams/` - List all teams
- `GET /api/teams/presets` - List preset teams
- `GET /api/teams/{team_id}` - Get team details + stats
- `POST /api/teams/` - Create custom team
- `DELETE /api/teams/{team_id}` - Delete custom team
- `POST /api/teams/tasks` - Create and execute team task
- `GET /api/teams/tasks` - List active tasks
- `GET /api/teams/tasks/{task_id}` - Get task status
- `GET /api/teams/tasks/history` - Task history
- `POST /api/teams/workflows` - Create and execute workflow
- `GET /api/teams/workflows` - List active workflows
- `GET /api/teams/workflows/history` - Workflow history
- `POST /api/teams/events` - Publish event
- `GET /api/teams/events` - Get recent events
- `GET /api/teams/events/types` - List event types
- `GET /api/teams/context` - Get all shared context
- `GET /api/teams/context/{key}` - Get context value
- `POST /api/teams/context` - Set context value
- `DELETE /api/teams/context/{key}` - Clear context key
- `POST /api/teams/route` - Route a message with team suggestion
- `GET /api/teams/agents` - List agents with health status
- `GET /api/teams/agents/{agent_id}/health` - Get agent health

**Manager Agent Enhancements**
- `coordinate_team()` - Spawn team for complex tasks
- `get_team_for_request()` - Analyze requests for team needs
- `handle_complex_request()` - Smart routing with team/agent selection
- `create_workflow()` - Create and execute multi-step workflows
- Event subscriptions for escalation handling
- Handles task_failed, security_incident, alert_triggered, budget_warning events

**Base Agent Enhancements**
- `handle_event()` - Override for domain-specific event handling
- `subscribe_to_events()` - Subscribe to multiple events
- `publish_event()` - Publish events from any agent
- `get_shared_context()` / `set_shared_context()` - Context access
- Auto-queue delegated tasks as pending tasks

### Changed
- API routes increased to 179 (from 157)
- Agent coordination now uses intent-based routing (not just keywords)
- Messages now support priority queues and TTL
- Coordinator state fully persisted (messages, events, workflows, context)

### Technical Details
- Coordination state persisted to `data/coordinator_state.json`
- Team state persisted to `data/teams/orchestrator_state.json`
- Event history capped at 500 events
- Message queue capped at 1000 messages
- Workflow history capped at 200 workflows

---

## [1.0.1] - 2026-01-29

### Added

#### Semantic Search
- **Embeddings Module** (`core/secondbrain/embeddings.py`)
  - Local semantic search using sentence-transformers
  - all-MiniLM-L6-v2 model for fast embeddings
  - Persistent embeddings index (JSON)
  - Auto-reindex on first search
- **API Routes**
  - GET /api/secondbrain/search/semantic - semantic similarity search
  - POST /api/secondbrain/embeddings/reindex - rebuild index
  - GET /api/secondbrain/embeddings/stats - index statistics

#### Bill Reminders & Notifications
- **Reminders Agent** (`agents/reminders.py`)
  - Bill reminder checking (7, 3, 1, 0 days before due)
  - Task reminder checking
  - Daily financial summary via WhatsApp
  - In-app notification creation
- **API Routes** (`api/routes/reminders.py`)
  - POST /api/reminders/check - check all reminders
  - POST /api/reminders/check/bills - bill reminders only
  - POST /api/reminders/check/tasks - task reminders only
  - POST /api/reminders/daily-summary - send morning summary
- **Scheduler Templates**
  - daily_bill_reminders (8:30 AM)
  - morning_summary (7:00 AM)
  - task_reminders (9:00 AM)

#### Dashboard Improvements
- **PortfolioChart** (`frontend/src/components/PortfolioChart.tsx`)
  - Live portfolio value display
  - Day change with trend indicators
  - Allocation bar by asset type
  - Top 5 holdings list
- **AgentTimeline** (`frontend/src/components/AgentTimeline.tsx`)
  - Real-time agent activity feed
  - Status badges (success/failed/pending)
  - Auto-refresh every 30 seconds

#### Contractor Calendar Integration
- Calendar event creation for scheduled jobs
- Uses `gog` CLI for Google Calendar
- Auto-creates all-day events with job details

#### Mobile-Responsive UI
- Comprehensive mobile CSS in globals.css
- Touch-friendly tap targets (44px minimum)
- Safe area insets for notched devices
- Responsive tables and cards
- Collapsible navigation

#### Chat Conversation Branching
- **Frontend UI** (`frontend/src/app/chat/page.tsx`)
  - Fork icon on message hover to create branch
  - Branch indicator button in header (shows current branch)
  - Branches drawer (right panel) to view/switch branches
  - Branch banner when on a forked conversation
  - Switch between parent and child branches
- **API Endpoints** (`api/routes/chat.py`)
  - DELETE /api/chat/conversations/{id} - delete a branch
  - GET /api/chat/conversations - list all conversations
  - (existing) POST /api/chat/fork - create branch from message
  - (existing) GET /api/chat/branches/{id} - get branch info

### Fixed
- **Async Bug** - Added nest_asyncio to fix asyncio.run() in async contexts
- **Start Script** - Fixed venv path (.venv instead of venv)

### Changed
- API routes increased to 157 (from 139)
- Scheduler templates increased to 8 (from 5)

---

## [1.0.0] - 2026-01-29

### Added

#### Agent System
- **Agent Teams** (`agents/teams.py`)
  - 5 pre-configured teams: finance_review, maintenance_dispatch, security_response, project_planning, daily_operations
  - 3 collaboration modes: parallel, sequential, consensus
  - Auto-routing based on task keywords
  - TeamRouter with synthesis by leader agent

- **Agent Scheduler** (`agents/scheduler.py`, `api/routes/scheduler.py`)
  - Schedule agents to run automatically
  - 5 frequency options: once, hourly, daily, weekly, monthly
  - 5 job templates for common tasks
  - 14 API endpoints for full CRUD + control
  - Persistent job storage and run history
  - Frontend UI in System → Scheduler tab

#### SecondBrain
- **Document Upload** (`api/routes/secondbrain.py`)
  - POST /api/secondbrain/upload
  - Supports PDF, DOCX, TXT, MD files
  - Auto-chunks large documents
  - Links chunks together
  - Tags with "uploaded"

- **Knowledge Graph API**
  - GET /api/secondbrain/graph - Full graph
  - GET /api/secondbrain/graph/{id} - Note connections
  - GET /api/secondbrain/stats - Vault statistics
  - GET /api/secondbrain/search - Text search

- **Interactive Graph Visualization** (`frontend/src/components/MemoryGraph/`)
  - Force-directed graph using react-force-graph-2d
  - Color-coded nodes by type
  - Zoom, pan, fit-to-view controls
  - Click nodes for detail modal
  - Filter by type, folder, search
  - Toggle graph/list view

#### Chat Interface
- **Reasoning Display**
  - Collapsible "How I decided this" section
  - Shows step-by-step reasoning
  - Intent detection, context loading, action taken

- **Shared Context** (`core/shared_context.py`)
  - Manager shares context with main Clawdbot
  - Loads MEMORY.md, USER.md, TOOLS.md
  - Access to daily memory files
  - Session history access

#### Connectors
- **Connector Marketplace** (`api/routes/connectors.py`, `frontend/src/components/ConnectorMarketplace/`)
  - Browse available connectors
  - View installation status
  - Configure and test connections
  - Health check all connectors

- **WhatsApp Connector** (`connectors/whatsapp/`)
  - Load contacts from TOOLS.md
  - Send messages via Clawdbot gateway
  - Resolve names to phone numbers

#### System
- **Live System Dashboard** (`api/routes/system_live.py`, `frontend/src/components/LiveSystemDashboard/`)
  - Real-time status of all systems
  - Auto-refresh every 5 seconds
  - Agents, SecondBrain, connectors, memory

- **Setup Wizard** (`frontend/src/components/SetupWizard/`)
  - 6-step onboarding flow
  - Tenant setup, income, budgets, connectors, notifications
  - Persists settings via API

#### Security
- **Prompt Security** (`core/prompt_security.py`)
  - Source classification (Owner/Trusted/Untrusted)
  - Injection pattern detection
  - Content leak auditing
  - Action gating by trust level

- **Enhanced Janitor Debugger** (`agents/janitor_debugger.py`)
  - Enum type handling checks
  - Spec compliance validation
  - Frontend/backend sync checks

### Changed
- API routes increased from ~60 to 139
- Frontend pages: 14 total
- SecondBrain vault notes: 21+
- All agents now inherit SecondBrain methods from BaseAgent

### Fixed
- Settings router not included in main.py
- Duplicate route detection in Janitor
- World-readable database files (chmod 600)
- Bare except clauses in janitor_debugger.py
- Wizard steps not matching spec
- Agent enum handling in SecondBrain

### Technical Debt Addressed
- Standardized error handling with correlation IDs
- Type validation for all API endpoints
- Consistent response formats
- Database file permissions secured

---

## [0.9.0] - 2026-01-28

### Added
- Initial MyCasa Pro implementation
- 8 specialized agents
- SecondBrain integration
- Frontend with 14 pages
- Portfolio management
- Basic API endpoints

---

## Future Plans

### High Priority
- Semantic search for SecondBrain
- Scheduled run notifications (WhatsApp/email)
- Agent activity timeline visualization

### Medium Priority
- Workspace/project organization
- Conversation branching UI
- Bill tracking and reminders

### Lower Priority
- Voice interface
- Mobile app
- Multi-tenant support

### Chat File Attachments
- **File Upload API** (`api/routes/chat.py`)
  - `POST /api/chat/upload` - Upload files for attachment
  - `GET /api/chat/uploads/{file_id}` - Get upload metadata
  - `DELETE /api/chat/uploads/{file_id}` - Delete upload
  - Supported: images (jpg, png, gif, webp), documents (pdf, doc, docx, txt, md), data (json, csv, yaml), code (py, js, ts)
  - Max size: 10MB per file
  - Generates previews for images

- **Chat API** (`api/routes/chat.py`)
  - `POST /api/chat/send` - Send message with optional attachments
  - `GET /api/chat/history` - Get conversation history
  - `POST /api/chat/clear` - Clear chat
  - `GET /api/chat/conversations` - List all conversations
  - `DELETE /api/chat/conversations/{id}` - Delete conversation
  - `POST /api/chat/fork` - Fork conversation from message
  - `GET /api/chat/branches/{id}` - Get branch info
  - Text file contents included in AI context
  - Images shown with preview thumbnails

- **Frontend Chat** (`frontend/src/app/chat/page.tsx`)
  - 📎 Paperclip button to attach files
  - File preview area with thumbnails
  - Multi-file upload support
  - Upload progress indicator
  - Remove attachment before sending
  - Attachments displayed in message bubbles
  - Image previews in messages
