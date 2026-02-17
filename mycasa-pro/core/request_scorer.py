"""
ClawRouter-inspired request complexity scorer.
Runs locally in <1ms, no API calls.

Inspired by https://github.com/BlockRunAI/ClawRouter
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
    """Result of scoring a request."""
    score: float
    tier: ModelTier
    confidence: float
    factors: Dict[str, float]
    recommended_model: str


class RequestScorer:
    """
    Weighted multi-dimension request scorer.

    Analyzes incoming requests and routes them to the cheapest capable model.
    Uses a 14-dimension weighted scoring system that runs entirely locally.
    """

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

    # Model tier configurations
    TIER_MODELS = {
        ModelTier.SIMPLE: "claude-haiku-4-5-20250514",
        ModelTier.MEDIUM: "claude-3-5-sonnet-20241022",
        ModelTier.COMPLEX: "claude-sonnet-4-20250514",
        ModelTier.REASONING: "claude-opus-4-5-20251101",
    }

    # Agent base tier adjustments
    AGENT_ADJUSTMENTS = {
        "manager": 0.20,        # Always needs strategic thinking
        "finance": 0.10,        # Financial analysis is nuanced
        "maintenance": 0.0,     # Usually straightforward tasks
        "contractors": 0.0,     # Scheduling, coordination
        "projects": 0.10,       # Planning, dependencies
        "security-manager": 0.10,  # Threat analysis
        "janitor": -0.15,       # Monitoring, cleanup
        "backup-recovery": -0.15,  # Automated operations
    }

    # Pattern sets for scoring
    REASONING_MARKERS = [
        r"\bprove\b", r"\btheorem\b", r"\bstep by step\b", r"\banalyze\b",
        r"\bwhy\b.*\?", r"\bexplain.*reasoning\b", r"\bevaluate\b",
        r"\bcompare and contrast\b", r"\bweigh the\b", r"\btrade-?off\b",
    ]

    CODE_INDICATORS = [
        r"```", r"\bfunction\b", r"\bclass\b", r"\bdef\b", r"\breturn\b",
        r"\bimport\b", r"\bconst\b", r"\blet\b", r"\bvar\b", r"\basync\b",
        r"\bawait\b", r"=>", r"\binterface\b", r"\btype\b",
    ]

    SIMPLE_INDICATORS = [
        r"^what is\b", r"^define\b", r"^list\b", r"^who is\b",
        r"^when\b", r"^where\b", r"^how many\b", r"^what time\b",
        r"^yes or no\b", r"^true or false\b",
    ]

    FINANCIAL_TERMS = [
        r"\btax\b", r"\binvest", r"\bportfolio\b", r"\bstock\b",
        r"\bdividend\b", r"\bcapital gain", r"\brebalance\b", r"\bROI\b",
        r"\byield\b", r"\basset\b", r"\bliabilit", r"\bequity\b",
    ]

    SECURITY_TERMS = [
        r"\bpassword\b", r"\bsecure\b", r"\bthreat\b", r"\baccess\b",
        r"\bencrypt\b", r"\bvulnerab", r"\bpermission\b", r"\bauth\b",
        r"\btoken\b", r"\bcredential\b",
    ]

    def score(self, request: str, agent_id: Optional[str] = None) -> ScoringResult:
        """
        Score a request and return routing recommendation.

        Args:
            request: The user's request text
            agent_id: Optional agent identifier for tier adjustment

        Returns:
            ScoringResult with score, tier, confidence, factors, and recommended model
        """
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

        # Normalize to 0-1 range
        score = max(0.0, min(1.0, (raw_score + 0.5)))

        # Apply agent adjustment if provided
        if agent_id:
            score = self._adjust_for_agent(score, agent_id)

        # Determine tier
        tier = self._score_to_tier(score)

        # Special rule: 2+ strong reasoning markers → REASONING tier
        if factors["reasoning_markers"] >= 0.6:
            tier = ModelTier.REASONING
            score = max(score, 0.85)

        return ScoringResult(
            score=round(score, 3),
            tier=tier,
            confidence=round(self._calculate_confidence(factors), 3),
            factors={k: round(v, 3) for k, v in factors.items()},
            recommended_model=self.TIER_MODELS[tier]
        )

    def _score_reasoning(self, text: str) -> float:
        """Score presence of reasoning/analytical markers."""
        matches = sum(1 for p in self.REASONING_MARKERS if re.search(p, text, re.I))
        return min(1.0, matches / 3)

    def _score_code(self, text: str) -> float:
        """Score presence of code indicators."""
        matches = sum(1 for p in self.CODE_INDICATORS if re.search(p, text))
        return min(1.0, matches / 4)

    def _score_simple(self, text: str) -> float:
        """Score simple query indicators (returns 1.0 if simple pattern matches)."""
        for pattern in self.SIMPLE_INDICATORS:
            if re.match(pattern, text.strip(), re.I):
                return 1.0
        return 0.0

    def _score_multi_step(self, text: str) -> float:
        """Score multi-step task indicators."""
        indicators = [
            r"\bfirst\b.*\bthen\b", r"\bstep \d", r"\b\d\.\s",
            r"\band then\b", r"\bafter that\b", r"\bfinally\b",
        ]
        matches = sum(1 for p in indicators if re.search(p, text, re.I))
        return min(1.0, matches / 2)

    def _score_technical(self, text: str) -> float:
        """Score technical vocabulary presence."""
        terms = [
            r"\bAPI\b", r"\bdatabase\b", r"\bschema\b", r"\balgorithm\b",
            r"\bconfig", r"\bdeploym", r"\binfrastructure\b", r"\barchitect",
        ]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_length(self, text: str) -> float:
        """Score request length as complexity proxy."""
        tokens = len(text.split())
        if tokens < 20:
            return 0.0
        if tokens < 50:
            return 0.3
        if tokens < 100:
            return 0.5
        if tokens < 200:
            return 0.7
        return 1.0

    def _score_financial(self, text: str) -> float:
        """Score financial domain complexity."""
        matches = sum(1 for t in self.FINANCIAL_TERMS if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_security(self, text: str) -> float:
        """Score security domain sensitivity."""
        matches = sum(1 for t in self.SECURITY_TERMS if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_creative(self, text: str) -> float:
        """Score creative task indicators."""
        terms = [r"\bwrite\b", r"\bcompose\b", r"\bdesign\b", r"\bcreate\b", r"\bdraft\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 2)

    def _score_question_complexity(self, text: str) -> float:
        """Score question structure complexity."""
        questions = text.count("?")
        conditionals = len(re.findall(r"\bif\b.*\bthen\b", text, re.I))
        nested = len(re.findall(r"\bwhich\b.*\bwhen\b|\bwhat\b.*\bif\b", text, re.I))
        return min(1.0, (questions + conditionals + nested) / 3)

    def _score_urgency(self, text: str) -> float:
        """Score urgency indicators (for maintenance context)."""
        terms = [r"\burgent\b", r"\bemergency\b", r"\bbroken\b", r"\basap\b", r"\bimmediately\b"]
        return 1.0 if any(re.search(t, text, re.I) for t in terms) else 0.0

    def _score_constraints(self, text: str) -> float:
        """Score constraint/requirement indicators."""
        terms = [r"\bmust\b", r"\bshould\b", r"\bensure\b", r"\brequire\b", r"\bneed to\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 3)

    def _score_format(self, text: str) -> float:
        """Score specific format requirement indicators."""
        terms = [r"\bjson\b", r"\bmarkdown\b", r"\bformat as\b", r"\breturn as\b", r"\blist of\b"]
        matches = sum(1 for t in terms if re.search(t, text, re.I))
        return min(1.0, matches / 2)

    def _adjust_for_agent(self, score: float, agent_id: str) -> float:
        """Adjust score based on agent's typical task complexity."""
        adjustment = self.AGENT_ADJUSTMENTS.get(agent_id, 0.0)
        return max(0.0, min(1.0, score + adjustment))

    def _score_to_tier(self, score: float) -> ModelTier:
        """Convert numeric score to model tier."""
        if score < 0.25:
            return ModelTier.SIMPLE
        if score < 0.55:
            return ModelTier.MEDIUM
        if score < 0.80:
            return ModelTier.COMPLEX
        return ModelTier.REASONING

    def _calculate_confidence(self, factors: Dict[str, float]) -> float:
        """Calculate confidence based on factor agreement."""
        values = list(factors.values())
        if not values:
            return 0.5
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        # Lower variance = higher confidence
        return max(0.5, 1.0 - variance)


# Singleton instance
_scorer: Optional[RequestScorer] = None


def get_request_scorer() -> RequestScorer:
    """Get the singleton RequestScorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = RequestScorer()
    return _scorer


# CLI for testing
if __name__ == "__main__":
    import sys
    import time

    scorer = get_request_scorer()

    test_requests = [
        ("What is 2+2?", None),
        ("Summarize this article about climate change", None),
        ("Write a Python function to sort a list using quicksort", None),
        ("Prove that the square root of 2 is irrational, step by step", None),
        ("Check if the HVAC filter needs replacing", "maintenance"),
        ("Analyze my portfolio performance and recommend rebalancing strategy", "finance"),
        ("What's the status of the security cameras?", "security-manager"),
    ]

    print("Request Scorer Benchmark\n" + "=" * 60)

    for request, agent in test_requests:
        start = time.perf_counter()
        result = scorer.score(request, agent)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nRequest: {request[:50]}...")
        print(f"Agent: {agent or 'none'}")
        print(f"Score: {result.score} | Tier: {result.tier.value} | Confidence: {result.confidence}")
        print(f"Model: {result.recommended_model}")
        print(f"Time: {elapsed:.3f}ms")
