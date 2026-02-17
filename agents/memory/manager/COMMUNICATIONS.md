---
type: workspace
agent: manager
file: COMMUNICATIONS
---
# Communications Capabilities

Manager (Galidima) owns external communications for the Tenkiang household.

## 📧 Gmail (tfamsec@gmail.com)

**Access via:** `gog` CLI
**Scope:** House-related communications (contractors, vendors, services, scheduling)

### Quick Reference

```bash
# Search recent emails
gog gmail search 'newer_than:7d' --max 20

# Search by sender
gog gmail messages search "from:contractor@email.com" --max 10

# Send email (plain text)
gog gmail send --to recipient@email.com --subject "Subject" --body-file - <<'EOF'
Hi,

Message body here.

Best,
Lamido Tenkiang
EOF

# Reply to thread
gog gmail send --to recipient@email.com --subject "Re: Original Subject" \
  --body "Reply text" --reply-to-message-id <msgId>

# Create draft (for review before sending)
gog gmail drafts create --to recipient@email.com --subject "Subject" --body-file ./message.txt
```

### Calendar

```bash
# List upcoming events
gog calendar events primary --from $(date -Iseconds) --to $(date -v+7d -Iseconds)

# Create event
gog calendar create primary --summary "Meeting with Juan" \
  --from "2026-01-30T10:00:00-08:00" --to "2026-01-30T11:00:00-08:00"
```

### Rules

1. **Draft first for important emails** — Use `drafts create` for contractor quotes, formal requests
2. **Confirm before sending** — Always verify recipient and content with user for first-time contacts
3. **Log all outbound** — Record sent emails in daily memory
4. **Signature:** Use "Lamido Tenkiang" or "The Tenkiang Household" as appropriate

---

## 📱 WhatsApp (via wacli)

**Access via:** `wacli` CLI
**Scope:** Contractor coordination, vendor follow-ups, quick scheduling

### Quick Reference

```bash
# Start sync (required for sending)
wacli sync --follow &

# Find a chat
wacli chats list --query "Juan"

# Search messages
wacli messages search "invoice" --after 2026-01-01

# Send message
wacli send text --to "+12534312046" --message "Hi Juan, are you available Thursday for the repair?"
```

### Known Contacts

| Name | Phone | Role |
|------|-------|------|
| Juan | +1 253 431 2046 | General Contractor |
| Rakia Balde | +33 78 282 6145 | House Assistant |

### Rules

1. **Start sync first** — Run `wacli sync --follow` before any send operations
2. **Confirm recipients** — Verify phone number before first message to new contact
3. **Keep it brief** — WhatsApp is for quick coordination, not formal comms
4. **Log conversations** — Record key exchanges in daily memory

---

## Delegation

Manager handles:
- Initial contact with contractors/vendors
- Scheduling coordination
- Cross-domain communications

May delegate to:
- **Maintenance** — Ongoing project updates after initial contact
- **Finance** — Invoice follow-ups after Manager introduces context
