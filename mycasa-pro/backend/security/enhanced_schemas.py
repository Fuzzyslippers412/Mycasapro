"""
Enhanced Security Schemas - Hardened Architecture Extensions
Adds identity metadata, evidence citations, constraints, and confirmation flow
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from .schemas import ActionIntent, PolicyDecision, PolicyResult, RiskLevel, ActionType
    from .trust_tiers import IdentityMetadata, TrustTier
    from .detectors import RiskCategory
except ImportError:
    from schemas import ActionIntent, PolicyDecision, PolicyResult, RiskLevel, ActionType
    from trust_tiers import IdentityMetadata, TrustTier
    from detectors import RiskCategory


# ==================== ENHANCED ACTION INTENT ====================

@dataclass
class EvidenceCitation:
    """
    Citation of evidence supporting an action intent

    This tracks which evidence (trusted vs untrusted) supports each intent
    """
    source_type: str  # "user_request" (T0) or "evidence_chunk" (T2/T3)
    source_id: str  # "user" or chunk ID
    trust_tier: TrustTier = TrustTier.T2_UNTRUSTED
    excerpt: Optional[str] = None  # Short excerpt (max 200 chars)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "trust_tier": self.trust_tier.value,
            "excerpt": self.excerpt,
        }


@dataclass
class EnhancedActionIntent(ActionIntent):
    """
    Enhanced ActionIntent with identity metadata and evidence citations

    Extends base ActionIntent with:
    - Identity metadata (user_id, org_id, origin, auth)
    - Evidence citations (what supports this intent?)
    - Trust tier classification
    """
    # Identity metadata (attached at gateway)
    identity: Optional[IdentityMetadata] = None

    # Evidence citations (what supports this action?)
    evidence_citations: List[EvidenceCitation] = field(default_factory=list)

    # Trust tier of the request source
    source_trust_tier: TrustTier = TrustTier.T0_TRUSTED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        data['identity'] = self.identity.to_dict() if self.identity else None
        data['evidence_citations'] = [c.to_dict() for c in self.evidence_citations]
        data['source_trust_tier'] = self.source_trust_tier.value
        return data

    def is_supported_by_trusted_source(self) -> bool:
        """
        Check if intent is supported by T0 (trusted) source

        For high-risk actions, this must be True
        """
        return any(
            c.trust_tier == TrustTier.T0_TRUSTED
            for c in self.evidence_citations
        )

    def get_untrusted_citations(self) -> List[EvidenceCitation]:
        """Get citations from untrusted sources"""
        return [
            c for c in self.evidence_citations
            if c.trust_tier in {TrustTier.T2_UNTRUSTED, TrustTier.T3_HOSTILE}
        ]


# ==================== ENHANCED POLICY DECISION ====================

@dataclass
class ActionConstraint:
    """
    Constraints on tool execution

    Applied by policy engine to limit scope/damage of actions
    """
    constraint_type: str  # "domain_allowlist", "max_bytes", "rate_limit", "amount_limit", etc.
    value: Any
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constraint_type": self.constraint_type,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class AllowedAction:
    """
    Action allowed with constraints

    Specifies exactly what can be done and with what limits
    """
    intent_id: str
    tool: str
    operation: str
    constraints: List[ActionConstraint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "tool": self.tool,
            "operation": self.operation,
            "constraints": [c.to_dict() for c in self.constraints],
        }


@dataclass
class DeniedAction:
    """Action denied with reason"""
    intent_id: str
    reason_category: str  # "prompt_injection", "authz", "tool_risk", etc.
    reason_detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "reason_category": self.reason_category,
            "reason_detail": self.reason_detail,
        }


@dataclass
class UserConfirmationPrompt:
    """
    Prompt for user confirmation

    For NEED_USER_CONFIRMATION decisions
    """
    confirmation_type: str  # "CONFIRMATION", "AMOUNT", "DESTINATION", etc.
    message: str
    fields_needed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confirmation_type": self.confirmation_type,
            "message": self.message,
            "fields_needed": self.fields_needed,
        }


@dataclass
class SafeResponseGuidance:
    """
    Guidance for generating safe responses

    Tells the response composer what to say/not say
    """
    what_to_say: str
    what_not_to_say: List[str] = field(default_factory=list)
    redactions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "what_to_say": self.what_to_say,
            "what_not_to_say": self.what_not_to_say,
            "redactions": self.redactions,
        }


class EnhancedPolicyResult(str, Enum):
    """Enhanced policy results with confirmation flow"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    ALLOW_WITH_CONSTRAINTS = "ALLOW_WITH_CONSTRAINTS"
    NEED_USER_CONFIRMATION = "NEED_USER_CONFIRMATION"


@dataclass
class EnhancedPolicyDecision:
    """
    Enhanced PolicyDecision with constraints and confirmation flow

    This is what the Policy Agent LLM outputs
    """
    # Decision
    decision: EnhancedPolicyResult = EnhancedPolicyResult.DENY
    risk_level: RiskLevel = RiskLevel.LOW

    # Reasoning
    reasons: List[Dict[str, Any]] = field(default_factory=list)  # category, summary, evidence

    # Actions
    allowed_actions: List[AllowedAction] = field(default_factory=list)
    denied_actions: List[DeniedAction] = field(default_factory=list)

    # Confirmation (if needed)
    required_user_prompts: List[UserConfirmationPrompt] = field(default_factory=list)

    # Response guidance
    safe_response_guidance: Optional[SafeResponseGuidance] = None

    # Metadata
    id: str = field(default_factory=lambda: f"enhanced-decision-{datetime.now().timestamp()}")
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "risk_level": self.risk_level.value,
            "reasons": self.reasons,
            "allowed_actions": [a.to_dict() for a in self.allowed_actions],
            "denied_actions": [a.to_dict() for a in self.denied_actions],
            "required_user_prompts": [p.to_dict() for p in self.required_user_prompts],
            "safe_response_guidance": self.safe_response_guidance.to_dict() if self.safe_response_guidance else None,
            "id": self.id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedPolicyDecision':
        """Parse from dictionary (e.g., LLM JSON output)"""
        # Parse decision
        decision = EnhancedPolicyResult(data.get("decision", "DENY"))
        risk_level = RiskLevel(data.get("risk_level", "LOW"))

        # Parse allowed actions
        allowed_actions = [
            AllowedAction(
                intent_id=a["intent_id"],
                tool=a["tool"],
                operation=a["operation"],
                constraints=[
                    ActionConstraint(
                        constraint_type=c["constraint_type"],
                        value=c["value"],
                        description=c["description"],
                    )
                    for c in a.get("constraints", [])
                ],
            )
            for a in data.get("allowed_actions", [])
        ]

        # Parse denied actions
        denied_actions = [
            DeniedAction(
                intent_id=d["intent_id"],
                reason_category=d.get("reason_category", "other"),
                reason_detail=d.get("why", d.get("reason_detail", "Unknown")),
            )
            for d in data.get("denied_actions", [])
        ]

        # Parse confirmation prompts
        prompts = [
            UserConfirmationPrompt(
                confirmation_type=p["type"],
                message=p["message"],
                fields_needed=p.get("fields_needed", []),
            )
            for p in data.get("required_user_prompts", [])
        ]

        # Parse response guidance
        guidance_data = data.get("safe_response_guidance")
        guidance = None
        if guidance_data:
            guidance = SafeResponseGuidance(
                what_to_say=guidance_data.get("what_to_say", ""),
                what_not_to_say=guidance_data.get("what_not_to_say", []),
                redactions=guidance_data.get("redactions", []),
            )

        return cls(
            decision=decision,
            risk_level=risk_level,
            reasons=data.get("reasons", []),
            allowed_actions=allowed_actions,
            denied_actions=denied_actions,
            required_user_prompts=prompts,
            safe_response_guidance=guidance,
        )


# ==================== ENHANCED EVIDENCE BUNDLE ====================

@dataclass
class EvidenceChunk:
    """
    Chunk of evidence from untrusted source

    Evidence is never concatenated into prompts - only references are passed
    """
    id: str
    content: str
    offset: int  # Character offset in original document
    length: int
    hash: str  # SHA-256 hash for integrity
    risk_score: float = 0.0
    risk_tags: List[str] = field(default_factory=list)

    def to_reference(self) -> Dict[str, Any]:
        """
        Get reference (no content!)

        This is what goes into prompts - never the actual content
        """
        return {
            "id": self.id,
            "offset": self.offset,
            "length": self.length,
            "hash": self.hash,
            "risk_score": self.risk_score,
            "risk_tags": self.risk_tags,
        }


@dataclass
class UntrustedEvidenceBundle:
    """
    Bundle of untrusted content with risk signals

    Content is stored separately and accessed by reference only
    This prevents prompt injection via document concatenation
    """
    id: str
    source_type: str  # pdf|web|doc|email|calendar|image|slack
    source_uri: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Content chunks (not exposed to LLM prompts directly)
    chunks: List[EvidenceChunk] = field(default_factory=list)

    # Risk assessment
    overall_risk_score: float = 0.0
    risk_tags: List[str] = field(default_factory=list)
    detector_results: Dict[str, Any] = field(default_factory=dict)

    # Rendering notes (for debugging)
    rendering_notes: List[str] = field(default_factory=list)

    def get_references(self) -> List[Dict[str, Any]]:
        """
        Get chunk references (NO CONTENT!)

        This is what Policy Agent sees - references only
        """
        return [chunk.to_reference() for chunk in self.chunks]

    def get_chunk_content(self, chunk_id: str) -> Optional[str]:
        """
        Get content of specific chunk (only when explicitly requested)

        This is the only way to access content - by explicit ID lookup
        """
        for chunk in self.chunks:
            if chunk.id == chunk_id:
                return chunk.content
        return None

    def to_summary(self) -> Dict[str, Any]:
        """
        Get summary for Policy Agent (no content!)

        Policy Agent receives this, not raw content
        """
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "retrieved_at": self.retrieved_at,
            "chunk_count": len(self.chunks),
            "overall_risk_score": self.overall_risk_score,
            "risk_tags": self.risk_tags,
            "references": self.get_references(),
        }


# ==================== HARD RULES ====================

@dataclass
class HardSecurityRule:
    """
    Non-negotiable security rule

    Even if Policy Agent LLM says ALLOW, these rules can override to DENY
    """
    rule_id: str
    name: str
    description: str
    applies_to: List[ActionType]
    check_function: str  # Name of function to call for validation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "applies_to": [a.value for a in self.applies_to],
        }


# Pre-defined hard rules
HARD_RULES = [
    HardSecurityRule(
        rule_id="money-movement-requires-t0",
        name="Money Movement Requires Trusted Source",
        description="Any money/payment action must be explicitly requested in T0 trusted user message",
        applies_to=[ActionType.CALL_API, ActionType.EXECUTE_COMMAND],
        check_function="check_money_movement_source",
    ),
    HardSecurityRule(
        rule_id="no-secret-exfil",
        name="Never Exfiltrate Secrets",
        description="Secrets (API keys, tokens, passwords) cannot be sent externally",
        applies_to=[ActionType.CALL_API, ActionType.SEND_MESSAGE],
        check_function="check_secret_exfiltration",
    ),
    HardSecurityRule(
        rule_id="t2-t3-cannot-trigger-tools",
        name="Untrusted Content Cannot Trigger Tools",
        description="T2/T3 content can only be analyzed/summarized, not trigger side effects",
        applies_to=[ActionType.WRITE_FILE, ActionType.EXECUTE_COMMAND, ActionType.CALL_API],
        check_function="check_trust_tier_tool_access",
    ),
]
