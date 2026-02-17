import pytest

from core.agent_profiles import get_or_create_agent_profile
from core.request_builder import RequestBuilder, BuildInput
from database.models import LLMRun


def _make_text(char_count: int) -> str:
    return "x" * char_count


@pytest.mark.unit
def test_trimming_order_and_determinism(db_session):
    profile = get_or_create_agent_profile(db_session, "manager")
    profile.context_window_tokens = 4096
    profile.reserved_output_tokens = 256
    profile.budgets_json = {
        "system": 2000,
        "memory": 40,
        "history": 40,
        "retrieval": 40,
        "tool_results": 40,
        "safety_margin": 0,
    }
    db_session.add(profile)
    db_session.commit()

    builder = RequestBuilder(db_session)
    build_input = BuildInput(
        system_prompt="System ok",
        developer_prompt="Developer ok",
        memory=_make_text(500),
        history=[
            {"role": "user", "content": _make_text(300)},
            {"role": "assistant", "content": _make_text(300)},
            {"role": "user", "content": _make_text(300)},
        ],
        retrieval=[
            {"id": "doc1", "content": _make_text(300)},
            {"id": "doc2", "content": _make_text(300)},
        ],
        tool_results=[
            {"id": "tool1", "content": _make_text(400)},
        ],
        user_message="hello",
    )

    first = builder.build("manager", build_input)
    second = builder.build("manager", build_input)

    actions = [a["action"] for a in first.trimming_applied]
    assert actions[:4] == [
        "drop_history_before",
        "reduce_retrieval",
        "truncate_tool_outputs",
        "summarize_memory",
    ]
    assert first.trimming_applied == second.trimming_applied


@pytest.mark.unit
def test_block_on_system_prompt_over_budget(db_session):
    profile = get_or_create_agent_profile(db_session, "finance")
    profile.context_window_tokens = 4096
    profile.reserved_output_tokens = 256
    profile.budgets_json = {
        "system": 10,
        "memory": 100,
        "history": 100,
        "retrieval": 100,
        "tool_results": 100,
        "safety_margin": 0,
    }
    db_session.add(profile)
    db_session.commit()

    builder = RequestBuilder(db_session)
    build_input = BuildInput(
        system_prompt=_make_text(200),
        developer_prompt="dev",
        memory="",
        history=[],
        retrieval=[],
        tool_results=[],
        user_message="test",
    )

    result = builder.build("finance", build_input)
    assert result.status == "blocked"
    assert "system" in (result.error or "").lower()


@pytest.mark.unit
def test_headroom_calculation(db_session):
    profile = get_or_create_agent_profile(db_session, "janitor")
    profile.context_window_tokens = 2000
    profile.reserved_output_tokens = 200
    profile.budgets_json = {
        "system": 2000,
        "memory": 2000,
        "history": 2000,
        "retrieval": 2000,
        "tool_results": 2000,
        "safety_margin": 0,
    }
    db_session.add(profile)
    db_session.commit()

    builder = RequestBuilder(db_session)
    build_input = BuildInput(
        system_prompt="System ok",
        developer_prompt="Developer ok",
        memory="",
        history=[],
        retrieval=[],
        tool_results=[],
        user_message=_make_text(200),
    )
    result = builder.build("janitor", build_input)
    assert result.status in {"ok", "trimmed"}
    expected_headroom = profile.context_window_tokens - (
        result.input_tokens_estimated + profile.reserved_output_tokens
    )
    assert result.headroom == max(expected_headroom, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_runs_persistence(db_session, monkeypatch):
    profile = get_or_create_agent_profile(db_session, "projects")
    profile.context_window_tokens = 4096
    profile.reserved_output_tokens = 256
    profile.budgets_json = {
        "system": 2000,
        "memory": 2000,
        "history": 2000,
        "retrieval": 2000,
        "tool_results": 2000,
        "safety_margin": 0,
    }
    db_session.add(profile)
    db_session.commit()

    class DummyLLM:
        provider = "openai"
        model = "dummy"

        def is_available(self):
            return True

        async def chat_messages_routed(self, **kwargs):
            return {
                "response": "ok",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "model_used": "dummy",
                "provider": "openai",
                "routing": {"tier": "simple", "score": 0.1, "confidence": 1.0, "factors": {}, "recommended_model": "dummy"},
            }

    monkeypatch.setattr("core.llm_client.get_llm_client", lambda: DummyLLM())

    builder = RequestBuilder(db_session)
    build_input = BuildInput(
        system_prompt="System ok",
        developer_prompt="Developer ok",
        memory="",
        history=[],
        retrieval=[],
        tool_results=[],
        user_message="hello",
    )
    result = await builder.run("projects", build_input, request_id="test-run")
    assert result["status"] in {"ok", "trimmed"}

    run = db_session.query(LLMRun).filter(LLMRun.request_id == "test-run").first()
    assert run is not None
    assert run.trimming_applied_json is not None
    assert run.component_tokens_json is not None
