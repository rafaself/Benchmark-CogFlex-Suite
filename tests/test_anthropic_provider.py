from __future__ import annotations

from pathlib import Path

import pytest

from core.model_execution import ModelExecutionOutcome, ModelMode, ModelRequest, ModelRunConfig
from core.providers.anthropic import (
    ANTHROPIC_API_KEY_ENV_VAR,
    AnthropicAdapter,
    MissingAnthropicApiKeyError,
    MissingAnthropicSdkError,
)


class _FakeUsage:
    input_tokens = 15
    output_tokens = 10


class _FakeTextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeMessage:
    def __init__(
        self,
        *,
        content: list[object],
        stop_reason: str = "end_turn",
        usage: object | None = None,
        id: str = "msg-abc123",
        model: str = "claude-3-5-haiku-20241022",
    ) -> None:
        self.content = content
        self.stop_reason = stop_reason
        self.usage = usage or _FakeUsage()
        self.id = id
        self.model = model


class _FakeMessages:
    def __init__(
        self,
        *,
        message: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self.message = message
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.message


class _FakeAnthropicClient:
    def __init__(self, *, messages: _FakeMessages) -> None:
        self.messages = messages


def test_anthropic_adapter_maps_binary_json_response_to_labels():
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[
                _FakeTextBlock('{"labels": ["attract", "repel", "repel", "attract"]}')
            ],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    adapter = AnthropicAdapter(
        api_key="test-key",
        client=client,
    )

    request = ModelRequest(
        provider_name="anthropic",
        model_name="claude-3-5-haiku-20241022",
        prompt_text="Benchmark prompt",
        mode=ModelMode.BINARY,
    )
    result = adapter.generate(
        request,
        ModelRunConfig(timeout_seconds=60.0, temperature=0.0, thinking_budget=0),
    )

    assert result.succeeded is True
    assert result.execution_outcome is ModelExecutionOutcome.COMPLETED
    assert result.response_text == "attract, repel, repel, attract"
    assert result.usage is not None
    assert result.usage.input_tokens == 15
    assert result.usage.output_tokens == 10
    assert result.response_id == "msg-abc123"
    assert result.provider_model_version == "claude-3-5-haiku-20241022"
    assert result.finish_reason == "end_turn"

    assert len(messages.calls) == 1
    call = messages.calls[0]
    assert call["model"] == "claude-3-5-haiku-20241022"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 4096
    assert call["timeout"] == 60.0
    prompt_content = call["messages"][0]["content"]
    assert "Benchmark prompt" in prompt_content
    assert '"labels"' in prompt_content


def test_anthropic_adapter_returns_raw_text_for_narrative_mode():
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[
                _FakeTextBlock("Reasoning.\nattract, repel, repel, attract")
            ],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    adapter = AnthropicAdapter(api_key="test-key", client=client)

    request = ModelRequest(
        provider_name="anthropic",
        model_name="claude-3-5-haiku-20241022",
        prompt_text="Narrative prompt",
        mode=ModelMode.NARRATIVE,
    )
    result = adapter.generate(request, ModelRunConfig())

    assert result.succeeded is True
    assert result.response_text == "Reasoning.\nattract, repel, repel, attract"

    call = messages.calls[0]
    prompt_content = call["messages"][0]["content"]
    assert "Narrative prompt" in prompt_content
    assert '"labels"' not in prompt_content


def test_anthropic_adapter_returns_raw_text_when_binary_json_is_malformed():
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[_FakeTextBlock("attract, repel, repel, attract")],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    adapter = AnthropicAdapter(api_key="test-key", client=client)

    request = ModelRequest(
        provider_name="anthropic",
        model_name="claude-3-5-haiku-20241022",
        prompt_text="Benchmark prompt",
        mode=ModelMode.BINARY,
    )
    result = adapter.generate(request, ModelRunConfig())

    assert result.succeeded is True
    assert result.response_text == "attract, repel, repel, attract"


def test_anthropic_adapter_returns_provider_failure_on_exception():
    messages = _FakeMessages(error=RuntimeError("provider exploded"))
    client = _FakeAnthropicClient(messages=messages)
    adapter = AnthropicAdapter(api_key="test-key", client=client)

    request = ModelRequest(
        provider_name="anthropic",
        model_name="claude-3-5-haiku-20241022",
        prompt_text="Benchmark prompt",
        mode=ModelMode.BINARY,
    )
    result = adapter.generate(request, ModelRunConfig())

    assert result.succeeded is False
    assert result.execution_outcome is ModelExecutionOutcome.PROVIDER_FAILURE
    assert result.error_type == "RuntimeError"
    assert result.error_message == "provider exploded"
    assert result.response_text is None


def test_anthropic_adapter_fails_clearly_when_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.delenv(ANTHROPIC_API_KEY_ENV_VAR, raising=False)
    monkeypatch.setattr("core.providers.anthropic._repo_root", lambda: tmp_path)

    with pytest.raises(MissingAnthropicApiKeyError) as excinfo:
        AnthropicAdapter.from_env(env={})

    assert ANTHROPIC_API_KEY_ENV_VAR in str(excinfo.value)


def test_anthropic_adapter_reads_api_key_from_env(
    monkeypatch: pytest.MonkeyPatch,
):
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[
                _FakeTextBlock('{"labels": ["attract", "repel", "repel", "attract"]}')
            ],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    monkeypatch.setenv(ANTHROPIC_API_KEY_ENV_VAR, "env-key")

    adapter = AnthropicAdapter.from_env(client=client)
    result = adapter.generate(
        ModelRequest(
            provider_name="anthropic",
            model_name="claude-3-5-haiku-20241022",
            prompt_text="Benchmark prompt",
            mode=ModelMode.BINARY,
        ),
        ModelRunConfig(),
    )

    assert result.succeeded is True
    assert adapter._api_key == "env-key"


def test_anthropic_adapter_reads_api_key_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[
                _FakeTextBlock('{"labels": ["attract", "repel", "repel", "attract"]}')
            ],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    monkeypatch.delenv(ANTHROPIC_API_KEY_ENV_VAR, raising=False)
    (tmp_path / ".env").write_text(
        "ANTHROPIC_API_KEY=dotenv-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("core.providers.anthropic._repo_root", lambda: tmp_path)

    adapter = AnthropicAdapter.from_env(client=client)
    result = adapter.generate(
        ModelRequest(
            provider_name="anthropic",
            model_name="claude-3-5-haiku-20241022",
            prompt_text="Benchmark prompt",
            mode=ModelMode.BINARY,
        ),
        ModelRunConfig(),
    )

    assert result.succeeded is True
    assert adapter._api_key == "dotenv-key"


def test_anthropic_adapter_ignores_thinking_budget():
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[
                _FakeTextBlock('{"labels": ["attract", "repel", "repel", "attract"]}')
            ],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    adapter = AnthropicAdapter(api_key="test-key", client=client)

    result = adapter.generate(
        ModelRequest(
            provider_name="anthropic",
            model_name="claude-3-5-haiku-20241022",
            prompt_text="Benchmark prompt",
            mode=ModelMode.BINARY,
        ),
        ModelRunConfig(thinking_budget=1024),
    )

    assert result.succeeded is True
    call = messages.calls[0]
    assert "thinking_budget" not in call
    assert "thinking_config" not in call


def test_anthropic_adapter_omits_timeout_when_not_configured():
    messages = _FakeMessages(
        message=_FakeMessage(
            content=[
                _FakeTextBlock('{"labels": ["attract", "repel", "repel", "attract"]}')
            ],
        )
    )
    client = _FakeAnthropicClient(messages=messages)
    adapter = AnthropicAdapter(api_key="test-key", client=client)

    adapter.generate(
        ModelRequest(
            provider_name="anthropic",
            model_name="claude-3-5-haiku-20241022",
            prompt_text="Benchmark prompt",
            mode=ModelMode.BINARY,
        ),
        ModelRunConfig(),
    )

    call = messages.calls[0]
    assert "timeout" not in call
