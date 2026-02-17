# Terminal → Web UI Mapping (Clawdbot Clone)

**Date:** 2026-01-28
**Author:** Galidima (Builder/Architect Mode)
**Goal:** Build a web app that is a 1:1 clone of the Clawdbot terminal experience.

---

## 1) INVENTORY OF TERMINAL BEHAVIOR

### 1.1 Top-Level Commands

| Command | Description | Sync/Async | Side Effects |
|---------|-------------|------------|--------------|
| `setup` | Initialize ~/.clawdbot | Sync | Creates config files |
| `onboard` | Interactive wizard | Interactive | Creates workspace, config |
| `configure` | Setup credentials/devices | Interactive | Writes config |
| `config get/set/unset` | Config manipulation | Sync | Writes clawdbot.json |
| `doctor` | Health checks | Sync | May apply fixes |
| `dashboard` | Open Control UI | Sync | Opens browser |
| `reset` | Reset local state | Sync | Deletes files |
| `uninstall` | Remove gateway | Sync | Deletes files/services |
| `message send/broadcast/poll/react` | Send messages | Async | Network calls |
| `memory search/index` | Memory tools | Sync | Index updates |
| `agent` | Run agent turn | **Async/Streaming** | Model calls, file writes |
| `agents` | Manage agents | Sync | Config changes |
| `gateway run/start/stop/restart` | Gateway control | Service | Service lifecycle |
| `gateway status/health/probe` | Gateway status | Sync | None |
| `logs` | View logs | Sync | None |
| `system` | System events | Sync | None |
| `models list/set/scan` | Model config | Sync | Config writes |
| `approvals get/set/allowlist` | Exec approvals | Sync | Config writes |
| `nodes status/invoke/run/notify` | Node control | Async | Node commands |
| `sandbox` | Sandbox tools | Sync | Container ops |
| `tui` | Terminal UI | Interactive | None |
| `cron add/rm/enable/disable/run` | Cron jobs | Sync | Writes cron config |
| `plugins list/install/enable` | Plugin mgmt | Sync | Package installs |
| `channels list/login/logout` | Channel mgmt | Sync/Interactive | Auth flows |
| `skills list/info/check` | Skills mgmt | Sync | None |
| `browser *` | Browser control | Async | Browser automation |
| `sessions` | List sessions | Sync | None |
| `status` | Channel health | Sync | None |
| `health` | Gateway health | Sync | None |

### 1.2 Agent Command (Primary Focus)

```
clawdbot agent [options]

Options:
  -m, --message <text>       Message body
  -t, --to <number>          Recipient (session key)
  --session-id <id>          Explicit session
  --agent <id>               Agent override
  --thinking <level>         off|minimal|low|medium|high
  --verbose <on|off>         Verbose logging
  --channel <channel>        Delivery channel
  --local                    Embedded agent
  --deliver                  Send reply to channel
  --json                     JSON output
  --timeout <seconds>        Timeout (default 600)
```

**Output:**
- stdout: Agent response text (streaming)
- stderr: Progress indicators, warnings
- Exit codes: 0 success, 1 error, 130 interrupted

### 1.3 Gateway Command

```
clawdbot gateway [options] [command]

Subcommands:
  run          - Foreground gateway
  status       - Service status
  install      - Install service
  uninstall    - Remove service
  start        - Start service
  stop         - Stop service
  restart      - Restart service
  call         - Call gateway method
  usage-cost   - Cost summary
  health       - Health check
  probe        - Discovery + health
  discover     - Bonjour discovery
```

### 1.4 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CLAWDBOT_STATE_DIR` | State directory | ~/.clawdbot |
| `CLAWDBOT_CONFIG_PATH` | Config file | ~/.clawdbot/clawdbot.json |
| `CLAWDBOT_GATEWAY_TOKEN` | Gateway auth token | From config |
| `ANTHROPIC_API_KEY` | Model API key | Required |
| `OPENROUTER_API_KEY` | OpenRouter key | Optional |

### 1.5 Config File Structure

```json
{
  "meta": { "lastTouchedVersion": "...", "lastTouchedAt": "..." },
  "wizard": { "lastRunAt": "...", "lastRunCommand": "..." },
  "ui": { "assistant": { "name": "Galidima" } },
  "auth": { "profiles": { "anthropic:default": { "provider": "anthropic", "mode": "api_key" } } },
  "agents": {
    "defaults": {
      "workspace": "/path/to/workspace",
      "compaction": { "mode": "safeguard" },
      "maxConcurrent": 4,
      "subagents": { "maxConcurrent": 8 }
    }
  },
  "messages": { "responsePrefix": "[Galidima]", "ackReactionScope": "group-mentions" },
  "channels": {
    "whatsapp": {
      "dmPolicy": "allowlist",
      "allowFrom": ["+12677180107"],
      "groupPolicy": "allowlist"
    }
  },
  "gateway": { "port": 18789, "mode": "local", "bind": "loopback" },
  "heartbeat": { "intervalMs": 1800000 },
  "cron": { "jobs": [...] }
}
```

### 1.6 Side Effects by Command

| Command | Files Written | Network Calls | DB Writes |
|---------|---------------|---------------|-----------|
| `agent` | sessions/*.json, memory/*.md | Model API, tool calls | Session store |
| `message send` | None | Channel API | Message log |
| `config set` | clawdbot.json | None | None |
| `cron add` | clawdbot.json | Gateway WS | None |
| `gateway start` | pid files, logs | Binds port | None |
| `browser *` | Screenshots, PDFs | Browser CDP | None |

---

## 2) CONTRACTS / INTERFACES

### 2.1 CommandRunner Interface

```python
class CommandRunner:
    """
    Core interface for executing CLI commands.
    Single entry point for both terminal and web UI.
    """
    
    async def run(
        self,
        command_string: str,
        context: ExecutionContext
    ) -> AsyncIterator[CommandEvent]:
        """
        Execute a command and yield events.
        
        Args:
            command_string: Full CLI command (e.g., "agent -m 'hello' --to +1234")
            context: Execution context with user/session/permissions
        
        Yields:
            CommandEvent instances for each output chunk/state change
        """
        pass


@dataclass
class ExecutionContext:
    user_id: str
    session_id: str
    permissions: Set[str]          # e.g., {"exec.shell", "browser.control"}
    budget_limits: BudgetLimits    # cost caps
    connectors: Dict[str, Any]     # channel configs
    workspace_path: Path
    env_overrides: Dict[str, str]
    timeout_seconds: int = 600
    stream_output: bool = True


@dataclass
class BudgetLimits:
    system_cost_cap_monthly: float = 1000.0
    spend_limit_monthly: float = 10000.0
    spend_limit_daily: float = 150.0
    current_month_cost: float = 0.0
    current_day_spend: float = 0.0
```

### 2.2 Event Types

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


class EventType(Enum):
    # Command lifecycle
    COMMAND_STARTED = "command_started"
    STDOUT_CHUNK = "stdout_chunk"
    STDERR_CHUNK = "stderr_chunk"
    COMMAND_FINISHED = "command_finished"
    
    # Task lifecycle (for async operations)
    TASK_QUEUED = "task_queued"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    
    # Approvals
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    
    # Cost tracking
    COST_INCURRED = "cost_incurred"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    
    # Tool calls
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"


@dataclass
class CommandEvent:
    event_type: EventType
    timestamp: datetime
    command_id: str
    session_id: str
    
    # Content (varies by event type)
    data: Optional[str] = None         # stdout/stderr chunk
    exit_code: Optional[int] = None    # for COMMAND_FINISHED
    progress: Optional[float] = None   # 0.0-1.0 for TASK_PROGRESS
    error: Optional[str] = None        # for failures
    cost: Optional[float] = None       # for COST_INCURRED
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.event_type.value,
            "ts": self.timestamp.isoformat(),
            "command_id": self.command_id,
            "session_id": self.session_id,
            "data": self.data,
            "exit_code": self.exit_code,
            "progress": self.progress,
            "error": self.error,
            "cost": self.cost,
            "meta": self.metadata
        }
```

### 2.3 Transcript Model

```python
@dataclass
class TranscriptEntry:
    """Append-only transcript entry"""
    id: str                    # UUID
    timestamp: datetime
    session_id: str
    command_id: str
    entry_type: str            # "input", "stdout", "stderr", "event"
    content: str
    metadata: Optional[dict] = None


class TranscriptStore:
    """Append-only transcript persistence"""
    
    def append(self, entry: TranscriptEntry) -> None:
        """Append entry to transcript (never modify/delete)"""
        pass
    
    def get_session_transcript(
        self, 
        session_id: str, 
        since: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[TranscriptEntry]:
        """Retrieve transcript entries"""
        pass
    
    def search(self, query: str, session_id: Optional[str] = None) -> List[TranscriptEntry]:
        """Full-text search transcripts"""
        pass
```

---

## 3) ARCHITECTURE

### 3.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           WEB BROWSER                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Next.js Frontend                             │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │  Terminal  │  │   Tasks    │  │  Settings  │  │   Logs     │  │   │
│  │  │    Pane    │  │ Dashboard  │  │   Panel    │  │   View     │  │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  │   │
│  └────────┼───────────────┼───────────────┼───────────────┼─────────┘   │
│           │               │               │               │             │
│           └───────────────┴───────────────┴───────────────┘             │
│                                   │                                      │
│                          WebSocket / SSE                                 │
│                                   │                                      │
└───────────────────────────────────┼──────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼──────────────────────────────────────┐
│                           FastAPI Backend                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      API Layer (REST + WS)                       │    │
│  │  /api/commands/run  /api/tasks  /api/sessions  /api/settings    │    │
│  └─────────────────────────────────┬───────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────┼───────────────────────────────┐    │
│  │              CLI Compatibility Adapter                           │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │  CommandRunner.run("clawdbot agent -m 'hi'", context)   │    │    │
│  │  │                                                          │    │    │
│  │  │  Option A: Direct import (same process)                  │    │    │
│  │  │    from clawdbot.cli import main                         │    │    │
│  │  │    main(["agent", "-m", "hi"])                           │    │    │
│  │  │                                                          │    │    │
│  │  │  Option B: Subprocess (isolation)                        │    │    │
│  │  │    subprocess.Popen(["clawdbot", "agent", "-m", "hi"])   │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────┬───────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────┼───────────────────────────────┐    │
│  │              Background Worker (Celery/ARQ/Custom)               │    │
│  │  - Long-running commands                                         │    │
│  │  - Async task queue                                              │    │
│  │  - Timeout management                                            │    │
│  │  - Retry logic                                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         Storage Layer                            │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐     │    │
│  │  │ Transcripts│ │   Tasks   │ │  Settings │ │Cost Ledger│     │    │
│  │  │  (JSONL)  │  │ (SQLite)  │ │ (SQLite)  │ │ (SQLite)  │     │    │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ subprocess / import
                                    │
┌───────────────────────────────────┼──────────────────────────────────────┐
│                        Clawdbot CLI Runtime                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  - Gateway WebSocket (ws://127.0.0.1:18789)                      │    │
│  │  - Model APIs (Anthropic, OpenRouter)                            │    │
│  │  - Channel APIs (WhatsApp, Telegram, Discord, etc.)              │    │
│  │  - Tool execution (browser, nodes, sandbox)                      │    │
│  │  - Session management                                            │    │
│  │  - Plugin system                                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Directory Structure

```
clawdbot-web/
├── backend/
│   ├── api/
│   │   ├── main.py                 # FastAPI app
│   │   ├── routes/
│   │   │   ├── commands.py         # POST /api/commands/run
│   │   │   ├── tasks.py            # Task CRUD
│   │   │   ├── sessions.py         # Session management
│   │   │   ├── settings.py         # User settings
│   │   │   ├── transcripts.py      # Transcript retrieval
│   │   │   └── cost.py             # Cost ledger
│   │   └── websocket.py            # WebSocket for streaming
│   ├── core/
│   │   ├── command_runner.py       # CLI compatibility adapter
│   │   ├── events.py               # Event types
│   │   ├── context.py              # Execution context
│   │   └── budget.py               # Budget enforcement
│   ├── workers/
│   │   ├── task_queue.py           # Background task processing
│   │   └── handlers.py             # Command handlers
│   ├── storage/
│   │   ├── database.py             # SQLite setup
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── transcripts.py          # JSONL transcript store
│   │   └── repository.py           # Data access
│   └── integrations/
│       ├── clawdbot_adapter.py     # CLI execution wrapper
│       └── gateway_client.py       # Gateway WebSocket client
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Main terminal page
│       │   ├── tasks/page.tsx      # Tasks dashboard
│       │   ├── settings/page.tsx   # Settings
│       │   └── logs/page.tsx       # Logs viewer
│       ├── components/
│       │   ├── Terminal/
│       │   │   ├── Terminal.tsx    # Main terminal component
│       │   │   ├── Input.tsx       # Multiline input
│       │   │   ├── Output.tsx      # Stdout/stderr display
│       │   │   └── History.tsx     # Command history
│       │   ├── TasksSidebar.tsx    # Running tasks
│       │   ├── ApprovalModal.tsx   # Approval prompts
│       │   └── CostWidget.tsx      # Cost display
│       └── lib/
│           ├── api.ts              # API client
│           └── websocket.ts        # WebSocket client
├── data/
│   ├── clawdbot-web.db            # SQLite database
│   └── transcripts/               # JSONL transcripts
├── requirements.txt
├── package.json
└── start.sh
```

### 3.3 CLI Compatibility Adapter

```python
# backend/core/command_runner.py

import asyncio
import subprocess
import shlex
from typing import AsyncIterator
from pathlib import Path

from .events import CommandEvent, EventType
from .context import ExecutionContext


class CLIAdapter:
    """
    Executes Clawdbot CLI commands and streams output.
    Uses subprocess for isolation and to preserve exact CLI behavior.
    """
    
    def __init__(self, clawdbot_path: str = "clawdbot"):
        self.clawdbot_path = clawdbot_path
    
    async def run(
        self,
        command_string: str,
        context: ExecutionContext
    ) -> AsyncIterator[CommandEvent]:
        """
        Execute CLI command and yield events.
        
        Streams stdout/stderr in real-time.
        Handles long-running commands without blocking.
        Supports cancellation via context.
        """
        command_id = self._generate_command_id()
        
        # Parse command (remove "clawdbot" prefix if present)
        args = shlex.split(command_string)
        if args and args[0] == "clawdbot":
            args = args[1:]
        
        # Build full command
        full_cmd = [self.clawdbot_path] + args
        
        # Set up environment
        env = self._build_env(context)
        
        # Emit start event
        yield CommandEvent(
            event_type=EventType.COMMAND_STARTED,
            timestamp=datetime.utcnow(),
            command_id=command_id,
            session_id=context.session_id,
            metadata={"command": command_string, "args": args}
        )
        
        try:
            # Start subprocess with pipes
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(context.workspace_path)
            )
            
            # Stream output concurrently
            async def stream_pipe(pipe, event_type):
                while True:
                    line = await pipe.readline()
                    if not line:
                        break
                    yield CommandEvent(
                        event_type=event_type,
                        timestamp=datetime.utcnow(),
                        command_id=command_id,
                        session_id=context.session_id,
                        data=line.decode('utf-8', errors='replace')
                    )
            
            # Merge stdout and stderr streams
            stdout_task = asyncio.create_task(
                self._collect_stream(process.stdout, EventType.STDOUT_CHUNK, command_id, context.session_id)
            )
            stderr_task = asyncio.create_task(
                self._collect_stream(process.stderr, EventType.STDERR_CHUNK, command_id, context.session_id)
            )
            
            # Yield events as they arrive
            pending = {stdout_task, stderr_task}
            while pending:
                done, pending = await asyncio.wait(
                    pending,
                    timeout=0.1,
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    events = task.result()
                    for event in events:
                        yield event
            
            # Wait for process to complete
            exit_code = await asyncio.wait_for(
                process.wait(),
                timeout=context.timeout_seconds
            )
            
            yield CommandEvent(
                event_type=EventType.COMMAND_FINISHED,
                timestamp=datetime.utcnow(),
                command_id=command_id,
                session_id=context.session_id,
                exit_code=exit_code
            )
            
        except asyncio.TimeoutError:
            process.kill()
            yield CommandEvent(
                event_type=EventType.TASK_FAILED,
                timestamp=datetime.utcnow(),
                command_id=command_id,
                session_id=context.session_id,
                error=f"Command timed out after {context.timeout_seconds}s"
            )
        except Exception as e:
            yield CommandEvent(
                event_type=EventType.TASK_FAILED,
                timestamp=datetime.utcnow(),
                command_id=command_id,
                session_id=context.session_id,
                error=str(e)
            )
    
    async def _collect_stream(
        self,
        stream,
        event_type: EventType,
        command_id: str,
        session_id: str
    ) -> List[CommandEvent]:
        """Collect all events from a stream"""
        events = []
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            events.append(CommandEvent(
                event_type=event_type,
                timestamp=datetime.utcnow(),
                command_id=command_id,
                session_id=session_id,
                data=chunk.decode('utf-8', errors='replace')
            ))
        return events
    
    def _build_env(self, context: ExecutionContext) -> dict:
        """Build environment variables for subprocess"""
        import os
        env = os.environ.copy()
        env.update(context.env_overrides)
        return env
    
    def _generate_command_id(self) -> str:
        import uuid
        return f"cmd_{uuid.uuid4().hex[:12]}"
```

---

## 4) UI SPEC (CLONE TERMINAL UX)

### 4.1 Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Logo] Clawdbot Terminal                              [🌙] [⚙️] [👤]    │
├────────────────────────────────────────────────┬─────────────────────────┤
│                                                │   LIVE TASKS            │
│  ┌──────────────────────────────────────────┐  │   ┌─────────────────┐   │
│  │ $ clawdbot agent -m "summarize inbox"    │  │   │ 🟢 agent -m ... │   │
│  │                                          │  │   │    Running 12s   │   │
│  │ 📬 **Inbox Summary**                     │  │   └─────────────────┘   │
│  │                                          │  │   ┌─────────────────┐   │
│  │ You have 5 unread messages:              │  │   │ ⏳ cron job #3   │   │
│  │ - Jessie: "Call me when..."              │  │   │    Queued        │   │
│  │ - Bank: "Statement ready"                │  │   └─────────────────┘   │
│  │ - ...                                    │  │                         │
│  │                                          │  ├─────────────────────────┤
│  │ [✓ Done] Exit code: 0                    │  │   RECENT EVENTS         │
│  │                                          │  │   • agent completed      │
│  │ $ _                                      │  │   • message sent         │
│  │                                          │  │   • cron fired           │
│  └──────────────────────────────────────────┘  │                         │
│                                                ├─────────────────────────┤
│  [↑↓ History] [Tab Complete] [Ctrl+C Cancel]   │   APPROVALS (0)         │
│                                                │   No pending approvals   │
│                                                ├─────────────────────────┤
│                                                │   COST                   │
│                                                │   Today: $0.42           │
│                                                │   Month: $127.50         │
│                                                │   Budget: $1000          │
│                                                │   [██████░░░░] 12.8%     │
└────────────────────────────────────────────────┴─────────────────────────┘
```

### 4.2 Terminal Pane Requirements

| Feature | Implementation |
|---------|----------------|
| **Multiline input** | Shift+Enter for newline, Enter to submit |
| **History** | Up/Down arrows, persisted in localStorage |
| **Copy/paste** | Ctrl+C/V, right-click menu |
| **Stdout styling** | White/light text |
| **Stderr styling** | Yellow/orange text, italic |
| **Clickable artifacts** | Links, file paths open in new tab |
| **Re-run button** | Click on any previous command to re-run |
| **Clear** | Ctrl+L or `clear` command |
| **Cancel** | Ctrl+C sends interrupt signal |
| **Exit code** | Show [✓ 0] or [✗ 1] badge |
| **Streaming** | Characters appear as they arrive |
| **Timestamps** | Hover to see execution time |

### 4.3 Tasks Sidebar

```typescript
interface Task {
  id: string;
  command: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt?: Date;
  completedAt?: Date;
  exitCode?: number;
  progress?: number;  // 0-100
  error?: string;
}

// Display:
// 🟢 Running (animated pulse)
// ⏳ Queued (static)
// ✅ Completed
// ❌ Failed
// 🚫 Cancelled
```

### 4.4 No Streamlit Branding

```css
/* Remove all Streamlit elements */
#MainMenu { display: none !important; }
footer { display: none !important; }
header { display: none !important; }
.stDeployButton { display: none !important; }

/* Custom favicon */
link[rel="icon"] { display: none; }
```

---

## 5) STREAMLIT IMPLEMENTATION PLAN

**Decision: DO NOT USE STREAMLIT**

Streamlit is unsuitable for this use case because:
1. No WebSocket streaming support
2. Reruns on every interaction
3. Cannot remove branding cleanly
4. No real terminal emulation

**Use Instead: Next.js + FastAPI**

### 5.1 Alternative: Next.js Frontend

```bash
# Install
cd frontend
npm install next@latest react@latest react-dom@latest
npm install @mantine/core @mantine/hooks
npm install xterm xterm-addon-fit xterm-addon-web-links
npm install socket.io-client
```

### 5.2 Terminal Component (xterm.js)

```typescript
// frontend/src/components/Terminal/Terminal.tsx
import { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';

export function TerminalPane({ 
  onCommand,
  events 
}: { 
  onCommand: (cmd: string) => void;
  events: CommandEvent[];
}) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  
  useEffect(() => {
    if (!terminalRef.current) return;
    
    const terminal = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'JetBrains Mono, Monaco, monospace',
      theme: {
        background: '#1a1a1a',
        foreground: '#e0e0e0',
        cursor: '#ffffff',
        selection: 'rgba(255, 255, 255, 0.3)',
      }
    });
    
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(new WebLinksAddon());
    
    terminal.open(terminalRef.current);
    fitAddon.fit();
    
    // Handle input
    let currentLine = '';
    terminal.onKey(({ key, domEvent }) => {
      if (domEvent.key === 'Enter') {
        terminal.writeln('');
        onCommand(currentLine);
        currentLine = '';
      } else if (domEvent.key === 'Backspace') {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          terminal.write('\b \b');
        }
      } else {
        currentLine += key;
        terminal.write(key);
      }
    });
    
    terminal.write('$ ');
    xtermRef.current = terminal;
    
    return () => terminal.dispose();
  }, []);
  
  // Write events to terminal
  useEffect(() => {
    const terminal = xtermRef.current;
    if (!terminal) return;
    
    for (const event of events) {
      if (event.event_type === 'stdout_chunk') {
        terminal.write(event.data || '');
      } else if (event.event_type === 'stderr_chunk') {
        terminal.write(`\x1b[33m${event.data}\x1b[0m`);  // Yellow for stderr
      } else if (event.event_type === 'command_finished') {
        const color = event.exit_code === 0 ? '\x1b[32m' : '\x1b[31m';
        terminal.writeln(`${color}[Exit ${event.exit_code}]\x1b[0m`);
        terminal.write('$ ');
      }
    }
  }, [events]);
  
  return <div ref={terminalRef} style={{ height: '100%', width: '100%' }} />;
}
```

---

## 6) COMMAND EXECUTION / STREAMING OUTPUT

### 6.1 WebSocket Protocol

```typescript
// Client -> Server
interface ExecuteCommand {
  type: 'execute';
  command: string;
  session_id?: string;
  timeout?: number;
}

interface CancelCommand {
  type: 'cancel';
  command_id: string;
}

// Server -> Client
interface CommandStarted {
  type: 'command_started';
  command_id: string;
  command: string;
  timestamp: string;
}

interface OutputChunk {
  type: 'stdout' | 'stderr';
  command_id: string;
  data: string;
  timestamp: string;
}

interface CommandFinished {
  type: 'command_finished';
  command_id: string;
  exit_code: number;
  duration_ms: number;
  cost?: number;
}
```

### 6.2 Backend WebSocket Handler

```python
# backend/api/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.running_commands: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        # Cancel any running commands
        if session_id in self.running_commands:
            self.running_commands[session_id].cancel()
    
    async def handle_message(self, session_id: str, data: dict):
        if data['type'] == 'execute':
            await self.execute_command(session_id, data)
        elif data['type'] == 'cancel':
            await self.cancel_command(session_id, data['command_id'])
    
    async def execute_command(self, session_id: str, data: dict):
        websocket = self.active_connections[session_id]
        context = self.build_context(session_id, data)
        
        async def run_and_stream():
            cli = CLIAdapter()
            async for event in cli.run(data['command'], context):
                await websocket.send_json(event.to_dict())
        
        task = asyncio.create_task(run_and_stream())
        self.running_commands[session_id] = task
        
        try:
            await task
        except asyncio.CancelledError:
            await websocket.send_json({
                'type': 'command_cancelled',
                'command_id': data.get('command_id')
            })
        finally:
            if session_id in self.running_commands:
                del self.running_commands[session_id]
    
    async def cancel_command(self, session_id: str, command_id: str):
        if session_id in self.running_commands:
            self.running_commands[session_id].cancel()
```

### 6.3 Timeout & Retry Logic

```python
class CommandExecutor:
    DEFAULT_TIMEOUT = 600  # 10 minutes
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    # Commands that are safe to retry
    RETRIABLE_COMMANDS = {
        'status', 'health', 'sessions', 'skills list', 
        'models list', 'channels list', 'nodes status'
    }
    
    async def execute_with_retry(
        self,
        command: str,
        context: ExecutionContext,
        on_event: Callable[[CommandEvent], Awaitable[None]]
    ):
        retries = 0
        last_error = None
        
        while retries <= self.MAX_RETRIES:
            try:
                async for event in self.cli.run(command, context):
                    await on_event(event)
                    if event.event_type == EventType.COMMAND_FINISHED:
                        return event.exit_code
                    if event.event_type == EventType.TASK_FAILED:
                        raise Exception(event.error)
            except Exception as e:
                last_error = e
                if not self._is_retriable(command):
                    raise
                retries += 1
                if retries <= self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY * retries)
        
        raise last_error
    
    def _is_retriable(self, command: str) -> bool:
        return any(command.startswith(rc) for rc in self.RETRIABLE_COMMANDS)
```

---

## 7) STATE, SETTINGS, AND PROFILES

### 7.1 Settings Schema

```python
# backend/storage/models.py

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, index=True)
    
    # Global settings
    theme = Column(String, default="dark")
    font_size = Column(Integer, default=14)
    
    # Budget caps
    system_cost_cap_monthly = Column(Float, default=1000.0)
    spend_limit_monthly = Column(Float, default=10000.0)
    spend_limit_daily = Column(Float, default=150.0)
    
    # Notification preferences
    notify_on_completion = Column(Boolean, default=True)
    notify_on_error = Column(Boolean, default=True)
    notify_on_approval = Column(Boolean, default=True)
    
    # Default command options
    default_thinking_level = Column(String, default="low")
    default_timeout = Column(Integer, default=600)
    
    # Finance Manager intake
    finance_intake_complete = Column(Boolean, default=False)
    primary_income_source = Column(String, nullable=True)
    key_accounts = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class AgentProfile(Base):
    __tablename__ = "agent_profiles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    name = Column(String)  # "main", "ops", "finance", etc.
    
    # Agent-specific settings
    model = Column(String, default="claude-opus-4")
    thinking_level = Column(String, default="low")
    verbose = Column(Boolean, default=False)
    
    # Workspace
    workspace_path = Column(String)
    
    # Permissions
    allowed_tools = Column(JSON, default=list)
    blocked_tools = Column(JSON, default=list)
    
    # Connectors
    enabled_channels = Column(JSON, default=list)
    
    is_default = Column(Boolean, default=False)
```

### 7.2 Finance Manager Intake

```python
# backend/api/routes/settings.py

@router.post("/settings/finance-intake")
async def complete_finance_intake(
    intake: FinanceIntakeRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Finance Manager intake flow.
    Must be completed before budgets are enforced.
    """
    # Validate required fields
    if not intake.primary_income_source:
        raise HTTPException(400, "Primary income source required")
    
    # Update settings
    settings = await get_or_create_settings(user_id)
    settings.finance_intake_complete = True
    settings.primary_income_source = intake.primary_income_source
    settings.key_accounts = intake.key_accounts
    
    # Apply budget limits
    settings.system_cost_cap_monthly = intake.system_cost_cap or 1000.0
    settings.spend_limit_monthly = intake.spend_limit_monthly or 10000.0
    settings.spend_limit_daily = intake.spend_limit_daily or 150.0
    
    await save_settings(settings)
    
    return {"success": True, "message": "Finance intake complete"}


class FinanceIntakeRequest(BaseModel):
    primary_income_source: str  # "JP Morgan Brokerage"
    key_accounts: List[AccountInfo]  # [{name, balance, type}]
    system_cost_cap: Optional[float] = 1000.0
    spend_limit_monthly: Optional[float] = 10000.0
    spend_limit_daily: Optional[float] = 150.0
```

---

## 8) COST LEDGER + JANITOR HOOKS

### 8.1 Cost Tracking Model

```python
class CostEntry(Base):
    __tablename__ = "cost_entries"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Source
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    command_id = Column(String, index=True)
    agent_id = Column(String, nullable=True)
    
    # Cost details
    model = Column(String)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    estimated_cost = Column(Float)
    actual_cost = Column(Float, nullable=True)
    
    # Context
    command = Column(String)
    tool_calls = Column(JSON, default=list)


# Token pricing (cents per 1K tokens)
TOKEN_PRICING = {
    "claude-opus-4": {"input": 1.5, "output": 7.5},
    "claude-sonnet-4": {"input": 0.3, "output": 1.5},
    "claude-haiku-3.5": {"input": 0.025, "output": 0.125},
    "gpt-4-turbo": {"input": 1.0, "output": 3.0},
}

def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost in dollars"""
    pricing = TOKEN_PRICING.get(model, TOKEN_PRICING["claude-opus-4"])
    cost = (tokens_in / 1000 * pricing["input"]) + (tokens_out / 1000 * pricing["output"])
    return round(cost / 100, 4)  # Convert cents to dollars
```

### 8.2 Janitor Integration

```python
# backend/workers/janitor.py

class CostJanitor:
    """
    Background worker that aggregates and reports costs.
    """
    
    async def run_daily_report(self):
        """Generate daily cost report for Finance Manager"""
        today = date.today()
        
        entries = await get_cost_entries(
            since=datetime.combine(today, time.min),
            until=datetime.combine(today, time.max)
        )
        
        report = {
            "date": today.isoformat(),
            "total_cost": sum(e.estimated_cost for e in entries),
            "by_model": self._aggregate_by_model(entries),
            "by_agent": self._aggregate_by_agent(entries),
            "top_commands": self._top_commands(entries, limit=10),
            "token_usage": {
                "total_in": sum(e.tokens_in for e in entries),
                "total_out": sum(e.tokens_out for e in entries)
            }
        }
        
        # Queue report for Finance Manager
        await queue_manager_message(
            f"📊 **Daily Cost Report ({today})**\n\n"
            f"Total: ${report['total_cost']:.2f}\n"
            f"Tokens: {report['token_usage']['total_in']:,} in / "
            f"{report['token_usage']['total_out']:,} out"
        )
        
        return report
    
    async def check_budget_limits(self, user_id: str) -> List[str]:
        """Check if approaching budget limits"""
        warnings = []
        settings = await get_settings(user_id)
        
        month_cost = await get_month_cost(user_id)
        day_cost = await get_day_cost(user_id)
        
        # Monthly system cost
        if month_cost >= settings.system_cost_cap_monthly * 0.9:
            warnings.append(f"System cost at {month_cost:.0f}% of monthly cap")
        
        # Daily spend
        if day_cost >= settings.spend_limit_daily * 0.8:
            warnings.append(f"Daily spend at {day_cost:.0f}% of limit")
        
        return warnings
```

---

## 9) APPROVALS & GUARDRAILS

### 9.1 Approval System

```python
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String, unique=True, index=True)
    
    user_id = Column(String, index=True)
    session_id = Column(String)
    command_id = Column(String)
    
    # What needs approval
    action_type = Column(String)  # "exec", "send_message", "payment", etc.
    action_details = Column(JSON)
    risk_level = Column(String)  # "low", "medium", "high", "critical"
    
    # Estimated impact
    estimated_cost = Column(Float, nullable=True)
    affected_resources = Column(JSON, default=list)
    
    # Status
    status = Column(String, default="pending")  # pending, approved, denied, expired
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_note = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


# Approval gates configuration
APPROVAL_GATES = {
    "exec.shell": {
        "always_require": True,
        "except_allowlist": True  # Use per-agent allowlist
    },
    "message.send": {
        "require_if": lambda ctx: ctx.get("first_time_contact"),
    },
    "payment": {
        "require_above": 100.0,  # Dollars
    },
    "browser.navigate": {
        "require_if": lambda ctx: ctx.get("domain") not in TRUSTED_DOMAINS
    }
}


async def check_approval_required(
    action_type: str,
    context: dict,
    user_settings: UserSettings
) -> Optional[ApprovalRequest]:
    """Check if action requires approval"""
    gate = APPROVAL_GATES.get(action_type)
    if not gate:
        return None
    
    requires_approval = False
    
    if gate.get("always_require"):
        requires_approval = True
    
    if gate.get("require_if"):
        requires_approval = gate["require_if"](context)
    
    if gate.get("require_above"):
        amount = context.get("amount", 0)
        requires_approval = amount >= gate["require_above"]
    
    if requires_approval:
        return await create_approval_request(action_type, context)
    
    return None
```

### 9.2 Budget Guardrails

```python
class BudgetEnforcer:
    """Enforce budget limits before command execution"""
    
    async def check(self, command: str, context: ExecutionContext) -> BudgetCheckResult:
        settings = await get_settings(context.user_id)
        
        # Estimate command cost
        estimated_cost = await estimate_command_cost(command)
        
        # Check daily limit
        day_cost = await get_day_cost(context.user_id)
        if day_cost + estimated_cost > settings.spend_limit_daily:
            return BudgetCheckResult(
                allowed=False,
                reason=f"Would exceed daily limit (${settings.spend_limit_daily})",
                suggestion="Try --cheap flag for reduced model/tokens"
            )
        
        # Check monthly limit
        month_cost = await get_month_cost(context.user_id)
        if month_cost + estimated_cost > settings.system_cost_cap_monthly:
            return BudgetCheckResult(
                allowed=False,
                reason=f"Would exceed monthly cap (${settings.system_cost_cap_monthly})",
                suggestion="Wait until next month or increase cap in settings"
            )
        
        # Warning thresholds
        warnings = []
        if month_cost / settings.system_cost_cap_monthly > 0.9:
            warnings.append(f"Monthly cost at {month_cost/settings.system_cost_cap_monthly*100:.0f}%")
        
        return BudgetCheckResult(allowed=True, warnings=warnings)


@dataclass
class BudgetCheckResult:
    allowed: bool
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
```

---

## 10) TEST PLAN

### 10.1 Golden Tests

```python
# tests/test_golden.py

import pytest
import subprocess
import asyncio
from web_runner import run_command_via_web

GOLDEN_COMMANDS = [
    ("clawdbot status", None),
    ("clawdbot health", None),
    ("clawdbot sessions", None),
    ("clawdbot skills list", None),
    ("clawdbot models list", None),
    ("clawdbot channels list", None),
    ("clawdbot config get agents.defaults.workspace", None),
    ("clawdbot agent -m 'say hello' --json", {"contains": "hello"}),
]


@pytest.mark.parametrize("command,check", GOLDEN_COMMANDS)
async def test_golden_match(command, check):
    """Terminal and web must produce identical output"""
    
    # Run via terminal
    terminal_result = subprocess.run(
        command.split(),
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Run via web
    web_result = await run_command_via_web(command, timeout=60)
    
    # Compare exit codes
    assert terminal_result.returncode == web_result.exit_code, \
        f"Exit code mismatch: terminal={terminal_result.returncode}, web={web_result.exit_code}"
    
    # Compare output (normalized)
    terminal_output = normalize_output(terminal_result.stdout)
    web_output = normalize_output(web_result.stdout)
    
    if check and check.get("contains"):
        assert check["contains"] in web_output
    else:
        assert terminal_output == web_output, \
            f"Output mismatch:\nTerminal: {terminal_output}\nWeb: {web_output}"


def normalize_output(output: str) -> str:
    """Normalize output for comparison (strip timestamps, etc.)"""
    import re
    # Remove timestamps
    output = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', output)
    # Remove process IDs
    output = re.sub(r'pid \d+', 'pid XXXX', output)
    # Strip whitespace
    return output.strip()
```

### 10.2 Performance Tests

```python
# tests/test_performance.py

import asyncio
import pytest
from statistics import mean, stdev

@pytest.mark.performance
async def test_concurrent_commands():
    """Test multiple concurrent command executions"""
    commands = ["clawdbot status"] * 10
    
    async def run_one(cmd):
        start = time.time()
        result = await run_command_via_web(cmd)
        return time.time() - start
    
    times = await asyncio.gather(*[run_one(c) for c in commands])
    
    assert mean(times) < 2.0, f"Mean time {mean(times):.2f}s exceeds 2s"
    assert max(times) < 5.0, f"Max time {max(times):.2f}s exceeds 5s"


@pytest.mark.performance
async def test_streaming_latency():
    """Test first-byte latency for streaming commands"""
    async with websocket_connect() as ws:
        start = time.time()
        await ws.send_json({"type": "execute", "command": "clawdbot agent -m 'hi'"})
        
        # Wait for first output chunk
        first_chunk = await ws.receive_json()
        first_byte_time = time.time() - start
        
        assert first_byte_time < 1.0, f"First byte latency {first_byte_time:.2f}s exceeds 1s"
```

### 10.3 Failure Tests

```python
# tests/test_failures.py

@pytest.mark.failure
async def test_network_timeout():
    """Test behavior when gateway is unreachable"""
    with mock_gateway_down():
        result = await run_command_via_web("clawdbot agent -m 'test'")
        assert result.exit_code != 0
        assert "connection" in result.stderr.lower() or "timeout" in result.stderr.lower()


@pytest.mark.failure
async def test_invalid_command():
    """Test invalid command handling"""
    result = await run_command_via_web("clawdbot invalid-command")
    assert result.exit_code != 0
    assert "unknown command" in result.stderr.lower()


@pytest.mark.failure
async def test_permission_denied():
    """Test permission denial"""
    context = ExecutionContext(permissions=set())  # No permissions
    result = await run_command_via_web(
        "clawdbot browser navigate https://example.com",
        context=context
    )
    assert result.exit_code != 0
    assert "permission" in result.stderr.lower()
```

---

## 11) ROLLOUT PLAN

### Phase 1: Terminal Pane + Streaming (Week 1-2)
- [ ] Set up Next.js + FastAPI project structure
- [ ] Implement WebSocket streaming
- [ ] Create xterm.js terminal component
- [ ] Implement CLI adapter (subprocess execution)
- [ ] Basic command history
- [ ] Transcript persistence (JSONL)

### Phase 2: Tasks Dashboard + Approvals (Week 2-3)
- [ ] Task model and storage
- [ ] Tasks sidebar component
- [ ] Approval request system
- [ ] Approval modal in UI
- [ ] Cancel command functionality

### Phase 3: Settings + Profiles + Budgets (Week 3-4)
- [ ] User settings storage
- [ ] Settings page UI
- [ ] Agent profiles
- [ ] Finance Manager intake flow
- [ ] Budget enforcement middleware

### Phase 4: Cost Ledger + Janitor (Week 4-5)
- [ ] Cost entry model
- [ ] Cost tracking middleware
- [ ] Cost display widget
- [ ] Janitor background worker
- [ ] Daily/monthly reports

### Phase 5: Polish + Packaging (Week 5-6)
- [ ] Remove all default branding
- [ ] Error handling polish
- [ ] Performance optimization
- [ ] Documentation
- [ ] Package as installable skill

---

## 12) OPEN QUESTIONS

### 12.1 Clawdbot Internals

| Question | How to Discover | Fallback |
|----------|-----------------|----------|
| How does Clawdbot stream output internally? | Check `clawdbot/cli/agent.ts` or similar | Use subprocess + pty |
| What is the exact session storage format? | Inspect `~/.clawdbot/agents/main/sessions/sessions.json` | Reverse-engineer from file |
| How are tool calls logged? | Check gateway logs with `clawdbot logs --follow` | Parse from stdout |
| What triggers approval prompts? | Check `clawdbot/core/approvals.ts` | Match terminal behavior via testing |

### 12.2 Integration Points

| Question | Discovery Command | Fallback |
|----------|-------------------|----------|
| Gateway WebSocket protocol | `clawdbot gateway call --help` | Reverse-engineer with wireshark |
| Plugin loading mechanism | `clawdbot plugins doctor` | Skip plugins initially |
| Memory indexing format | `clawdbot memory status --verbose` | Use external search |

### 12.3 Assumptions Made

1. **Subprocess isolation is acceptable** — We spawn `clawdbot` as a subprocess rather than importing directly. Risk: Slightly higher latency. Mitigation: Profile and optimize if needed.

2. **JSONL transcripts are sufficient** — We use append-only JSONL files for transcripts. Risk: Large files over time. Mitigation: Implement rotation/archival.

3. **xterm.js provides terminal parity** — We assume xterm.js can replicate terminal behavior. Risk: Edge cases in escape codes. Mitigation: Golden tests.

---

## NEXT STEP

**What terminal commands are most important to match first (top 10)?**

My recommendation based on usage patterns:

1. `clawdbot agent -m "..." --deliver` — Primary agent interaction
2. `clawdbot status` — System health check
3. `clawdbot sessions` — Session management
4. `clawdbot message send` — Direct messaging
5. `clawdbot gateway status` — Gateway health
6. `clawdbot cron list/add/rm` — Scheduled tasks
7. `clawdbot config get/set` — Configuration
8. `clawdbot skills list` — Available skills
9. `clawdbot browser *` — Browser automation
10. `clawdbot logs` — Log viewing

Please confirm or adjust this priority list.
