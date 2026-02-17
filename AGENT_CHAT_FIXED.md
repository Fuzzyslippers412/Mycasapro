# Agent Chat Fix - LLM Integration

## What Was Broken

All agents had **hardcoded pattern-matching responses** instead of using the LLM to generate intelligent responses based on their personas.

Example from security_manager.py:
```python
if "incident" in message:
    return "🛡️ **No Active Incidents**..."  # Hardcoded!
```

## What Was Fixed

### 1. Created LLM Client (`core/llm_client.py`)
- Centralized Anthropic Claude API client
- Handles authentication, error handling, and retry logic
- Supports conversation history

### 2. Updated Base Agent (`agents/base.py`)
The `chat()` method now:
- Loads agent's system prompt from `agent_prompts.py`
- Loads agent's SOUL.md (persona/identity)
- Loads agent's MEMORY.md (long-term memory)
- Recalls relevant context from SecondBrain
- **Calls Claude API** to generate intelligent responses
- Fallback if LLM unavailable

### 3. Removed Hardcoded Chat Overrides
Deleted hardcoded `chat()` methods from all agents:
- ✓ contractors.py
- ✓ finance.py
- ✓ janitor.py
- ✓ maintenance.py
- ✓ manager.py
- ✓ projects.py
- ✓ security_manager.py

### 4. Added Dependencies
- Added `anthropic` to requirements.txt

## How to Use

### 1. Install Dependencies
```bash
cd ~/clawd/apps/mycasa-pro
pip install anthropic
```

### 2. Set API Key
Add to `.env` file or export:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or add to `~/clawd/apps/mycasa-pro/.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Test an Agent
```bash
# Via API
curl -X POST http://localhost:8501/agents/security/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What security threats should I be aware of?"}'
```

## How It Works Now

When you chat with an agent:

1. **System Prompt**: Agent's role/personality from `agent_prompts.py`
2. **SOUL.md**: Agent's identity and objectives
3. **MEMORY.md**: Agent's long-term curated memory
4. **SecondBrain**: Recalls relevant notes/entities/decisions
5. **Claude API**: Generates response in agent's persona
6. **Response**: Natural, contextual reply

## Agent Personas

Each agent has a distinct persona defined in `core/agent_prompts.py`:
- **Finance Agent**: Analytical, risk-aware, data-driven
- **Maintenance Agent**: Practical, organized, proactive
- **Security Manager (Aïcha)**: Vigilant, protective, transparent
- **Contractors Agent**: Relationship-focused, evaluative
- **Projects Agent**: Organized, timeline-focused
- **Manager (Galidima)**: Supervisory, truthful, coordinating
- **Janitor Agent**: Systematic, health-conscious, efficient

## Fallback Behavior

If Claude API is unavailable:
- Agent returns informative message about LLM not being configured
- No crash or error thrown
- User is notified to set ANTHROPIC_API_KEY

## Cost Optimization

Default settings:
- Model: `claude-opus-4-5` (best quality)
- Max tokens: 2048
- Temperature: 1.0

To reduce costs, edit `core/llm_client.py`:
- Change model to `claude-sonnet-4` or `claude-haiku-4`
- Reduce `max_tokens`

## Testing

Test that agents now respond with intelligence:

```python
from agents.security_manager import SecurityManagerAgent
import asyncio

async def test():
    agent = SecurityManagerAgent()
    response = await agent.chat("What security threats should I monitor?")
    print(response)

asyncio.run(test())
```

Should now return an intelligent response about security threats, not a hardcoded pattern match!
