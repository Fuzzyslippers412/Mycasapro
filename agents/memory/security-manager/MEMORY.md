---
type: workspace
agent: security-manager
file: MEMORY
---
# MEMORY.md — Security-Manager Agent Long-Term Memory

## Approved Egress Allowlist

| Domain | Protocol | Purpose | Approved By | Date |
|--------|----------|---------|-------------|------|
| api.anthropic.com | HTTPS | LLM API | Lamido | 2026-01-28 |

---

## Approved Listeners

| Port | Service | Binding | Auth | TLS | Approved |
|------|---------|---------|------|-----|----------|
| 8501 | Streamlit UI | 127.0.0.1 | None (local) | No | Default |

---

## Secrets Inventory

| Secret | Storage | Rotation | Last Verified |
|--------|---------|----------|---------------|
| ANTHROPIC_API_KEY | env var | Manual | PENDING |

---

## Dependency Audit Log

<!-- Track dependency checks and updates -->

---

## Security Incidents

<!-- Append incidents for pattern detection -->

---

## Hardening Backlog

| Priority | Item | Status | Notes |
|----------|------|--------|-------|
| P2 | Enable HTTPS for Streamlit | Pending | Requires cert setup |
| P3 | Add egress firewall rules | Pending | macOS pf config |

---

## Local-Only Migration Checklist

- [ ] Identify local model candidate (llama.cpp, ollama, etc.)
- [ ] Document API compatibility layer requirements
- [ ] Plan tool permission parity
- [ ] Design offline fallback behavior
- [ ] Create validation test suite
