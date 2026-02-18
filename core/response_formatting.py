import re

# Remove most emoji and pictographs (basic Unicode planes + common symbol ranges)
_EMOJI_RE = re.compile(
    r"[\U00010000-\U0010FFFF\u2600-\u27BF\uFE0F]",
    flags=re.UNICODE,
)

_BOLD_RE = re.compile(r"(\*\*|__)(.*?)\1")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)|_(.*?)_")
_CODE_RE = re.compile(r"`([^`]*)`")


def _strip_markdown(text: str) -> str:
    lines = []
    in_code_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^\s*[-*•]\s+", "", line)
        line = re.sub(r"^\s*\d+\.\s+", "", line)
        line = _BOLD_RE.sub(r"\2", line)
        line = _ITALIC_RE.sub(lambda m: m.group(1) or m.group(2) or "", line)
        line = _CODE_RE.sub(r"\1", line)
        lines.append(line)
    return "\n".join(lines).strip()


def _strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub("", text)


def _strip_signoff(text: str) -> str:
    lines = text.splitlines()
    while lines:
        tail = lines[-1].strip()
        if re.match(r"^[-—]{1,2}\s*\w+", tail):
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


def _summarize_janitor_report(text: str) -> str:
    status_match = re.search(r"Status:\s*([A-Z]+)", text)
    status = status_match.group(1).lower() if status_match else "unknown"
    return f"System health report generated. Status: {status}. Open Janitor for details."


def normalize_agent_response(agent_id: str, text: str) -> str:
    if not text:
        return text
    cleaned = text.strip()

    if agent_id in {"janitor", "janitor-debugger"} and (
        "SYSTEM HEALTH REPORT" in cleaned or "╔" in cleaned or "║" in cleaned
    ):
        return _summarize_janitor_report(cleaned)

    cleaned = _strip_emojis(cleaned)
    cleaned = _strip_signoff(cleaned)
    cleaned = _strip_markdown(cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
