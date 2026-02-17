"""Helpers to prevent identity/heartbeat content from leaking in responses."""
from __future__ import annotations

from typing import Dict, Iterable, List


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _iter_identity_sections(identity: Dict[str, str]) -> Iterable[str]:
    for key in ("soul", "user", "security", "tools", "memory"):
        content = identity.get(key)
        if content:
            yield content
    daily_notes = identity.get("daily_notes") or {}
    for _, content in daily_notes.items():
        if content:
            yield content


def extract_sensitive_snippets(identity: Dict[str, str], limit: int = 160, max_snippets: int = 120) -> List[str]:
    snippets: List[str] = []
    for content in _iter_identity_sections(identity):
        for line in content.splitlines():
            line = line.strip()
            if len(line) < 24:
                continue
            if len(line) > limit:
                line = line[:limit]
            snippets.append(line)
            if len(snippets) >= max_snippets:
                return snippets
    return snippets


def redact_identity_snippets(text: str, identity: Dict[str, str]) -> str:
    if not text or not identity:
        return text
    normalized_text = _normalize(text)
    for snippet in extract_sensitive_snippets(identity):
        if _normalize(snippet) in normalized_text:
            return (
                "I can't share internal identity or heartbeat configuration, "
                "but I can summarize status or help with tasks."
            )
    return text
