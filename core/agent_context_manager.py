"""
Per-agent context division and management.

Manages context budgets, memory inclusion, and caching strategies
for each agent persona.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import re


class ContextStrategy(Enum):
    """Strategy for building agent context."""
    FULL = "full"           # Include everything within budget
    ADAPTIVE = "adaptive"   # Include based on request relevance
    MINIMAL = "minimal"     # Only essential context
    CACHED = "cached"       # Use cached context when possible


@dataclass
class ContextBudget:
    """Token budget allocation for an agent."""
    max_tokens: int          # Total context window limit
    soul_tokens: int         # Budget for persona identity
    memory_tokens: int       # Budget for long-term memory
    secondbrain_limit: int   # Max SecondBrain recall items


@dataclass
class MemoryConfig:
    """Memory inclusion configuration."""
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


# Default context budgets per agent
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

# Default context strategies per agent
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

# Default memory configs per agent
AGENT_MEMORY_CONFIGS: Dict[str, MemoryConfig] = {
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
    "contractors": MemoryConfig(
        memory_days=14,
        memory_max_chars=2000,
        secondbrain_limit=3
    ),
    "projects": MemoryConfig(
        memory_days=30,
        memory_max_chars=3000,
        secondbrain_limit=5
    ),
    "security-manager": MemoryConfig(
        memory_days=7,
        memory_max_chars=2500,
        secondbrain_limit=5
    ),
    "janitor": MemoryConfig(
        memory_days=3,
        memory_max_chars=1000,
        secondbrain_limit=2,
        include_recent_activity=False
    ),
    "backup-recovery": MemoryConfig(
        memory_days=1,
        memory_max_chars=500,
        secondbrain_limit=1,
        include_recent_activity=False
    ),
}


class AgentContextManager:
    """
    Manages context division and budget allocation per agent.

    Responsibilities:
    - Allocate context budgets per agent
    - Build optimized system prompts
    - Track token usage
    - Manage context caching
    """

    def __init__(self):
        self._context_cache: Dict[str, str] = {}
        self._token_usage: Dict[str, int] = {}
        self._encoder = None

        # Try to load tiktoken for accurate token counting
        try:
            import tiktoken
            self._encoder = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            pass

    def get_budget(self, agent_id: str) -> ContextBudget:
        """Get context budget for an agent."""
        return AGENT_BUDGETS.get(
            agent_id,
            ContextBudget(30000, 1000, 2000, 3)  # Default
        )

    def get_strategy(self, agent_id: str) -> ContextStrategy:
        """Get context strategy for an agent."""
        return AGENT_STRATEGIES.get(agent_id, ContextStrategy.ADAPTIVE)

    def get_memory_config(self, agent_id: str) -> MemoryConfig:
        """Get memory configuration for an agent."""
        return AGENT_MEMORY_CONFIGS.get(agent_id, MemoryConfig())

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Uses tiktoken if available, otherwise falls back to char-based estimate.
        """
        if self._encoder:
            return len(self._encoder.encode(text))
        # Fallback: rough estimate (~4 chars per token)
        return len(text) // 4

    def build_context(
        self,
        agent_id: str,
        base_prompt: str,
        soul: str = "",
        memory: str = "",
        secondbrain_results: Optional[List[Dict]] = None,
        recent_activity: Optional[List[Dict]] = None,
        request: Optional[str] = None,
    ) -> str:
        """
        Build optimized context for an agent based on their budget and strategy.

        Args:
            agent_id: The agent's identifier
            base_prompt: The agent's base system prompt
            soul: The agent's SOUL.md content (identity)
            memory: The agent's MEMORY.md content (history)
            secondbrain_results: Relevant knowledge from SecondBrain
            recent_activity: Recent agent activities
            request: The current user request (for adaptive filtering)

        Returns:
            Optimized system prompt string
        """
        budget = self.get_budget(agent_id)
        strategy = self.get_strategy(agent_id)
        mem_config = self.get_memory_config(agent_id)

        # Check cache for static content (CACHED strategy)
        if strategy == ContextStrategy.CACHED:
            cache_key = f"{agent_id}:base"
            if cache_key in self._context_cache:
                cached = self._context_cache[cache_key]
                return cached + (f"\n\n## Current Request\n{request}" if request else "")

        parts = [base_prompt]
        tokens_used = self.count_tokens(base_prompt)

        # Add soul (identity)
        if soul and mem_config.include_soul:
            soul_budget = min(budget.soul_tokens, mem_config.soul_max_chars // 4)
            soul_tokens = self.count_tokens(soul)

            if soul_tokens > soul_budget:
                soul = self._truncate_to_tokens(soul, soul_budget)

            parts.append(f"## Your Identity\n{soul}")
            tokens_used += self.count_tokens(soul)

        # Add memory based on strategy
        if memory and mem_config.include_memory and strategy != ContextStrategy.MINIMAL:
            memory_budget = min(budget.memory_tokens, mem_config.memory_max_chars // 4)

            if strategy == ContextStrategy.ADAPTIVE and request:
                # Only include relevant memory sections
                memory = self._filter_relevant_memory(memory, request)

            memory_tokens = self.count_tokens(memory)
            if memory_tokens > memory_budget:
                memory = self._truncate_to_tokens(memory, memory_budget)

            parts.append(f"## Your Memory\n{memory}")
            tokens_used += self.count_tokens(memory)

        # Add SecondBrain results
        if secondbrain_results and mem_config.include_secondbrain:
            limit = min(budget.secondbrain_limit, mem_config.secondbrain_limit)
            limited = secondbrain_results[:limit]

            if limited:
                recalls = "\n".join(
                    f"- **{r.get('title', 'Note')}**: {r.get('snippet', r.get('content', ''))[:200]}"
                    for r in limited
                )
                recalls_tokens = self.count_tokens(recalls)

                if tokens_used + recalls_tokens < budget.max_tokens:
                    parts.append(f"## Relevant Knowledge\n{recalls}")
                    tokens_used += recalls_tokens

        # Add recent activity (FULL strategy only)
        if recent_activity and mem_config.include_recent_activity:
            if strategy == ContextStrategy.FULL:
                activity_limit = mem_config.activity_limit
                activity_text = "\n".join(
                    f"- {a.get('timestamp', '')}: {a.get('action', '')} - {a.get('result', '')[:100]}"
                    for a in recent_activity[:activity_limit]
                )
                activity_tokens = self.count_tokens(activity_text)

                if tokens_used + activity_tokens < budget.max_tokens:
                    parts.append(f"## Recent Activity\n{activity_text}")
                    tokens_used += activity_tokens

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
            truncated = self._encoder.decode(tokens[:max_tokens])
            return truncated.rsplit(" ", 1)[0] + "..."
        # Fallback: char-based truncation
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(" ", 1)[0] + "..."

    def _filter_relevant_memory(self, memory: str, request: str) -> str:
        """
        Filter memory to only include sections relevant to the request.

        Uses simple keyword-based filtering for speed.
        """
        # Extract meaningful words from request (skip common words)
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "have", "has", "had", "do", "does", "did", "will", "would",
                     "could", "should", "may", "might", "can", "to", "of", "in",
                     "for", "on", "with", "at", "by", "from", "as", "into", "it"}

        request_words = set(
            word.lower() for word in re.findall(r'\b\w+\b', request)
            if word.lower() not in stopwords and len(word) > 2
        )

        if not request_words:
            # If no meaningful words, return truncated memory
            return memory[:2000]

        # Split memory into sections
        sections = re.split(r'\n(?=## |\n# )', memory)
        relevant = []

        for section in sections:
            section_words = set(
                word.lower() for word in re.findall(r'\b\w+\b', section)
                if word.lower() not in stopwords and len(word) > 2
            )
            overlap = len(request_words & section_words)

            # Include if 2+ word overlap or if it's a short section (likely a header)
            if overlap >= 2 or len(section) < 100:
                relevant.append(section)

        if relevant:
            return "\n".join(relevant)

        # Fallback: return beginning of memory
        return memory[:2000]

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

    def get_all_token_usage(self) -> Dict[str, int]:
        """Get token usage for all agents."""
        return dict(self._token_usage)

    def estimate_cost(self, agent_id: str, model: str) -> float:
        """
        Estimate cost for a request based on token usage.

        Prices are per million tokens (input).
        """
        token_count = self._token_usage.get(agent_id, 0)

        # Approximate input prices per 1M tokens
        prices = {
            "claude-haiku-4-5": 0.80,
            "claude-3-5-sonnet": 3.00,
            "claude-sonnet-4": 3.00,
            "claude-opus-4-5": 15.00,
        }

        # Match model to price (handle version suffixes)
        price = 3.00  # Default to Sonnet pricing
        for model_key, p in prices.items():
            if model_key in model:
                price = p
                break

        return (token_count / 1_000_000) * price


# Singleton instance
_manager: Optional[AgentContextManager] = None


def get_context_manager() -> AgentContextManager:
    """Get the singleton AgentContextManager instance."""
    global _manager
    if _manager is None:
        _manager = AgentContextManager()
    return _manager


# CLI for testing
if __name__ == "__main__":
    manager = get_context_manager()

    # Test with sample data
    test_agents = ["manager", "finance", "maintenance", "janitor"]

    sample_soul = """
    You are Mamadou, the Finance Agent for MyCasa Pro.
    Your role is to manage household finances, track investments,
    and provide financial recommendations.
    """

    sample_memory = """
    ## 2026-02-05
    - Reviewed portfolio: 15% stocks, 85% cash
    - User asked about rebalancing

    ## 2026-02-04
    - Monthly bills: $2,450 total
    - Electricity up 12% from last month

    ## 2026-02-03
    - Added new stock position: AAPL 10 shares
    """

    sample_secondbrain = [
        {"title": "Investment Strategy", "snippet": "Conservative approach with 60/40 split"},
        {"title": "Bill Schedule", "snippet": "Rent due 1st, utilities 15th"},
    ]

    print("Context Manager Test\n" + "=" * 60)

    for agent in test_agents:
        context = manager.build_context(
            agent_id=agent,
            base_prompt=f"You are the {agent} agent.",
            soul=sample_soul,
            memory=sample_memory,
            secondbrain_results=sample_secondbrain,
            request="What's my portfolio allocation?",
        )

        budget = manager.get_budget(agent)
        strategy = manager.get_strategy(agent)
        tokens = manager.get_token_usage(agent)

        print(f"\nAgent: {agent}")
        print(f"Strategy: {strategy.value}")
        print(f"Budget: {budget.max_tokens} tokens")
        print(f"Context: {tokens} tokens ({tokens/budget.max_tokens*100:.1f}% of budget)")
        print(f"Context preview: {context[:100]}...")
