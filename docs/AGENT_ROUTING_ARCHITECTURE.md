# MyCasa Pro: Agent Routing & Context Division Architecture

## Overview

This document outlines the implementation plan for intelligent agent orchestration with:
- **Per-persona context division** - Each agent gets optimized context based on its role
- **Per-request model routing** - Inspired by ClawRouter's weighted scoring system
- **Cost-optimized LLM selection** - Route to cheapest capable model per task

---

## 1. Architecture Principles

### From ClawRouter (Adapted)
- **14-dimension weighted scoring** for request complexity analysis
- **Tier-based routing**: SIMPLE → MEDIUM → COMPLEX → REASONING
- **Local routing decisions** (<1ms, no external API calls)
- **Per-request cost optimization**

### From MyCasa Pro (Existing)
- **Soccer team coordination model** - Manager orchestrates specialists
- **Persona-based agents** - Each agent has SOUL.md identity
- **Memory hierarchy** - SOUL → MEMORY.md → SecondBrain
- **Activity tracking** - Comprehensive audit trail

### Combined Approach
```
┌─────────────────────────────────────────────────────────────────┐
│                     MANAGER AGENT                                │
│  (Orchestrator - always uses claude-opus-4-5 for coordination)  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  ClawRouter     │     │  Per-Persona    │
│  Request Scorer │     │  Context        │
│  (local, <1ms)  │     │  Manager        │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           AGENT EXECUTION               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Finance │ │ Maint.  │ │Security │   │
│  │ Mamadou │ │ Ousmane │ │ Aicha   │   │
│  └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │         │
│  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐   │
│  │ Context │ │ Context │ │ Context │   │
│  │ Budget: │ │ Budget: │ │ Budget: │   │
│  │ 50k tok │ │ 30k tok │ │ 40k tok │   │
│  └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │         │
│  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐   │
│  │ Model:  │ │ Model:  │ │ Model:  │   │
│  │ Sonnet  │ │ Haiku   │ │ Sonnet  │   │
│  │ (routed)│ │ (routed)│ │ (routed)│   │
│  └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────┘
```

---

## 2. Request Routing System

### 2.1 Weighted Scoring Dimensions (Adapted from ClawRouter)

```python
SCORING_WEIGHTS = {
    # Reasoning indicators
    "reasoning_markers": 0.18,      # "prove", "analyze", "step by step", "why"
    "multi_step_patterns": 0.12,    # Sequential task indicators

    # Code & technical
    "code_presence": 0.15,          # Code blocks, programming keywords
    "technical_terms": 0.10,        # Domain-specific vocabulary

    # Complexity
    "token_count": 0.08,            # Request length as complexity proxy
    "constraint_count": 0.04,       # "must", "should", "ensure"
    "question_complexity": 0.05,    # Nested questions, conditionals

    # Simplicity indicators (negative weight)
    "simple_indicators": -0.12,     # "what is", "define", "list"

    # Domain-specific (MyCasa Pro)
    "financial_complexity": 0.08,   # Portfolio analysis, tax implications
    "maintenance_urgency": 0.04,    # "urgent", "emergency", "broken"
    "security_sensitivity": 0.06,   # PII, access control, threats

    # Creative/format
    "creative_markers": 0.05,       # "write", "compose", "design"
    "format_requirements": 0.03,    # Specific output format requests
}
```

### 2.2 Model Tiers

| Tier | Score Range | Primary Model | Fallback | Cost/1M tokens | Use Cases |
|------|-------------|---------------|----------|----------------|-----------|
| **SIMPLE** | 0.0 - 0.25 | claude-haiku-4-5 | gpt-4o-mini | $0.25 | Lookups, simple Q&A, status checks |
| **MEDIUM** | 0.25 - 0.55 | claude-3-5-sonnet | gpt-4o | $3.00 | Summaries, standard tasks, CRUD |
| **COMPLEX** | 0.55 - 0.80 | claude-sonnet-4 | claude-3-5-sonnet | $6.00 | Code, analysis, multi-step reasoning |
| **REASONING** | 0.80 - 1.0 | claude-opus-4-5 | o3 | $15.00 | Strategic decisions, complex analysis |

### 2.3 Agent-Specific Tier Adjustments

Each agent has a **base tier** that influences routing:

```python
AGENT_BASE_TIERS = {
    "manager": "REASONING",      # Always needs strategic thinking
    "finance": "COMPLEX",        # Financial analysis is nuanced
    "maintenance": "MEDIUM",     # Usually straightforward tasks
    "contractors": "MEDIUM",     # Scheduling, coordination
    "projects": "COMPLEX",       # Planning, dependencies
    "security-manager": "COMPLEX", # Threat analysis
    "janitor": "SIMPLE",         # Monitoring, cleanup
    "backup-recovery": "SIMPLE", # Automated operations
}

# Adjustment: agent_base_tier shifts the score by +/- 0.15
def adjust_score_for_agent(base_score: float, agent_id: str) -> float:
    tier = AGENT_BASE_TIERS.get(agent_id, "MEDIUM")
    adjustments = {"SIMPLE": -0.15, "MEDIUM": 0, "COMPLEX": 0.10, "REASONING": 0.20}
    return min(1.0, max(0.0, base_score + adjustments[tier]))
```

---

## 3. Per-Persona Context Division

### 3.1 Context Budget Allocation

Each agent gets a context budget based on their role complexity:

```python
AGENT_CONTEXT_BUDGETS = {
    # Agent ID: (max_tokens, soul_tokens, memory_tokens, secondbrain_limit)
    "manager": (100000, 2000, 5000, 10),      # Needs full context for coordination
    "finance": (50000, 1500, 3000, 5),        # Financial analysis needs detail
    "maintenance": (30000, 1000, 2000, 3),    # Task-focused, less context needed
    "contractors": (30000, 1000, 2000, 3),    # Similar to maintenance
    "projects": (40000, 1500, 3000, 5),       # Project planning needs history
    "security-manager": (40000, 1500, 2500, 5), # Threat context important
    "janitor": (20000, 500, 1000, 2),         # Minimal context, focused tasks
    "backup-recovery": (15000, 500, 500, 1),  # Very focused operations
}
```

### 3.2 Context Building Strategy

```python
class ContextStrategy(Enum):
    FULL = "full"           # Include everything within budget
    ADAPTIVE = "adaptive"   # Include based on request relevance
    MINIMAL = "minimal"     # Only essential context
    CACHED = "cached"       # Use cached context when possible

AGENT_CONTEXT_STRATEGIES = {
    "manager": ContextStrategy.FULL,
    "finance": ContextStrategy.ADAPTIVE,
    "maintenance": ContextStrategy.MINIMAL,
    "contractors": ContextStrategy.MINIMAL,
    "projects": ContextStrategy.ADAPTIVE,
    "security-manager": ContextStrategy.ADAPTIVE,
    "janitor": ContextStrategy.MINIMAL,
    "backup-recovery": ContextStrategy.CACHED,
}
```

### 3.3 Memory Inclusion Rules

```python
@dataclass
class MemoryConfig:
    include_soul: bool = True
    soul_max_chars: int = 2000

    include_memory: bool = True
    memory_days: int = 7          # Only include last N days
    memory_max_chars: int = 3000

    include_secondbrain: bool = True
    secondbrain_limit: int = 5    # Max recalled items
    secondbrain_relevance: float = 0.7  # Min similarity threshold

    include_recent_activity: bool = True
    activity_limit: int = 10      # Last N activities

# Per-agent configurations
AGENT_MEMORY_CONFIGS = {
    "manager": MemoryConfig(
        soul_max_chars=3000,
        memory_days=14,
        memory_max_chars=5000,
        secondbrain_limit=10,
        activity_limit=20
    ),
    "finance": MemoryConfig(
        memory_days=30,  # Financial history is important
        memory_max_chars=4000,
        secondbrain_limit=5
    ),
    "maintenance": MemoryConfig(
        memory_days=7,
        memory_max_chars=2000,
        secondbrain_limit=3
    ),
    # ... etc
}
```

---

## 4. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

#### 4.1 Create Request Scorer

**File**: `core/request_scorer.py`

```python
"""
ClawRouter-inspired request complexity scorer.
Runs locally in <1ms, no API calls.
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class ModelTier(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    REASONING = "reasoning"

@dataclass
class ScoringResult:
    score: float
    tier: ModelTier
    confidence: float
    factors: Dict[str, float]
    recommended_model: str

class RequestScorer:
    """Weighted multi-dimension request scorer."""

    WEIGHTS = {
        "reasoning_markers": 0.18,
        "code_presence": 0.15,
        "simple_indicators": -0.12,
        "multi_step_patterns": 0.12,
        "technical_terms": 0.10,
        "token_count": 0.08,
        "financial_complexity": 0.08,
        "security_sensitivity": 0.06,
        "creative_markers": 0.05,
        "question_complexity": 0.05,
        "maintenance_urgency": 0.04,
        "constraint_count": 0.04,
        "format_requirements": 0.03,
    }

    REASONING_MARKERS = [
        r"\bprove\b", r"\btheorem\b", r"\bstep by step\b", r"\banalyze\b",
        r"\bwhy\b.*\?", r"\bexplain.*reasoning\b", r"\bevaluate\b"
    ]

    CODE_INDICATORS = [
        r"```", r"\bfunction\b", r"\bclass\b", r"\bdef\b", r"\breturn\b",
        r"\bimport\b", r"\bconst\b", r"\blet\b", r"\bvar\b"
    ]

    SIMPLE_INDICATORS = [
        r"^what is\b", r"^define\b", r"^list\b", r"^who is\b",
        r"^when\b", r"^where\b", r"^how many\b"
    ]

    def score(self, request: str, agent_id: Optional[str] = None) -> ScoringResult:
        """Score a request and return routing recommendation."""
        factors = {}

        # Calculate each dimension
        factors["reasoning_markers"] = self._score_reasoning(request)
        factors["code_presence"] = self._score_code(request)
        factors["simple_indicators"] = self._score_simple(request)
        factors["multi_step_patterns"] = self._score_multi_step(request)
        factors["technical_terms"] = self._score_technical(request)
        factors["token_count"] = self._score_length(request)
        factors["financial_complexity"] = self._score_financial(request)
        factors["security_sensitivity"] = self._score_security(request)
        factors["creative_markers"] = self._score_creative(request)
        factors["question_complexity"] = self._score_question_complexity(request)
        factors["maintenance_urgency"] = self._score_urgency(request)
        factors["constraint_count"] = self._score_constraints(request)
        factors["format_requirements"] = self._score_format(request)

        # Weighted sum
        raw_score = sum(
            factors[k] * self.WEIGHTS[k]
            for k in factors
        )

        # Normalize to 0-1
        score = max(0.0, min(1.0, (raw_score + 0.5)))

        # Apply agent adjustment
        if agent_id:
            score = self._adjust_for_agent(score, agent_id)

        # Determine tier
        tier = self._score_to_tier(score)

        # Special rule: 2+ reasoning markers → REASONING
        if factors["reasoning_markers"] >= 0.6:
            tier = ModelTier.REASONING
            score = max(score, 0.85)

        return ScoringResult(
            score=score,
            tier=tier,
            confidence=self._calculate_confidence(factors),
            factors=factors,
            recommended_model=self._tier_to_model(tier)
        )

    def _score_reasoning(self, text: str) -> float:
        matches = sum(1 for p in self.REASONING_MARKERS if re.search(p, text, re.I))
        return min(1.0, matches / 3)

    def _score_code(self, text: str) -> float:
        matches = sum(1 for p in self.CODE_INDICATORS if re.search(p, text))
        return min(1.0, matches / 4)

    def _score_simple(self, text: str) -> float:
        for pattern in self.SIMPLE_INDICATORS:
            if re.match(pattern, text.strip(), re.I):
                return 1.0
        return 0.0

    def _score_multi_step(self, text: str) -> float:
        indicators = [r"\bfirst\b.*\bthen\b", r"\bstep \d", r"\b\d\.\s", r"\band then\b"]
        matches = sum(1 for p in indicators if re.search(p, text, re.I))
        return min(1.0, matches / 2)

    def _score_technical(self, text: str) -> float:
        terms = [r"\bAPI\b", r"\bdatabase\b", r"\bschema\b", r"\balgorithm\b",
                 r"\bportfolio\b", r"\bROI\b", r"\byield\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_length(self, text: str) -> float:
        # Longer requests often more complex
        tokens = len(text.split())
        if tokens < 20: return 0.0
        if tokens < 50: return 0.3
        if tokens < 100: return 0.5
        if tokens < 200: return 0.7
        return 1.0

    def _score_financial(self, text: str) -> float:
        terms = [r"\btax\b", r"\binvest", r"\bportfolio\b", r"\bstock\b",
                 r"\bdividend\b", r"\bcapital gain", r"\brebalance\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_security(self, text: str) -> float:
        terms = [r"\bpassword\b", r"\bsecure\b", r"\bthreat\b", r"\baccess\b",
                 r"\bencrypt\b", r"\bvulnerab", r"\bpermission\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_creative(self, text: str) -> float:
        terms = [r"\bwrite\b", r"\bcompose\b", r"\bdesign\b", r"\bcreate\b", r"\bdraft\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 2)

    def _score_question_complexity(self, text: str) -> float:
        questions = text.count("?")
        conditionals = len(re.findall(r"\bif\b.*\bthen\b", text, re.I))
        return min(1.0, (questions + conditionals) / 3)

    def _score_urgency(self, text: str) -> float:
        terms = [r"\burgent\b", r"\bemergency\b", r"\bbroken\b", r"\basap\b", r"\bimmediately\b"]
        return 1.0 if any(re.search(t, text, re.I) for t in terms) else 0.0

    def _score_constraints(self, text: str) -> float:
        terms = [r"\bmust\b", r"\bshould\b", r"\bensure\b", r"\brequire\b", r"\bneed to\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_format(self, text: str) -> float:
        terms = [r"\bjson\b", r"\bmarkdown\b", r"\bformat as\b", r"\breturn as\b", r"\blist of\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 2)

    def _adjust_for_agent(self, score: float, agent_id: str) -> float:
        adjustments = {
            "manager": 0.20,
            "finance": 0.10,
            "maintenance": 0.0,
            "contractors": 0.0,
            "projects": 0.10,
            "security-manager": 0.10,
            "janitor": -0.15,
            "backup-recovery": -0.15,
        }
        adj = adjustments.get(agent_id, 0.0)
        return max(0.0, min(1.0, score + adj))

    def _score_to_tier(self, score: float) -> ModelTier:
        if score < 0.25: return ModelTier.SIMPLE
        if score < 0.55: return ModelTier.MEDIUM
        if score < 0.80: return ModelTier.COMPLEX
        return ModelTier.REASONING

    def _tier_to_model(self, tier: ModelTier) -> str:
        models = {
            ModelTier.SIMPLE: "claude-haiku-4-5",
            ModelTier.MEDIUM: "claude-3-5-sonnet-20241022",
            ModelTier.COMPLEX: "claude-sonnet-4-20250514",
            ModelTier.REASONING: "claude-opus-4-5-20251101",
        }
        return models[tier]

    def _calculate_confidence(self, factors: Dict[str, float]) -> float:
        # Higher variance = lower confidence
        values = list(factors.values())
        if not values:
            return 0.5
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return max(0.5, 1.0 - variance)


# Singleton instance
_scorer = None

def get_request_scorer() -> RequestScorer:
    global _scorer
    if _scorer is None:
        _scorer = RequestScorer()
    return _scorer
```

#### 4.2 Create Context Manager

**File**: `core/agent_context_manager.py`

```python
"""
Per-agent context division and management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import tiktoken

class ContextStrategy(Enum):
    FULL = "full"
    ADAPTIVE = "adaptive"
    MINIMAL = "minimal"
    CACHED = "cached"

@dataclass
class MemoryConfig:
    include_soul: bool = True
    soul_max_chars: int = 2000
    include_memory: bool = True
    memory_days: int = 7
    memory_max_chars: int = 3000
    include_secondbrain: bool = True
    secondbrain_limit: int = 5
    secondbrain_relevance: float = 0.7
    include_recent_activity: bool = True
    activity_limit: int = 10

@dataclass
class ContextBudget:
    max_tokens: int
    soul_tokens: int
    memory_tokens: int
    secondbrain_limit: int

AGENT_BUDGETS: Dict[str, ContextBudget] = {
    "manager": ContextBudget(100000, 2000, 5000, 10),
    "finance": ContextBudget(50000, 1500, 3000, 5),
    "maintenance": ContextBudget(30000, 1000, 2000, 3),
    "contractors": ContextBudget(30000, 1000, 2000, 3),
    "projects": ContextBudget(40000, 1500, 3000, 5),
    "security-manager": ContextBudget(40000, 1500, 2500, 5),
    "janitor": ContextBudget(20000, 500, 1000, 2),
    "backup-recovery": ContextBudget(15000, 500, 500, 1),
}

AGENT_STRATEGIES: Dict[str, ContextStrategy] = {
    "manager": ContextStrategy.FULL,
    "finance": ContextStrategy.ADAPTIVE,
    "maintenance": ContextStrategy.MINIMAL,
    "contractors": ContextStrategy.MINIMAL,
    "projects": ContextStrategy.ADAPTIVE,
    "security-manager": ContextStrategy.ADAPTIVE,
    "janitor": ContextStrategy.MINIMAL,
    "backup-recovery": ContextStrategy.CACHED,
}

class AgentContextManager:
    """Manages context division and budget allocation per agent."""

    def __init__(self):
        self._context_cache: Dict[str, str] = {}
        self._token_usage: Dict[str, int] = {}
        try:
            self._encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._encoder = None

    def get_budget(self, agent_id: str) -> ContextBudget:
        """Get context budget for an agent."""
        return AGENT_BUDGETS.get(agent_id, ContextBudget(30000, 1000, 2000, 3))

    def get_strategy(self, agent_id: str) -> ContextStrategy:
        """Get context strategy for an agent."""
        return AGENT_STRATEGIES.get(agent_id, ContextStrategy.ADAPTIVE)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._encoder:
            return len(self._encoder.encode(text))
        # Fallback: rough estimate
        return len(text) // 4

    def build_context(
        self,
        agent_id: str,
        base_prompt: str,
        soul: str,
        memory: str,
        secondbrain_results: List[Dict],
        recent_activity: Optional[List[Dict]] = None,
        request: Optional[str] = None,
    ) -> str:
        """
        Build optimized context for an agent based on their budget and strategy.
        """
        budget = self.get_budget(agent_id)
        strategy = self.get_strategy(agent_id)

        # Check cache for static content
        if strategy == ContextStrategy.CACHED:
            cache_key = f"{agent_id}:base"
            if cache_key in self._context_cache:
                cached = self._context_cache[cache_key]
                return cached + f"\n\n## Current Request\n{request or ''}"

        parts = [base_prompt]
        tokens_used = self.count_tokens(base_prompt)

        # Add soul (identity)
        if soul:
            soul_tokens = self.count_tokens(soul)
            if soul_tokens > budget.soul_tokens:
                # Truncate soul to budget
                soul = self._truncate_to_tokens(soul, budget.soul_tokens)
            parts.append(f"## Your Identity\n{soul}")
            tokens_used += self.count_tokens(soul)

        # Add memory based on strategy
        if memory and strategy != ContextStrategy.MINIMAL:
            memory_budget = budget.memory_tokens
            if strategy == ContextStrategy.ADAPTIVE and request:
                # Only include relevant memory sections
                memory = self._filter_relevant_memory(memory, request)

            memory_tokens = self.count_tokens(memory)
            if memory_tokens > memory_budget:
                memory = self._truncate_to_tokens(memory, memory_budget)

            parts.append(f"## Your Memory\n{memory}")
            tokens_used += self.count_tokens(memory)

        # Add SecondBrain results
        if secondbrain_results and budget.secondbrain_limit > 0:
            limited = secondbrain_results[:budget.secondbrain_limit]
            if limited:
                recalls = "\n".join(
                    f"- **{r.get('title', 'Note')}**: {r.get('snippet', r.get('content', ''))[:200]}"
                    for r in limited
                )
                parts.append(f"## Relevant Knowledge\n{recalls}")
                tokens_used += self.count_tokens(recalls)

        # Add recent activity for context (if budget allows)
        if recent_activity and strategy == ContextStrategy.FULL:
            activity_text = "\n".join(
                f"- {a.get('timestamp', '')}: {a.get('action', '')} - {a.get('result', '')[:100]}"
                for a in recent_activity[:10]
            )
            if tokens_used + self.count_tokens(activity_text) < budget.max_tokens:
                parts.append(f"## Recent Activity\n{activity_text}")

        context = "\n\n".join(parts)

        # Cache if strategy calls for it
        if strategy == ContextStrategy.CACHED:
            self._context_cache[f"{agent_id}:base"] = context

        # Track usage
        self._token_usage[agent_id] = self.count_tokens(context)

        return context

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget."""
        if self._encoder:
            tokens = self._encoder.encode(text)
            if len(tokens) <= max_tokens:
                return text
            return self._encoder.decode(tokens[:max_tokens]) + "..."
        # Fallback: char-based truncation
        max_chars = max_tokens * 4
        return text[:max_chars] + "..." if len(text) > max_chars else text

    def _filter_relevant_memory(self, memory: str, request: str) -> str:
        """Filter memory to only include sections relevant to the request."""
        # Simple keyword-based filtering
        request_words = set(request.lower().split())

        sections = memory.split("\n## ")
        relevant = []

        for section in sections:
            section_words = set(section.lower().split())
            overlap = len(request_words & section_words)
            if overlap >= 2 or not sections:  # Include if 2+ word overlap
                relevant.append(section)

        return "\n## ".join(relevant) if relevant else memory[:2000]

    def get_token_usage(self, agent_id: str) -> int:
        """Get last recorded token usage for an agent."""
        return self._token_usage.get(agent_id, 0)

    def clear_cache(self, agent_id: Optional[str] = None):
        """Clear context cache."""
        if agent_id:
            keys_to_remove = [k for k in self._context_cache if k.startswith(agent_id)]
            for k in keys_to_remove:
                del self._context_cache[k]
        else:
            self._context_cache.clear()


# Singleton
_manager = None

def get_context_manager() -> AgentContextManager:
    global _manager
    if _manager is None:
        _manager = AgentContextManager()
    return _manager
```

### Phase 2: Integration (Week 2)

#### 4.3 Update LLM Client

**File**: `core/llm_client.py` - Add routing integration

```python
# Add to existing LLMClient class

async def chat_routed(
    self,
    agent_id: str,
    system_prompt: str,
    user_message: str,
    force_model: Optional[str] = None,
    **kwargs
) -> Tuple[str, Dict[str, Any]]:
    """
    Chat with automatic model routing based on request complexity.
    Returns (response, metadata) where metadata includes routing info.
    """
    from core.request_scorer import get_request_scorer

    # Score the request
    scorer = get_request_scorer()
    scoring = scorer.score(user_message, agent_id)

    # Determine model
    model = force_model or scoring.recommended_model

    # Make the call
    response = await self.chat(
        system_prompt=system_prompt,
        user_message=user_message,
        model=model,
        **kwargs
    )

    metadata = {
        "model_used": model,
        "routing": {
            "score": scoring.score,
            "tier": scoring.tier.value,
            "confidence": scoring.confidence,
            "factors": scoring.factors,
        }
    }

    return response, metadata
```

#### 4.4 Update BaseAgent

**File**: `agents/base.py` - Integrate context manager and routing

```python
# Add to BaseAgent.chat() method

async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Chat with automatic context building and model routing."""
    from core.agent_context_manager import get_context_manager
    from core.llm_client import get_llm_client

    # Load agent identity and memory
    soul = self._load_soul()
    memory = self._load_memory()
    secondbrain_results = await self._recall_from_secondbrain(message)

    # Build optimized context
    ctx_mgr = get_context_manager()
    system_prompt = ctx_mgr.build_context(
        agent_id=self.name,
        base_prompt=self._get_base_prompt(),
        soul=soul,
        memory=memory,
        secondbrain_results=secondbrain_results,
        recent_activity=self._get_recent_activity(),
        request=message,
    )

    # Get LLM client and make routed call
    llm = get_llm_client()
    response, metadata = await llm.chat_routed(
        agent_id=self.name,
        system_prompt=system_prompt,
        user_message=message,
    )

    # Log routing decision for telemetry
    self._log_activity({
        "action": "llm_call",
        "model": metadata["model_used"],
        "routing": metadata["routing"],
        "context_tokens": ctx_mgr.get_token_usage(self.name),
    })

    return response
```

### Phase 3: Configuration & UI (Week 3)

#### 4.5 Update Settings Schema

**File**: `core/settings_typed.py` - Add LLM config per agent

```python
class AgentLLMConfig(BaseModel):
    """LLM configuration for an agent."""
    default_model: Optional[str] = None  # Override default routing
    max_tier: str = "reasoning"  # Cap the maximum tier
    temperature: float = 0.7
    thinking_mode: Optional[str] = None  # "extended", "medium", "fast"
    context_strategy: str = "adaptive"  # "full", "adaptive", "minimal"

class AgentSettings(BaseModel):
    """Base class for agent settings."""
    enabled: bool = True
    notification_channel: NotificationChannel = NotificationChannel.INAPP
    llm_config: AgentLLMConfig = Field(default_factory=AgentLLMConfig)
```

#### 4.6 Add Routing Dashboard to UI

**File**: `frontend/src/app/settings/page.tsx` - Add routing config section

```tsx
// Add to Agents tab - per-agent model configuration
<Card withBorder p="lg" radius="md">
  <Text fw={600} mb="md">Model Routing Configuration</Text>
  <Stack gap="md">
    <Select
      label="Default Model Tier"
      description="Maximum model tier this agent can use"
      data={[
        { value: "simple", label: "Simple (Haiku) - Fast & cheap" },
        { value: "medium", label: "Medium (Sonnet 3.5) - Balanced" },
        { value: "complex", label: "Complex (Sonnet 4) - Capable" },
        { value: "reasoning", label: "Reasoning (Opus) - Most powerful" },
      ]}
      defaultValue="complex"
    />
    <Select
      label="Context Strategy"
      description="How much context to include in requests"
      data={[
        { value: "minimal", label: "Minimal - Fast, less context" },
        { value: "adaptive", label: "Adaptive - Relevant context only" },
        { value: "full", label: "Full - Include all available context" },
      ]}
      defaultValue="adaptive"
    />
    <NumberInput
      label="Temperature"
      description="Response creativity (0.0 = deterministic, 1.0 = creative)"
      min={0}
      max={1}
      step={0.1}
      defaultValue={0.7}
    />
  </Stack>
</Card>
```

---

## 5. Cost Optimization Projections

| Agent | Current Cost/Call | Optimized Cost/Call | Savings |
|-------|-------------------|---------------------|---------|
| Manager | $0.015 (Opus) | $0.015 (Opus) | 0% (needs reasoning) |
| Finance | $0.015 (Opus) | $0.006 (Sonnet) | 60% |
| Maintenance | $0.015 (Opus) | $0.0003 (Haiku) | 98% |
| Contractors | $0.015 (Opus) | $0.0003 (Haiku) | 98% |
| Projects | $0.015 (Opus) | $0.006 (Sonnet) | 60% |
| Security | $0.015 (Opus) | $0.006 (Sonnet) | 60% |
| Janitor | $0.015 (Opus) | $0.0003 (Haiku) | 98% |
| Backup | $0.015 (Opus) | $0.0003 (Haiku) | 98% |

**Average savings: 70%+** while maintaining quality for complex tasks.

---

## 6. Files to Create/Modify

### New Files
1. `core/request_scorer.py` - ClawRouter-inspired scoring
2. `core/agent_context_manager.py` - Per-agent context division
3. `docs/AGENT_ROUTING_ARCHITECTURE.md` - This document

### Modified Files
1. `core/llm_client.py` - Add `chat_routed()` method
2. `agents/base.py` - Integrate context manager and routing
3. `core/settings_typed.py` - Add LLM config to agent settings
4. `frontend/src/app/settings/page.tsx` - Routing configuration UI
5. `agents/persona_registry.py` - Add `llm_config` to persona definition

---

## 7. Testing Strategy

```bash
# Unit tests
pytest tests/unit/test_request_scorer.py -v
pytest tests/unit/test_context_manager.py -v

# Integration tests
pytest tests/integration/test_agent_routing.py -v

# Benchmark routing speed
python -m core.request_scorer --benchmark

# Verify cost savings
python scripts/analyze_routing_costs.py --period=7d
```

---

## Summary

This architecture combines:
1. **ClawRouter's** weighted scoring for intelligent per-request model selection
2. **MyCasa Pro's** persona-based agent system with optimized context division
3. **Cost optimization** through automatic routing to cheapest capable model
4. **Quality preservation** through agent-specific tier adjustments

The result is a system where each agent gets exactly the context and model capability it needs, minimizing costs while maximizing effectiveness.
