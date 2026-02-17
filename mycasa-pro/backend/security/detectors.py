"""
Content Detectors for Security Layer
Implements fast, deterministic detection of injection/exfil/credential/money patterns
"""
import re
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RiskCategory(str, Enum):
    """Risk categories for detected patterns"""
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    CREDENTIAL_PHISHING = "credential_phishing"
    MONEY_MOVEMENT = "money_movement"
    HIDDEN_TEXT = "hidden_text"
    SUSPICIOUS_COMMAND = "suspicious_command"


@dataclass
class DetectionResult:
    """Result from a detector"""
    category: RiskCategory
    score: float  # 0.0-1.0
    matches: List[str] = field(default_factory=list)
    positions: List[Tuple[int, int]] = field(default_factory=list)
    description: str = ""


class ContentDetectors:
    """
    Fast, deterministic detectors for security threats

    These run BEFORE LLM processing to catch obvious attacks
    """

    # Prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?(?:previous|prior|earlier)\s+(?:instructions?|prompts?|commands?)",
        r"system\s+(?:prompt|message|instruction)",
        r"developer\s+(?:message|prompt|instruction|mode)",
        r"you\s+(?:must|should|need\s+to)\s+(?:now|immediately)",
        r"act\s+as\s+(?:if|a|an)",
        r"tool\s+(?:call|execute|run|invoke)",
        r"function\s+(?:call|execute|run|invoke)",
        r"do\s+(?:this|that|it)\s+now",
        r"override\s+(?:previous|all|your)",
        r"disregard\s+(?:previous|all|your)",
        r"admin\s+(?:mode|access|override|command)",
        r"sudo\s+mode",
        r"privileged\s+mode",
        r"root\s+access",
        r"bypass\s+(?:security|validation|checks?)",
    ]

    # Data exfiltration patterns
    EXFIL_PATTERNS = [
        r"send\s+(?:me|to|it|this|the|your)",
        r"email\s+(?:me|to|it|this|the|your)",
        r"post\s+(?:to|it|this|the)",
        r"upload\s+(?:to|it|this|the)",
        r"paste\s+(?:here|it|this|the)",
        r"copy\s+(?:to|it|this|the)",
        r"forward\s+(?:to|me|it|this)",
        r"share\s+(?:with|to|it|this)",
        r"leak\s+(?:to|it|this|the)",
        r"exfiltrate",
        r"transmit\s+(?:to|it|this|the)",
        r"redirect\s+(?:to|it|this)",
    ]

    # Credential/secret phishing patterns
    CREDENTIAL_PATTERNS = [
        r"enter\s+(?:your\s+)?password",
        r"provide\s+(?:your\s+)?(?:password|credentials?|api\s+key)",
        r"api\s+key",
        r"access\s+token",
        r"bearer\s+token",
        r"oauth\s+(?:token|code)",
        r"2fa\s+(?:code|token)",
        r"two[\s-]factor",
        r"seed\s+phrase",
        r"private\s+key",
        r"secret\s+key",
        r"session\s+(?:token|cookie|id)",
        r"jwt\s+token",
        r"encryption\s+key",
        r"ssh\s+key",
        r"certificate\s+(?:private|key)",
    ]

    # Money movement patterns
    MONEY_PATTERNS = [
        r"wire\s+(?:transfer|payment|funds?)",
        r"transfer\s+(?:\$|\d+|money|funds?)",
        r"send\s+(?:\$|\d+|money|funds?)",
        r"pay(?:ment)?\s+(?:to|of|\$|\d+)",
        r"invoice\s+(?:payment|pay|amount)",
        r"purchase\s+(?:this|that|item)",
        r"buy\s+(?:this|that|item)",
        r"crypto\s+(?:wallet|address|transfer)",
        r"bitcoin\s+(?:address|wallet|transfer)",
        r"ethereum\s+(?:address|wallet|transfer)",
        r"bank\s+(?:account|transfer|routing)",
        r"routing\s+number",
        r"account\s+number",
        r"credit\s+card\s+(?:number|info)",
        r"debit\s+card",
        # Crypto addresses (simplified patterns)
        r"\b(?:0x[a-fA-F0-9]{40})\b",  # Ethereum
        r"\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b",  # Bitcoin
    ]

    # Suspicious command patterns
    COMMAND_PATTERNS = [
        r"rm\s+-rf",
        r"sudo\s+",
        r"chmod\s+777",
        r"chown\s+",
        r"curl\s+.*\|\s*bash",
        r"wget\s+.*\|\s*bash",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"subprocess\.",
        r"os\.system",
        r"os\.popen",
    ]

    def __init__(self):
        # Compile patterns for performance
        self._injection_re = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self._exfil_re = [re.compile(p, re.IGNORECASE) for p in self.EXFIL_PATTERNS]
        self._credential_re = [re.compile(p, re.IGNORECASE) for p in self.CREDENTIAL_PATTERNS]
        self._money_re = [re.compile(p, re.IGNORECASE) for p in self.MONEY_PATTERNS]
        self._command_re = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_PATTERNS]

    def detect_all(self, content: str) -> Dict[RiskCategory, DetectionResult]:
        """
        Run all detectors on content

        Args:
            content: Text to analyze

        Returns:
            Dict mapping categories to detection results
        """
        results = {}

        # Run each detector
        if result := self.detect_injection(content):
            results[RiskCategory.PROMPT_INJECTION] = result

        if result := self.detect_exfiltration(content):
            results[RiskCategory.DATA_EXFILTRATION] = result

        if result := self.detect_credentials(content):
            results[RiskCategory.CREDENTIAL_PHISHING] = result

        if result := self.detect_money_movement(content):
            results[RiskCategory.MONEY_MOVEMENT] = result

        if result := self.detect_suspicious_commands(content):
            results[RiskCategory.SUSPICIOUS_COMMAND] = result

        return results

    def detect_injection(self, content: str) -> DetectionResult | None:
        """Detect prompt injection attempts"""
        matches = []
        positions = []

        for pattern in self._injection_re:
            for match in pattern.finditer(content):
                matches.append(match.group(0))
                positions.append((match.start(), match.end()))

        if matches:
            # Score based on number of unique patterns matched
            score = min(len(set(matches)) / 5.0, 1.0)
            return DetectionResult(
                category=RiskCategory.PROMPT_INJECTION,
                score=score,
                matches=matches,
                positions=positions,
                description=f"Detected {len(matches)} injection pattern(s)",
            )

        return None

    def detect_exfiltration(self, content: str) -> DetectionResult | None:
        """Detect data exfiltration attempts"""
        matches = []
        positions = []

        for pattern in self._exfil_re:
            for match in pattern.finditer(content):
                matches.append(match.group(0))
                positions.append((match.start(), match.end()))

        if matches:
            score = min(len(set(matches)) / 4.0, 1.0)
            return DetectionResult(
                category=RiskCategory.DATA_EXFILTRATION,
                score=score,
                matches=matches,
                positions=positions,
                description=f"Detected {len(matches)} exfiltration pattern(s)",
            )

        return None

    def detect_credentials(self, content: str) -> DetectionResult | None:
        """Detect credential phishing attempts"""
        matches = []
        positions = []

        for pattern in self._credential_re:
            for match in pattern.finditer(content):
                matches.append(match.group(0))
                positions.append((match.start(), match.end()))

        if matches:
            score = min(len(set(matches)) / 3.0, 1.0)
            return DetectionResult(
                category=RiskCategory.CREDENTIAL_PHISHING,
                score=score,
                matches=matches,
                positions=positions,
                description=f"Detected {len(matches)} credential phishing pattern(s)",
            )

        return None

    def detect_money_movement(self, content: str) -> DetectionResult | None:
        """Detect money movement attempts"""
        matches = []
        positions = []

        for pattern in self._money_re:
            for match in pattern.finditer(content):
                matches.append(match.group(0))
                positions.append((match.start(), match.end()))

        if matches:
            score = min(len(set(matches)) / 3.0, 1.0)
            return DetectionResult(
                category=RiskCategory.MONEY_MOVEMENT,
                score=score,
                matches=matches,
                positions=positions,
                description=f"Detected {len(matches)} money movement pattern(s)",
            )

        return None

    def detect_suspicious_commands(self, content: str) -> DetectionResult | None:
        """Detect suspicious command patterns"""
        matches = []
        positions = []

        for pattern in self._command_re:
            for match in pattern.finditer(content):
                matches.append(match.group(0))
                positions.append((match.start(), match.end()))

        if matches:
            score = min(len(set(matches)) / 2.0, 1.0)
            return DetectionResult(
                category=RiskCategory.SUSPICIOUS_COMMAND,
                score=score,
                matches=matches,
                positions=positions,
                description=f"Detected {len(matches)} suspicious command(s)",
            )

        return None

    def get_overall_risk_score(self, results: Dict[RiskCategory, DetectionResult]) -> float:
        """
        Calculate overall risk score from detection results

        Returns:
            0.0-1.0 risk score (higher = more risky)
        """
        if not results:
            return 0.0

        # Weight categories by severity
        weights = {
            RiskCategory.PROMPT_INJECTION: 1.0,
            RiskCategory.DATA_EXFILTRATION: 0.9,
            RiskCategory.CREDENTIAL_PHISHING: 0.95,
            RiskCategory.MONEY_MOVEMENT: 1.0,
            RiskCategory.SUSPICIOUS_COMMAND: 0.8,
            RiskCategory.HIDDEN_TEXT: 0.7,
        }

        weighted_sum = sum(
            result.score * weights.get(category, 0.5)
            for category, result in results.items()
        )

        # Normalize to 0-1 range
        max_possible = len(results) * 1.0
        return min(weighted_sum / max_possible, 1.0) if max_possible > 0 else 0.0

    def get_risk_tags(self, results: Dict[RiskCategory, DetectionResult]) -> Set[str]:
        """
        Get set of risk tags from detection results

        Returns:
            Set of risk tags like "risk:prompt_injection"
        """
        tags = set()
        for category, result in results.items():
            if result.score >= 0.3:  # Threshold for tagging
                tags.add(f"risk:{category.value}")
        return tags


# Global detector instance
_detectors: ContentDetectors | None = None


def get_detectors() -> ContentDetectors:
    """Get global detectors instance"""
    global _detectors
    if _detectors is None:
        _detectors = ContentDetectors()
    return _detectors
