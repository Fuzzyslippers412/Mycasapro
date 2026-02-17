# Inbox Integration — Implementation Notes

## Message Sources

### WhatsApp Messages (via wacli)

**CLI Tool**: `wacli` (WhatsApp CLI)

**Commands**:
```bash
# List chats
wacli chats list

# Get messages from a chat
wacli messages list "Chat Name" --limit 20

# Search messages
wacli messages search "query"

# Check status
wacli doctor
```

**Note**: wacli sync must be stopped before reading (`pkill -f wacli`). For sending, use `wacli send text --to "+15551234567" --message "Hi"` once authenticated.

**Integration Pattern**:
1. Backend polls wacli periodically for new messages
2. Normalize message format: `{ source: "whatsapp", sender, timestamp, body, chatId }`
3. Push to Inbox via WebSocket
4. Link to domain if sender is known contact

---

### Gmail Messages (via gog)

**CLI Tool**: `gog` (Google Workspace CLI)

**Account**: your@gmail.com

**Commands**:
```bash
# Search recent emails
gog gmail search 'newer_than:7d' --max 20

# Get specific message
gog gmail get <message_id>

# List labels
gog gmail labels
```

**Integration Pattern**:
1. Backend polls gog periodically for new emails
2. Normalize message format: `{ source: "gmail", sender, subject, timestamp, snippet, messageId }`
3. Push to Inbox via WebSocket
4. Categorize by sender domain or labels

---

## Inbox Data Model

```typescript
interface InboxMessage {
  id: string;
  source: "whatsapp" | "gmail" | "system";
  sender: string;
  senderName?: string;
  subject?: string;        // Gmail only
  body: string;
  timestamp: string;       // ISO 8601
  read: boolean;
  linkedDomain?: string;   // "finance" | "maintenance" | "contractors" | etc.
  suggestedActions?: Action[];
  metadata: Record<string, any>;
}

interface Action {
  type: "approve" | "reply" | "assign" | "archive" | "delete";
  label: string;
  payload?: any;
}
```

---

## Backend API Endpoints

```
GET  /api/inbox              # List messages (paginated)
GET  /api/inbox/:id          # Get single message
POST /api/inbox/:id/action   # Execute action on message
POST /api/inbox/:id/read     # Mark as read
POST /api/inbox/sync         # Trigger manual sync
WS   /api/inbox/stream       # Real-time updates
```

---

## Frontend Components

```
src/app/inbox/
├── page.tsx                 # Main inbox page
├── components/
│   ├── MessageList.tsx      # Virtualized message list
│   ├── MessageItem.tsx      # Single message row
│   ├── MessageDetail.tsx    # Expanded message view
│   ├── ActionBar.tsx        # Quick actions
│   └── SourceBadge.tsx      # WhatsApp/Gmail/System badge
```

---

## Sync Strategy

1. **Polling Interval**: Every 60 seconds for both sources
2. **On-demand**: Manual refresh button
3. **WebSocket**: Push new messages immediately when detected
4. **Deduplication**: Hash of (source + messageId + timestamp)

---

## Known Contacts (for domain linking)

From TOOLS.md:
- Erika Tenkiang (Wife): +12675474854 → personal
- Jessie Tenkiang (Mother): +13027501982 → personal
- Rakia Baldé (House Assistant): +33782826145 → maintenance/contractors
- Juan (Contractor): +12534312046 → contractors

Auto-link messages from known contacts to appropriate domain.
