"""
Trust Tier System for Content Classification
Implements T0/T1/T2/T3 trust hierarchy for secure content handling
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


class TrustTier(str, Enum):
    """
    Trust tiers for content classification

    T0: Trusted instructions (system/developer + authenticated user)
    T1: Semi-trusted (internal DB, owned configs)
    T2: Untrusted (PDFs, web, docs, emails, OCR)
    T3: Hostile (flagged by detectors as injection/exfil)
    """
    T0_TRUSTED = "T0_trusted"
    T1_SEMI_TRUSTED = "T1_semi_trusted"
    T2_UNTRUSTED = "T2_untrusted"
    T3_HOSTILE = "T3_hostile"


class ContentOrigin(str, Enum):
    """Where content came from"""
    USER_CHAT = "user_chat"
    USER_API = "user_api"
    SYSTEM = "system"
    DEVELOPER = "developer"
    DATABASE = "database"
    CONFIG = "config"
    PDF = "pdf"
    WEB = "web"
    EMAIL = "email"
    CALENDAR = "calendar"
    SLACK = "slack"
    FILE_UPLOAD = "file_upload"
    OCR = "ocr"
    WEBHOOK = "webhook"
    CRON = "cron"
    UNKNOWN = "unknown"


class AuthStrength(str, Enum):
    """Authentication strength"""
    PASSWORD = "password"
    MFA = "mfa"
    MTLS = "mtls"
    API_KEY = "api_key"
    SESSION = "session"
    NONE = "none"


@dataclass
class IdentityMetadata:
    """
    Immutable identity metadata attached at gateway

    This cannot be forged by untrusted content
    """
    user_id: str
    org_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    origin: ContentOrigin = ContentOrigin.UNKNOWN
    auth_strength: AuthStrength = AuthStrength.NONE
    scopes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "origin": self.origin.value,
            "auth_strength": self.auth_strength.value,
            "scopes": self.scopes,
        }


@dataclass
class TrustedContent:
    """T0 content - system/developer/authenticated user"""
    content: str
    source: str  # "system", "developer", "user"
    identity: IdentityMetadata
    tier: TrustTier = TrustTier.T0_TRUSTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "identity": self.identity.to_dict(),
            "tier": self.tier.value,
        }


@dataclass
class UntrustedContent:
    """T2/T3 content - external documents, untrusted sources"""
    content: str
    source_type: ContentOrigin
    source_uri: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    risk_score: float = 0.0
    risk_tags: List[str] = field(default_factory=list)
    tier: TrustTier = TrustTier.T2_UNTRUSTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "content_length": len(self.content),
            "source_type": self.source_type.value,
            "source_uri": self.source_uri,
            "retrieved_at": self.retrieved_at,
            "risk_score": self.risk_score,
            "risk_tags": self.risk_tags,
            "tier": self.tier.value,
        }


class TrustTierClassifier:
    """
    Classifies content into trust tiers

    Rules:
    - T0: System/developer messages + authenticated user requests
    - T1: Internal DB records, owned configs
    - T2: External documents (PDFs, web, emails) with low risk
    - T3: Content flagged by detectors as hostile
    """

    # Origins that are T0 (trusted instructions)
    T0_ORIGINS = {
        ContentOrigin.SYSTEM,
        ContentOrigin.DEVELOPER,
        ContentOrigin.USER_CHAT,  # If properly authenticated
        ContentOrigin.USER_API,   # If properly authenticated
    }

    # Origins that are T1 (semi-trusted)
    T1_ORIGINS = {
        ContentOrigin.DATABASE,
        ContentOrigin.CONFIG,
    }

    # Origins that are T2 (untrusted)
    T2_ORIGINS = {
        ContentOrigin.PDF,
        ContentOrigin.WEB,
        ContentOrigin.EMAIL,
        ContentOrigin.CALENDAR,
        ContentOrigin.SLACK,
        ContentOrigin.FILE_UPLOAD,
        ContentOrigin.OCR,
        ContentOrigin.WEBHOOK,
    }

    # Risk score threshold for T3 classification
    T3_THRESHOLD = 0.5

    @classmethod
    def classify(
        cls,
        content: str,
        origin: ContentOrigin,
        identity: Optional[IdentityMetadata] = None,
        risk_score: float = 0.0,
        risk_tags: List[str] = None,
    ) -> TrustTier:
        """
        Classify content into trust tier

        Args:
            content: The content to classify
            origin: Where it came from
            identity: Identity metadata (required for T0)
            risk_score: Detector risk score (0.0-1.0)
            risk_tags: Risk tags from detectors

        Returns:
            Appropriate trust tier
        """
        risk_tags = risk_tags or []

        # T3: Hostile (high risk score or certain risk tags)
        if risk_score >= cls.T3_THRESHOLD:
            return TrustTier.T3_HOSTILE

        if any(tag.startswith("risk:prompt_injection") or
               tag.startswith("risk:data_exfiltration") or
               tag.startswith("risk:credential_phishing")
               for tag in risk_tags):
            return TrustTier.T3_HOSTILE

        # T0: Trusted instructions
        if origin in cls.T0_ORIGINS:
            # For user origins, require proper authentication
            if origin in {ContentOrigin.USER_CHAT, ContentOrigin.USER_API}:
                if identity and identity.auth_strength != AuthStrength.NONE:
                    return TrustTier.T0_TRUSTED
                else:
                    # User content without auth -> T2
                    return TrustTier.T2_UNTRUSTED
            else:
                # System/developer always T0
                return TrustTier.T0_TRUSTED

        # T1: Semi-trusted
        if origin in cls.T1_ORIGINS:
            return TrustTier.T1_SEMI_TRUSTED

        # T2: Untrusted (default for external content)
        return TrustTier.T2_UNTRUSTED

    @classmethod
    def can_execute_tools(cls, tier: TrustTier) -> bool:
        """
        Can this tier trigger tool execution?

        Rules:
        - T0: Yes (trusted user requests)
        - T1: Limited (read-only)
        - T2: No (can only be analyzed/summarized)
        - T3: Absolutely not
        """
        return tier == TrustTier.T0_TRUSTED

    @classmethod
    def can_modify_state(cls, tier: TrustTier) -> bool:
        """
        Can this tier modify system state?

        Rules:
        - T0: Yes
        - T1/T2/T3: No
        """
        return tier == TrustTier.T0_TRUSTED

    @classmethod
    def can_access_secrets(cls, tier: TrustTier) -> bool:
        """
        Can this tier access secrets?

        Rules:
        - T0: Yes (with proper auth)
        - T1/T2/T3: No
        """
        return tier == TrustTier.T0_TRUSTED

    @classmethod
    def allowed_operations(cls, tier: TrustTier) -> List[str]:
        """
        What operations are allowed for this tier?

        Returns:
            List of allowed operation types
        """
        if tier == TrustTier.T0_TRUSTED:
            return ["read", "write", "execute", "tool_call", "state_change"]
        elif tier == TrustTier.T1_SEMI_TRUSTED:
            return ["read"]
        elif tier == TrustTier.T2_UNTRUSTED:
            return ["analyze", "summarize", "extract", "classify"]
        else:  # T3_HOSTILE
            return ["summarize_safe"]  # Only safe summary with warnings


# Helper functions for common use cases

def create_trusted_user_content(
    content: str,
    user_id: str,
    session_id: str,
    auth_strength: AuthStrength = AuthStrength.PASSWORD,
    origin: ContentOrigin = ContentOrigin.USER_CHAT,
) -> TrustedContent:
    """Create T0 trusted content from authenticated user"""
    identity = IdentityMetadata(
        user_id=user_id,
        session_id=session_id,
        origin=origin,
        auth_strength=auth_strength,
    )

    return TrustedContent(
        content=content,
        source="user",
        identity=identity,
        tier=TrustTier.T0_TRUSTED,
    )


def create_untrusted_content(
    content: str,
    source_type: ContentOrigin,
    risk_score: float = 0.0,
    risk_tags: List[str] = None,
) -> UntrustedContent:
    """Create T2/T3 untrusted content from external source"""
    risk_tags = risk_tags or []

    # Determine tier based on risk
    tier = TrustTierClassifier.classify(
        content=content,
        origin=source_type,
        risk_score=risk_score,
        risk_tags=risk_tags,
    )

    return UntrustedContent(
        content=content,
        source_type=source_type,
        risk_score=risk_score,
        risk_tags=risk_tags,
        tier=tier,
    )
