from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import math
import re

from sqlalchemy.orm import Session

from core.agent_profiles import get_or_create_agent_profile, normalize_budgets
from core.llm_client import get_llm_client
from database.models import LLMRun, AgentContextSnapshot


CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)


def _estimate_tokens_deterministic(text: str) -> int:
    """Deterministic token estimator (~4 chars/token, code blocks ~3 chars/token)."""
    if not text:
        return 0
    total = 0
    pos = 0
    for match in CODE_BLOCK_RE.finditer(text):
        before = text[pos:match.start()]
        if before:
            total += math.ceil(len(before) / 4)
        code = match.group(0)
        total += math.ceil(len(code) / 3)
        pos = match.end()
    tail = text[pos:]
    if tail:
        total += math.ceil(len(tail) / 4)
    return total


class TokenCounter:
    def __init__(self) -> None:
        self._encoder = None
        self._encoder_model = None
        try:
            import tiktoken  # type: ignore
            self._tiktoken = tiktoken
        except Exception:
            self._tiktoken = None

    def _get_encoder(self, model: Optional[str]):
        if not self._tiktoken:
            return None
        if self._encoder is not None and self._encoder_model == model:
            return self._encoder
        try:
            if model:
                self._encoder = self._tiktoken.encoding_for_model(model)
            else:
                self._encoder = self._tiktoken.get_encoding("cl100k_base")
            self._encoder_model = model
        except Exception:
            self._encoder = self._tiktoken.get_encoding("cl100k_base")
            self._encoder_model = model
        return self._encoder

    def count_text(self, text: str, model: Optional[str] = None) -> int:
        if not text:
            return 0
        encoder = self._get_encoder(model)
        if encoder:
            return len(encoder.encode(text))
        return _estimate_tokens_deterministic(text)

    def count_messages(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> int:
        if not messages:
            return 0
        total = 2  # base overhead
        for msg in messages:
            total += self.count_text(msg.get("content", ""), model) + 4
        return total


def _truncate_text_to_tokens(text: str, target_tokens: int, counter: TokenCounter, model: Optional[str]) -> str:
    if not text or target_tokens <= 0:
        return ""
    if counter.count_text(text, model) <= target_tokens:
        return text
    low = 0
    high = len(text)
    best = ""
    for _ in range(18):
        mid = (low + high) // 2
        candidate = text[:mid]
        if counter.count_text(candidate, model) <= target_tokens:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best.rstrip()


def _summarize_memory(text: str, target_tokens: int, counter: TokenCounter, model: Optional[str]) -> str:
    if not text:
        return ""
    clean = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if counter.count_text(clean, model) <= target_tokens:
        return clean

    sentences = re.split(r"(?<=[.!?])\\s+", clean)
    if len(sentences) <= 2:
        return _truncate_text_to_tokens(clean, target_tokens, counter, model)

    head = " ".join(sentences[:2]).strip()
    tail = sentences[-1].strip()
    combined = f"{head} {tail}".strip()
    if counter.count_text(combined, model) <= target_tokens:
        return combined
    return _truncate_text_to_tokens(combined, target_tokens, counter, model)


def _truncate_tool_text(text: str, target_tokens: int, counter: TokenCounter, model: Optional[str]) -> str:
    if not text:
        return ""
    if counter.count_text(text, model) <= target_tokens:
        return text
    lines = text.splitlines()
    head = lines[:3]
    tail = lines[-6:] if len(lines) > 6 else lines
    combined = "\n".join(head + ["…(truncated)…"] + tail)
    if counter.count_text(combined, model) <= target_tokens:
        return combined
    return _truncate_text_to_tokens(combined, target_tokens, counter, model)


@dataclass
class BuildInput:
    system_prompt: str
    developer_prompt: str
    memory: str
    history: List[Dict[str, Any]]
    retrieval: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    user_message: str


@dataclass
class BuildResult:
    messages: List[Dict[str, str]]
    component_tokens: Dict[str, int]
    included_summary: Dict[str, Any]
    trimming_applied: List[Dict[str, Any]]
    status: str
    error: Optional[str]
    input_tokens_estimated: int
    headroom: int
    model: str
    provider: str
    reserved_output_tokens: int
    context_window_tokens: int


class RequestBuilder:
    def __init__(self, db: Session, counter: Optional[TokenCounter] = None):
        self.db = db
        self.counter = counter or TokenCounter()

    def build(
        self,
        agent_name: str,
        build_input: BuildInput,
        request_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> BuildResult:
        profile = get_or_create_agent_profile(self.db, agent_name)
        budgets = normalize_budgets(profile.budgets_json or {})

        context_window_tokens = int(overrides.get("context_window_tokens")) if overrides and overrides.get("context_window_tokens") else profile.context_window_tokens
        reserved_output_tokens = int(overrides.get("reserved_output_tokens")) if overrides and overrides.get("reserved_output_tokens") else profile.reserved_output_tokens
        if overrides and overrides.get("budgets_json") is not None:
            budgets = normalize_budgets(overrides.get("budgets_json"))

        provider = profile.provider
        model = profile.model

        trimming_applied: List[Dict[str, Any]] = []
        error: Optional[str] = None

        if reserved_output_tokens >= context_window_tokens:
            return BuildResult(
                messages=[],
                component_tokens={},
                included_summary={},
                trimming_applied=[],
                status="blocked",
                error="reserved_output_tokens must be less than context_window_tokens",
                input_tokens_estimated=0,
                headroom=0,
                model=model,
                provider=provider,
                reserved_output_tokens=reserved_output_tokens,
                context_window_tokens=context_window_tokens,
            )

        max_input_tokens = context_window_tokens - reserved_output_tokens - budgets["safety_margin"]
        if max_input_tokens <= 0:
            return BuildResult(
                messages=[],
                component_tokens={},
                included_summary={},
                trimming_applied=[],
                status="blocked",
                error="Context window too small after safety margin and reserved output tokens",
                input_tokens_estimated=0,
                headroom=0,
                model=model,
                provider=provider,
                reserved_output_tokens=reserved_output_tokens,
                context_window_tokens=context_window_tokens,
            )

        system_text = (build_input.system_prompt or "").strip()
        developer_text = (build_input.developer_prompt or "").strip()
        memory_text = (build_input.memory or "").strip()
        history_messages = list(build_input.history or [])
        retrieval_items = list(build_input.retrieval or [])
        tool_items = list(build_input.tool_results or [])
        user_message = (build_input.user_message or "").strip()

        system_tokens = self.counter.count_text(system_text, model)
        developer_tokens = self.counter.count_text(developer_text, model)

        if system_tokens + developer_tokens > budgets["system"]:
            error = (
                f"System+developer prompt exceeds system budget "
                f"({system_tokens + developer_tokens} > {budgets['system']})"
            )
            return BuildResult(
                messages=[],
                component_tokens={"system": system_tokens, "developer": developer_tokens},
                included_summary={},
                trimming_applied=[],
                status="blocked",
                error=error,
                input_tokens_estimated=0,
                headroom=0,
                model=model,
                provider=provider,
                reserved_output_tokens=reserved_output_tokens,
                context_window_tokens=context_window_tokens,
            )

        def _history_tokens(messages: List[Dict[str, Any]]) -> int:
            total = 2
            for msg in messages:
                total += self.counter.count_text(msg.get("content", ""), model) + 4
            return total

        # History trimming
        history_tokens = _history_tokens(history_messages)
        if history_tokens > budgets["history"]:
            before_tokens = history_tokens
            turns: List[List[Dict[str, Any]]] = []
            current: List[Dict[str, Any]] = []
            for msg in history_messages:
                if msg.get("role") == "user" and current:
                    turns.append(current)
                    current = [msg]
                else:
                    current.append(msg)
            if current:
                turns.append(current)

            dropped_turns = 0
            while turns and history_tokens > budgets["history"]:
                dropped = turns.pop(0)
                dropped_turns += 1
                dropped_tokens = sum(
                    self.counter.count_text(m.get("content", ""), model) + 4 for m in dropped
                )
                history_tokens -= dropped_tokens

            history_messages = [m for turn in turns for m in turn]
            trimming_applied.append(
                {
                    "action": "drop_history_before",
                    "before_tokens": before_tokens,
                    "after_tokens": history_tokens,
                    "dropped_turns": dropped_turns,
                }
            )

        # Retrieval trimming
        retrieval_tokens = 0
        retrieval_entries: List[Dict[str, Any]] = []
        for item in retrieval_items:
            content = (item.get("content") or "").strip()
            if not content:
                continue
            entry = {
                "id": item.get("id") or item.get("doc_id") or item.get("source") or "doc",
                "content": content,
            }
            entry_tokens = self.counter.count_text(f"[{entry['id']}] {entry['content']}", model)
            entry["tokens"] = entry_tokens
            retrieval_entries.append(entry)
            retrieval_tokens += entry_tokens

        retrieval_header_tokens = self.counter.count_text("## Retrieval Context", model) if retrieval_entries else 0
        retrieval_tokens += retrieval_header_tokens

        if retrieval_tokens > budgets["retrieval"]:
            before_tokens = retrieval_tokens
            dropped_ids: List[str] = []
            while retrieval_entries and retrieval_tokens > budgets["retrieval"] and len(retrieval_entries) > 1:
                removed = retrieval_entries.pop()
                retrieval_tokens -= int(removed["tokens"])
                dropped_ids.append(str(removed["id"]))

            if retrieval_entries and retrieval_tokens > budgets["retrieval"]:
                entry = retrieval_entries[0]
                target_tokens = budgets["retrieval"]
                truncated = _truncate_text_to_tokens(entry["content"], target_tokens, self.counter, model)
                entry["content"] = truncated
                entry["tokens"] = self.counter.count_text(f"[{entry['id']}] {entry['content']}", model)
                retrieval_tokens = int(entry["tokens"]) + retrieval_header_tokens

            trimming_applied.append(
                {
                    "action": "reduce_retrieval",
                    "before_tokens": before_tokens,
                    "after_tokens": retrieval_tokens,
                    "dropped_doc_ids": dropped_ids,
                }
            )

        # Tool results trimming
        tool_tokens = 0
        tool_entries: List[Dict[str, Any]] = []
        for item in tool_items:
            content = (item.get("content") or "").strip()
            if not content:
                continue
            entry = {
                "id": item.get("id") or item.get("tool_call_id") or item.get("name") or "tool",
                "content": content,
            }
            entry_tokens = self.counter.count_text(entry["content"], model)
            entry["tokens"] = entry_tokens
            tool_entries.append(entry)
            tool_tokens += entry_tokens

        tool_header_tokens = self.counter.count_text("## Tool Results", model) if tool_entries else 0
        tool_tokens += tool_header_tokens

        if tool_tokens > budgets["tool_results"]:
            before_tokens = tool_tokens
            for entry in tool_entries:
                if tool_tokens <= budgets["tool_results"]:
                    break
                reduce_needed = tool_tokens - budgets["tool_results"]
                target = max(int(entry["tokens"]) - reduce_needed, 0)
                entry["content"] = _truncate_tool_text(entry["content"], target, self.counter, model)
                new_tokens = self.counter.count_text(entry["content"], model)
                tool_tokens = tool_tokens - int(entry["tokens"]) + new_tokens
                entry["tokens"] = new_tokens

            trimming_applied.append(
                {
                    "action": "truncate_tool_outputs",
                    "before_tokens": before_tokens,
                    "after_tokens": tool_tokens,
                }
            )

        # Memory summarization
        memory_tokens = self.counter.count_text(memory_text, model)
        if memory_text:
            memory_tokens += self.counter.count_text("## Memory", model)
        if memory_tokens > budgets["memory"]:
            before_tokens = memory_tokens
            memory_text = _summarize_memory(memory_text, budgets["memory"], self.counter, model)
            memory_tokens = self.counter.count_text(memory_text, model)
            if memory_text:
                memory_tokens += self.counter.count_text("## Memory", model)
            trimming_applied.append(
                {
                    "action": "summarize_memory",
                    "before_tokens": before_tokens,
                    "after_tokens": memory_tokens,
                }
            )

        # Assemble messages
        messages: List[Dict[str, str]] = []
        if system_text:
            messages.append({"role": "system", "content": system_text})
        if developer_text:
            messages.append({"role": "system", "content": developer_text})
        if memory_text:
            messages.append({"role": "system", "content": f"## Memory\\n{memory_text}"})
        if history_messages:
            for msg in history_messages:
                role = msg.get("role") or "user"
                content = msg.get("content") or ""
                messages.append({"role": "user" if role == "user" else "assistant", "content": content})
        if retrieval_entries:
            retrieval_block = ["## Retrieval Context"]
            for entry in retrieval_entries:
                retrieval_block.append(f"[{entry['id']}] {entry['content']}")
            messages.append({"role": "system", "content": "\\n\\n".join(retrieval_block)})
        if tool_entries:
            tool_block = ["## Tool Results"]
            for entry in tool_entries:
                tool_block.append(f"[{entry['id']}]\\n{entry['content']}")
            messages.append({"role": "system", "content": "\\n\\n".join(tool_block)})
        if user_message:
            messages.append({"role": "user", "content": user_message})

        input_tokens_estimated = self.counter.count_messages(messages, model)
        total_input = input_tokens_estimated

        if total_input > max_input_tokens:
            error = (
                f"Context still exceeds window after trimming "
                f"({total_input} > {max_input_tokens})."
            )
            return BuildResult(
                messages=[],
                component_tokens={
                    "system": system_tokens,
                    "developer": developer_tokens,
                    "memory": memory_tokens,
                    "history": history_tokens,
                    "retrieval": retrieval_tokens,
                    "tool_results": tool_tokens,
                    "other": self.counter.count_text(user_message, model),
                },
                included_summary={},
                trimming_applied=trimming_applied,
                status="blocked",
                error=error,
                input_tokens_estimated=total_input,
                headroom=0,
                model=model,
                provider=provider,
                reserved_output_tokens=reserved_output_tokens,
                context_window_tokens=context_window_tokens,
            )

        headroom = context_window_tokens - (total_input + reserved_output_tokens)
        if headroom < 0:
            headroom = 0

        history_ids = [str(m.get("id")) for m in history_messages if m.get("id")]
        history_token_counts = [
            self.counter.count_text(m.get("content", ""), model) + 4 for m in history_messages
        ]
        retrieval_ids = [str(e.get("id")) for e in retrieval_entries]
        retrieval_token_counts = [int(e.get("tokens") or 0) for e in retrieval_entries]
        tool_ids = [str(e.get("id")) for e in tool_entries]
        tool_token_counts = [int(e.get("tokens") or 0) for e in tool_entries]

        def _preview(text: str) -> Dict[str, str]:
            if not text:
                return {"head": "", "tail": ""}
            return {"head": text[:300], "tail": text[-300:] if len(text) > 300 else text}

        included_summary = {
            "system": {"tokens": system_tokens, "chars": len(system_text)},
            "developer": {"tokens": developer_tokens, "chars": len(developer_text)},
            "memory": {"tokens": memory_tokens, "chars": len(memory_text)},
            "history": {
                "message_ids": history_ids,
                "count": len(history_messages),
                "tokens": history_tokens,
                "token_counts": history_token_counts,
            },
            "retrieval": {
                "doc_ids": retrieval_ids,
                "count": len(retrieval_entries),
                "tokens": retrieval_tokens,
                "token_counts": retrieval_token_counts,
                "header_tokens": retrieval_header_tokens,
            },
            "tool_results": {
                "tool_call_ids": tool_ids,
                "count": len(tool_entries),
                "tokens": tool_tokens,
                "token_counts": tool_token_counts,
                "header_tokens": tool_header_tokens,
            },
            "user_message": {
                "tokens": self.counter.count_text(user_message, model),
                "chars": len(user_message),
            },
            "prompt_preview": {
                "system": _preview(system_text),
                "developer": _preview(developer_text),
                "memory": _preview(memory_text),
                "history": _preview("\\n".join(m.get("content", "") for m in history_messages)),
                "retrieval": _preview("\\n".join(e.get("content", "") for e in retrieval_entries)),
                "tool_results": _preview("\\n".join(e.get("content", "") for e in tool_entries)),
                "user_message": _preview(user_message),
            },
        }

        component_tokens = {
            "system": system_tokens,
            "developer": developer_tokens,
            "memory": memory_tokens,
            "history": history_tokens,
            "retrieval": retrieval_tokens,
            "tool_results": tool_tokens,
            "other": self.counter.count_text(user_message, model),
        }

        status = "trimmed" if trimming_applied else "ok"

        return BuildResult(
            messages=messages,
            component_tokens=component_tokens,
            included_summary=included_summary,
            trimming_applied=trimming_applied,
            status=status,
            error=None,
            input_tokens_estimated=total_input,
            headroom=headroom,
            model=model,
            provider=provider,
            reserved_output_tokens=reserved_output_tokens,
            context_window_tokens=context_window_tokens,
        )

    async def run(
        self,
        agent_name: str,
        build_input: BuildInput,
        request_id: Optional[str] = None,
        temperature: float = 1.0,
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        build = self.build(agent_name, build_input, request_id=request_id)
        profile = get_or_create_agent_profile(self.db, agent_name)

        if build.status == "blocked":
            run = self._record_run(
                profile=profile,
                request_id=request_id,
                build=build,
                response_text="",
                usage=None,
                status="blocked",
                error_message=build.error,
            )
            return {
                "status": "blocked",
                "response": None,
                "error": build.error,
                "build": build,
                "run": run,
            }

        llm = get_llm_client()
        if not llm.is_available():
            run = self._record_run(
                profile=profile,
                request_id=request_id,
                build=build,
                response_text="",
                usage=None,
                status="error",
                error_message="LLM not available",
            )
            return {
                "status": "error",
                "response": None,
                "error": "LLM not available",
                "build": build,
                "run": run,
            }

        try:
            result = await llm.chat_messages_routed(
                agent_id=agent_name,
                messages=build.messages,
                max_tokens=build.reserved_output_tokens,
                temperature=temperature,
                force_model=force_model,
            )
            response_text = result.get("response") or ""
            usage = result.get("usage")
            routing = result.get("routing")
            model_used = result.get("model_used") or build.model
            provider = result.get("provider") or build.provider
            build.model = model_used
            build.provider = provider

            run = self._record_run(
                profile=profile,
                request_id=request_id,
                build=build,
                response_text=response_text,
                usage=usage,
                status=build.status,
                error_message=None,
            )
            return {
                "status": build.status,
                "response": response_text,
                "error": None,
                "build": build,
                "run": run,
                "usage": usage,
                "model_used": model_used,
                "routing": routing,
            }
        except Exception as exc:
            run = self._record_run(
                profile=profile,
                request_id=request_id,
                build=build,
                response_text="",
                usage=None,
                status="error",
                error_message=str(exc),
            )
            return {
                "status": "error",
                "response": None,
                "error": str(exc),
                "build": build,
                "run": run,
            }

    def _record_run(
        self,
        profile,
        request_id: Optional[str],
        build: BuildResult,
        response_text: str,
        usage: Optional[Dict[str, Any]],
        status: str,
        error_message: Optional[str],
    ) -> LLMRun:
        output_estimated = self.counter.count_text(response_text or "", build.model)
        input_measured = None
        output_measured = None
        if usage:
            input_measured = usage.get("input_tokens") or usage.get("prompt_tokens")
            output_measured = usage.get("output_tokens") or usage.get("completion_tokens")

        run = LLMRun(
            agent_id=profile.id,
            request_id=request_id,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            model=build.model,
            provider=build.provider,
            input_tokens_measured=input_measured,
            output_tokens_measured=output_measured,
            input_tokens_estimated=build.input_tokens_estimated,
            output_tokens_estimated=output_estimated,
            component_tokens_json=build.component_tokens,
            included_summary_json=build.included_summary,
            trimming_applied_json=build.trimming_applied,
            status=status,
            error_json={"message": error_message} if error_message else None,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        snapshot = AgentContextSnapshot(
            agent_id=profile.id,
            snapshot_json={
                "budgets": normalize_budgets(profile.budgets_json or {}),
                "context_window_tokens": build.context_window_tokens,
                "reserved_output_tokens": build.reserved_output_tokens,
                "headroom": build.headroom,
                "status": status,
                "recorded_at": datetime.utcnow().isoformat(),
            },
        )
        self.db.add(snapshot)
        self.db.commit()
        return run


__all__ = [
    "BuildInput",
    "BuildResult",
    "RequestBuilder",
    "TokenCounter",
]
