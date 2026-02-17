# MyCasa Pro — Frontend Technical Stack

Based on [Homarr](https://github.com/homarr-labs/homarr) patterns.

## Stack

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **UI Library**: Mantine v7 (same as Homarr)
- **State**: Zustand or Jotai
- **Real-time**: WebSockets / Server-Sent Events
- **Icons**: Tabler Icons
- **Charts**: Recharts or Tremor

### Backend API
- **Runtime**: Python (FastAPI) — already exists
- **WebSocket**: FastAPI WebSockets for real-time events
- **Database**: SQLite (current) → PostgreSQL (production)

### Build & Deploy
- **Package Manager**: pnpm
- **Containerization**: Docker + Docker Compose
- **Dev**: Hot reload, TypeScript strict mode

---

## Directory Structure (Frontend)

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx           # Dashboard
│   ├── inbox/
│   ├── maintenance/
│   ├── finance/
│   ├── contractors/
│   ├── projects/
│   ├── security/
│   ├── logs/
│   └── settings/
├── components/
│   ├── widgets/           # Dashboard widgets
│   │   ├── SystemStatus.tsx
│   │   ├── AgentStatus.tsx
│   │   ├── LiveEvents.tsx
│   │   ├── TaskQueue.tsx
│   │   ├── Alerts.tsx
│   │   └── index.ts
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── Shell.tsx
│   └── ui/                # Shared components
├── hooks/
│   ├── useAgents.ts
│   ├── useEvents.ts
│   ├── useWebSocket.ts
│   └── useSettings.ts
├── lib/
│   ├── api.ts             # API client
│   ├── websocket.ts       # WS connection
│   └── utils.ts
├── stores/
│   ├── agents.ts
│   ├── events.ts
│   └── settings.ts
└── styles/
    └── globals.css
```

---

## Widget System (Homarr Pattern)

```typescript
// widgets/registry.ts
export const widgetRegistry = {
  'system-status': {
    component: SystemStatusWidget,
    defaultSize: { w: 2, h: 1 },
    minSize: { w: 1, h: 1 },
  },
  'agent-status': {
    component: AgentStatusWidget,
    defaultSize: { w: 2, h: 2 },
    lazyLoad: true,
  },
  'live-events': {
    component: LiveEventsWidget,
    defaultSize: { w: 1, h: 3 },
    realtime: true,
  },
  // ...
};
```

---

## Real-time Architecture

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   Browser   │ ◄───────────────► │   FastAPI   │
│  (Next.js)  │                    │   Backend   │
└─────────────┘                    └─────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │  Event Bus  │
                                   │   (Python)  │
                                   └─────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              ┌──────────┐         ┌──────────┐         ┌──────────┐
              │ Finance  │         │  Maint.  │         │ Security │
              │  Agent   │         │  Agent   │         │  Agent   │
              └──────────┘         └──────────┘         └──────────┘
```

---

## Migration Path

### Phase 1: API Layer
- [ ] Add FastAPI WebSocket endpoint for events
- [ ] Add REST endpoints for all agent operations
- [ ] Keep Streamlit running in parallel

### Phase 2: Frontend Shell
- [ ] Scaffold Next.js app
- [ ] Implement Sidebar + Layout
- [ ] Connect to existing API

### Phase 3: Widgets
- [ ] System Status
- [ ] Agent Status
- [ ] Live Events
- [ ] Task Queue
- [ ] Alerts

### Phase 4: Pages
- [ ] Dashboard (widget grid)
- [ ] Inbox
- [ ] Finance
- [ ] Settings

### Phase 5: Cutover
- [ ] Remove Streamlit
- [ ] Docker Compose with frontend + backend

---

## References

- Homarr source: https://github.com/homarr-labs/homarr
- Mantine UI: https://mantine.dev/
- Next.js: https://nextjs.org/
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
