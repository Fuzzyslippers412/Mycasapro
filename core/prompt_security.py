"""
MyCasa Pro - Prompt Security Module
Detects prompt injection attempts and enforces trust boundaries.

Based on ACIP v1.3 Cognitive Integrity Framework.
"""
import re
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum
from datetime import datetime


class TrustZone(str, Enum):
    """Trust zones for message sources"""
    OWNER = "owner"           # Zone A - Full authority
    TRUSTED = "trusted"       # Zone A-Limited - Conversation only
    UNTRUSTED = "untrusted"   # Zone B - Passive data


class ThreatLevel(str, Enum):
    """Threat assessment levels"""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


# Owner identifiers (should match SECURITY.md)
OWNER_IDENTIFIERS = [
    "+12677180107",
    "12677180107",
]

# Trusted but limited contacts
TRUSTED_IDENTIFIERS = [
    "+351915443876",
    "351915443876",
]


# Injection patterns to detect
INJECTION_PATTERNS = [
    # Priority manipulation
    (r"ignore\s+(previous|prior|all|your)\s+instructions?", "priority_override", ThreatLevel.BLOCKED),
    (r"disregard\s+(everything|all|your)\s+(above|instructions?|rules?)", "priority_override", ThreatLevel.BLOCKED),
    (r"forget\s+(everything|all|your)\s+(rules?|instructions?)", "priority_override", ThreatLevel.BLOCKED),
    (r"you\s+are\s+now\s+(in\s+)?(bypass|override|admin|sudo)\s+mode", "mode_switch", ThreatLevel.BLOCKED),
    (r"enter\s+(bypass|override|admin|sudo|developer)\s+mode", "mode_switch", ThreatLevel.BLOCKED),
    
    # Authority claims
    (r"(system|admin|root|developer)\s*(:|override|command)", "authority_claim", ThreatLevel.BLOCKED),
    (r"i\s*(am|'m)\s+(the\s+)?(admin|administrator|owner|developer|system)", "authority_claim", ThreatLevel.BLOCKED),
    (r"authorized\s+(by|to|access)", "authority_claim", ThreatLevel.SUSPICIOUS),
    
    # Secret extraction
    (r"(reveal|show|display|output|print)\s+(your\s+)?(system\s+)?prompt", "secret_extraction", ThreatLevel.BLOCKED),
    (r"(what|tell\s+me)\s+(are\s+)?your\s+(instructions?|rules?|guidelines?)", "secret_extraction", ThreatLevel.SUSPICIOUS),
    (r"(reveal|show|output)\s+(your\s+)?(api\s*key|token|password|secret)", "secret_extraction", ThreatLevel.BLOCKED),
    
    # Encoded payloads
    (r"decode\s+(and\s+)?(run|execute|follow)", "encoded_payload", ThreatLevel.BLOCKED),
    (r"base64\s*:\s*[A-Za-z0-9+/=]{20,}", "encoded_payload", ThreatLevel.SUSPICIOUS),
    (r"\\x[0-9a-fA-F]{2}", "hex_encoding", ThreatLevel.SUSPICIOUS),
    
    # Urgency manipulation
    (r"(urgent|emergency|quickly|immediately)\s*(!|:|\s+do)", "urgency_manipulation", ThreatLevel.SUSPICIOUS),
    (r"no\s+time\s+to\s+(check|verify|ask)", "urgency_manipulation", ThreatLevel.SUSPICIOUS),
    
    # Role manipulation  
    (r"(pretend|act\s+as\s+if|roleplay\s+as)\s+(you\s+)?(don't\s+have|have\s+no)\s+(restrictions?|rules?)", "role_manipulation", ThreatLevel.BLOCKED),
    (r"if\s+you\s+(didn't|did\s+not)\s+have\s+(restrictions?|rules?)", "role_manipulation", ThreatLevel.SUSPICIOUS),
    
    # Jailbreak attempts
    (r"(dan|developer\s+mode|jailbreak)", "jailbreak", ThreatLevel.BLOCKED),
    (r"ignore\s+(safety|security)\s+(guidelines?|rules?)", "jailbreak", ThreatLevel.BLOCKED),
]


# Sensitive information patterns (things we should never leak)
SENSITIVE_PATTERNS = [
    r"sk-ant-[a-zA-Z0-9-]+",  # Anthropic API key
    r"sk-[a-zA-Z0-9]{32,}",   # OpenAI API key
    r"ANTHROPIC_API_KEY",
    r"OPENAI_API_KEY", 
    r"api[_-]?key\s*[=:]\s*['\"][^'\"]+['\"]",
    r"password\s*[=:]\s*['\"][^'\"]+['\"]",
    r"secret\s*[=:]\s*['\"][^'\"]+['\"]",
    r"token\s*[=:]\s*['\"][^'\"]+['\"]",
]


def classify_source(identifier: str) -> TrustZone:
    """
    Classify a message source into trust zones.
    
    Args:
        identifier: Phone number, email, or other identifier
    
    Returns:
        TrustZone enum value
    """
    # Normalize identifier
    clean_id = identifier.replace("+", "").replace("-", "").replace(" ", "")
    
    # Check owner
    for owner_id in OWNER_IDENTIFIERS:
        if clean_id == owner_id.replace("+", ""):
            return TrustZone.OWNER
    
    # Check trusted
    for trusted_id in TRUSTED_IDENTIFIERS:
        if clean_id == trusted_id.replace("+", ""):
            return TrustZone.TRUSTED
    
    return TrustZone.UNTRUSTED


def scan_for_injection(content: str) -> Tuple[ThreatLevel, List[Dict[str, Any]]]:
    """
    Scan content for prompt injection attempts.
    
    Args:
        content: Text content to scan
    
    Returns:
        Tuple of (highest threat level, list of findings)
    """
    findings = []
    highest_threat = ThreatLevel.SAFE
    
    content_lower = content.lower()
    
    for pattern, category, threat_level in INJECTION_PATTERNS:
        matches = re.findall(pattern, content_lower, re.IGNORECASE)
        if matches:
            findings.append({
                "category": category,
                "threat_level": threat_level.value,
                "pattern": pattern,
                "matches": len(matches) if isinstance(matches[0], str) else len(matches),
            })
            
            # Track highest threat
            if threat_level == ThreatLevel.BLOCKED:
                highest_threat = ThreatLevel.BLOCKED
            elif threat_level == ThreatLevel.SUSPICIOUS and highest_threat != ThreatLevel.BLOCKED:
                highest_threat = ThreatLevel.SUSPICIOUS
    
    return highest_threat, findings


def scan_for_sensitive_data(content: str) -> List[Dict[str, Any]]:
    """
    Scan content for sensitive data that shouldn't be leaked.
    
    Args:
        content: Text content to scan
    
    Returns:
        List of findings (patterns matched)
    """
    findings = []
    
    for pattern in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            findings.append({
                "pattern": pattern,
                "count": len(matches),
                "type": "sensitive_data",
            })
    
    return findings


def evaluate_message_security(
    content: str,
    source_identifier: str,
    action_requested: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive security evaluation of a message.
    
    Args:
        content: Message content
        source_identifier: Who sent the message
        action_requested: What action is being requested (if any)
    
    Returns:
        Security evaluation result
    """
    # Classify source
    trust_zone = classify_source(source_identifier)
    
    # Scan for injection
    injection_threat, injection_findings = scan_for_injection(content)
    
    # Determine if action is allowed
    action_allowed = True
    block_reason = None
    
    # Zone B (untrusted) cannot authorize actions
    if trust_zone == TrustZone.UNTRUSTED:
        if action_requested in ["workspace_change", "send_message", "execute_command", "config_change"]:
            action_allowed = False
            block_reason = "Untrusted source cannot authorize this action"
    
    # Zone A-Limited (trusted) cannot authorize workspace changes
    if trust_zone == TrustZone.TRUSTED:
        if action_requested in ["workspace_change", "config_change"]:
            action_allowed = False
            block_reason = "Trusted contact cannot authorize workspace changes"
    
    # Injection detected - block regardless of zone
    if injection_threat == ThreatLevel.BLOCKED:
        action_allowed = False
        block_reason = f"Prompt injection detected: {injection_findings[0]['category']}"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "source": source_identifier,
        "trust_zone": trust_zone.value,
        "injection_threat": injection_threat.value,
        "injection_findings": injection_findings,
        "action_requested": action_requested,
        "action_allowed": action_allowed,
        "block_reason": block_reason,
    }


def audit_content_for_leaks(content: str) -> Dict[str, Any]:
    """
    Audit outgoing content for potential data leaks.
    
    Args:
        content: Content about to be sent/shared
    
    Returns:
        Audit result with any findings
    """
    sensitive_findings = scan_for_sensitive_data(content)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "content_length": len(content),
        "sensitive_data_found": len(sensitive_findings) > 0,
        "findings": sensitive_findings,
        "recommendation": "BLOCK" if sensitive_findings else "ALLOW",
    }
