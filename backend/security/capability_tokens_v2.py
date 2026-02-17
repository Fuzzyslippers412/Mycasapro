"""
Capability Tokens V2 - JWT-like Authorization Tokens
Implements time-limited, scoped authorization for tool execution
"""
import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from uuid import uuid4

try:
    from .invariants import InvariantEnforcer
except ImportError:
    from invariants import InvariantEnforcer


@dataclass
class CapabilityTokenV2:
    """
    JWT-like capability token

    Structure matches the spec:
    {
      "iss": "mycasapro",
      "sub": "tool_capability",
      "agent_id": "legal_analyzer",
      "tool": "web.fetch",
      "operation": "GET",
      "constraints": {...},
      "iat": 1730000000,
      "exp": 1730000030,
      "nonce": "uuid"
    }
    """
    # JWT standard claims
    iss: str = "mycasapro"  # Issuer
    sub: str = "tool_capability"  # Subject
    iat: float = field(default_factory=time.time)  # Issued at
    exp: float = field(default_factory=lambda: time.time() + 30)  # Expires in 30s
    nonce: str = field(default_factory=lambda: str(uuid4()))  # Unique nonce

    # Capability-specific claims
    agent_id: str = ""
    tool: str = ""
    operation: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Signature (computed)
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (for signing)"""
        return {
            "iss": self.iss,
            "sub": self.sub,
            "agent_id": self.agent_id,
            "tool": self.tool,
            "operation": self.operation,
            "constraints": self.constraints,
            "iat": self.iat,
            "exp": self.exp,
            "nonce": self.nonce,
        }

    def generate_signature(self, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature

        Args:
            secret: Secret key for signing

        Returns:
            Hex signature
        """
        payload = json.dumps(self.to_dict(), sort_keys=True).encode()
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return sig

    def sign(self, secret: str) -> None:
        """Sign the token"""
        self.signature = self.generate_signature(secret)

    def verify_signature(self, secret: str) -> bool:
        """
        Verify token signature

        Args:
            secret: Secret key

        Returns:
            True if signature is valid
        """
        if not self.signature:
            return False

        expected = self.generate_signature(secret)
        return hmac.compare_digest(self.signature, expected)

    def is_valid(self, current_time: Optional[float] = None) -> tuple[bool, str]:
        """
        Check if token is valid

        Returns:
            (valid: bool, reason: str)
        """
        current_time = current_time or time.time()

        # Check signature exists
        if not self.signature:
            return False, "No signature"

        # Check expiration (INVARIANT_5)
        if self.exp is None:
            return False, "No expiration (INVARIANT_5 violation)"

        if current_time > self.exp:
            return False, f"Token expired (exp: {self.exp}, now: {current_time})"

        # Check issued time
        if self.iat > current_time:
            return False, "Token issued in future"

        # Check required fields
        if not self.agent_id:
            return False, "Missing agent_id"

        if not self.tool:
            return False, "Missing tool"

        if not self.operation:
            return False, "Missing operation"

        return True, ""

    def enforce_invariants(self, current_time: Optional[float] = None) -> None:
        """
        Enforce INVARIANT_5: Authority expires automatically

        Raises InvariantViolation if expired
        """
        current_time = current_time or time.time()
        InvariantEnforcer.check_authority_expiry(self.iat, self.exp, current_time)

    def to_jwt_string(self) -> str:
        """
        Encode as JWT-like string (simplified)

        Format: base64(header).base64(payload).signature
        """
        import base64

        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")

        payload_b64 = base64.urlsafe_b64encode(json.dumps(self.to_dict()).encode()).decode().rstrip("=")

        signature_b64 = self.signature or ""

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    @classmethod
    def from_jwt_string(cls, jwt_string: str) -> 'CapabilityTokenV2':
        """
        Decode from JWT-like string

        Args:
            jwt_string: JWT string

        Returns:
            CapabilityTokenV2
        """
        import base64

        parts = jwt_string.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        # Decode payload
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding

        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)

        # Create token
        token = cls(
            iss=payload.get("iss", "mycasapro"),
            sub=payload.get("sub", "tool_capability"),
            agent_id=payload.get("agent_id", ""),
            tool=payload.get("tool", ""),
            operation=payload.get("operation", ""),
            constraints=payload.get("constraints", {}),
            iat=payload.get("iat", time.time()),
            exp=payload.get("exp", time.time() + 30),
            nonce=payload.get("nonce", str(uuid4())),
        )

        # Extract signature
        token.signature = parts[2] if parts[2] else None

        return token


class CapabilityTokenManager:
    """
    Manages capability token lifecycle

    - Minting (creating tokens)
    - Validation (checking tokens)
    - Revocation (invalidating tokens)
    """

    def __init__(self, secret: str):
        """
        Initialize token manager

        Args:
            secret: Secret key for signing tokens
        """
        self.secret = secret
        self._revoked_nonces: set = set()

    def mint_token(
        self,
        agent_id: str,
        tool: str,
        operation: str,
        constraints: Dict[str, Any] = None,
        ttl_seconds: int = 30,
    ) -> CapabilityTokenV2:
        """
        Mint a new capability token

        Args:
            agent_id: Agent ID
            tool: Tool name (e.g., "web.fetch")
            operation: Operation (e.g., "GET")
            constraints: Constraints dict
            ttl_seconds: Time to live in seconds

        Returns:
            Signed CapabilityTokenV2
        """
        now = time.time()

        token = CapabilityTokenV2(
            iss="mycasapro",
            sub="tool_capability",
            agent_id=agent_id,
            tool=tool,
            operation=operation,
            constraints=constraints or {},
            iat=now,
            exp=now + ttl_seconds,
            nonce=str(uuid4()),
        )

        # Sign token
        token.sign(self.secret)

        return token

    def validate_token(
        self,
        token: CapabilityTokenV2,
        agent_id: str,
        tool: str,
        operation: str,
    ) -> tuple[bool, str]:
        """
        Validate a capability token

        Args:
            token: Token to validate
            agent_id: Expected agent ID
            tool: Expected tool
            operation: Expected operation

        Returns:
            (valid: bool, reason: str)
        """
        # Verify signature
        if not token.verify_signature(self.secret):
            return False, "Invalid signature"

        # Check validity
        valid, reason = token.is_valid()
        if not valid:
            return False, reason

        # Check revocation
        if token.nonce in self._revoked_nonces:
            return False, "Token revoked"

        # Check agent ID match
        if token.agent_id != agent_id:
            return False, f"Agent ID mismatch (expected {agent_id}, got {token.agent_id})"

        # Check tool match
        if token.tool != tool:
            return False, f"Tool mismatch (expected {tool}, got {token.tool})"

        # Check operation match
        if token.operation != operation:
            return False, f"Operation mismatch (expected {operation}, got {token.operation})"

        return True, ""

    def revoke_token(self, nonce: str) -> None:
        """
        Revoke a token by nonce

        Args:
            nonce: Token nonce to revoke
        """
        self._revoked_nonces.add(nonce)

    def cleanup_expired_revocations(self, max_age_seconds: int = 3600) -> None:
        """
        Clean up old revocations

        Since tokens expire, we don't need to keep revocations forever

        Args:
            max_age_seconds: Max age to keep revocations
        """
        # In production, this would track revocation timestamps
        # For now, just clear periodically
        if len(self._revoked_nonces) > 10000:
            self._revoked_nonces.clear()


# Global token manager
_token_manager: Optional[CapabilityTokenManager] = None


def get_token_manager(secret: Optional[str] = None) -> CapabilityTokenManager:
    """Get global token manager"""
    global _token_manager
    if _token_manager is None:
        import os
        secret = secret or os.getenv("CAPABILITY_SECRET", "default-secret-change-in-production")
        _token_manager = CapabilityTokenManager(secret)
    return _token_manager
