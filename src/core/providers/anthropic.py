from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import os
from pathlib import Path
import time

from core.model_execution import (
    ModelExecutionOutcome,
    ModelMode,
    ModelRawResult,
    ModelRequest,
    ModelRunConfig,
    ModelUsage,
)

__all__ = [
    "ANTHROPIC_API_KEY_ENV_VAR",
    "AnthropicConfigurationError",
    "MissingAnthropicApiKeyError",
    "MissingAnthropicSdkError",
    "AnthropicAdapter",
]

ANTHROPIC_API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
_DEFAULT_TEMPERATURE = 0.0
_DEFAULT_MAX_TOKENS = 4096
_BINARY_JSON_SUFFIX = (
    '\n\nReturn the final answer as JSON with one key named "labels". '
    "Its value must be an array of 4 strings in probe order. "
    'Each string must be either "attract" or "repel".'
)


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


class AnthropicConfigurationError(RuntimeError):
    """Raised when Anthropic execution is not configured correctly."""


class MissingAnthropicApiKeyError(AnthropicConfigurationError):
    """Raised when ANTHROPIC_API_KEY is not available."""


class MissingAnthropicSdkError(AnthropicConfigurationError):
    """Raised when anthropic is not installed."""


class AnthropicAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        client: object | None = None,
        client_factory: Callable[[str], object] | None = None,
    ) -> None:
        if not _is_nonempty_string(api_key):
            raise MissingAnthropicApiKeyError(
                f"{ANTHROPIC_API_KEY_ENV_VAR} must be set to run Anthropic benchmark panels."
            )
        self._api_key = api_key
        self._client = client
        self._client_factory = client_factory

    @classmethod
    def from_env(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        client: object | None = None,
        client_factory: Callable[[str], object] | None = None,
    ) -> "AnthropicAdapter":
        normalized_env = _build_env_mapping(env)
        api_key = normalized_env.get(ANTHROPIC_API_KEY_ENV_VAR, "").strip()
        if not api_key:
            raise MissingAnthropicApiKeyError(
                f"{ANTHROPIC_API_KEY_ENV_VAR} is not set. Export {ANTHROPIC_API_KEY_ENV_VAR} or "
                "add it to the repo-root `.env`, then rerun `ife anthropic-panel`."
            )
        return cls(
            api_key=api_key,
            client=client,
            client_factory=client_factory,
        )

    def generate(
        self,
        request: ModelRequest,
        config: ModelRunConfig,
    ) -> ModelRawResult:
        started_at = time.perf_counter()
        try:
            kwargs: dict[str, object] = {}
            if config.timeout_seconds is not None:
                kwargs["timeout"] = config.timeout_seconds
            message = self._client_instance().messages.create(
                model=request.model_name,
                max_tokens=_DEFAULT_MAX_TOKENS,
                temperature=(
                    _DEFAULT_TEMPERATURE
                    if config.temperature is None
                    else config.temperature
                ),
                messages=[
                    {"role": "user", "content": self._render_contents(request)}
                ],
                **kwargs,
            )
        except Exception as exc:
            return ModelRawResult.from_request(
                request,
                execution_outcome=ModelExecutionOutcome.PROVIDER_FAILURE,
                duration_seconds=time.perf_counter() - started_at,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

        return ModelRawResult.from_request(
            request,
            response_text=self._extract_response_text(request, message),
            duration_seconds=time.perf_counter() - started_at,
            usage=self._extract_usage(message),
            response_id=self._extract_string_attr(message, "id"),
            provider_model_version=self._extract_string_attr(message, "model"),
            finish_reason=self._extract_finish_reason(message),
        )

    def _client_instance(self) -> object:
        if self._client is None:
            factory = self._client_factory or _default_client_factory
            self._client = factory(self._api_key)
        return self._client

    def _render_contents(self, request: ModelRequest) -> str:
        if request.mode is ModelMode.BINARY:
            return request.prompt_text + _BINARY_JSON_SUFFIX
        return request.prompt_text

    def _extract_response_text(
        self, request: ModelRequest, message: object
    ) -> str | None:
        text = _extract_text_from_content(getattr(message, "content", None))
        if text is None:
            return None
        if request.mode is ModelMode.BINARY:
            labels = _extract_binary_labels_from_text(text)
            if labels is not None:
                return ", ".join(labels)
        return text

    def _extract_usage(self, message: object) -> ModelUsage | None:
        usage = getattr(message, "usage", None)
        if usage is None:
            return None
        return ModelUsage(
            input_tokens=_read_int_attr(usage, "input_tokens"),
            output_tokens=_read_int_attr(usage, "output_tokens"),
        )

    def _extract_string_attr(self, message: object, attr_name: str) -> str | None:
        value = getattr(message, attr_name, None)
        if _is_nonempty_string(value):
            return value.strip()
        return None

    def _extract_finish_reason(self, message: object) -> str | None:
        value = getattr(message, "stop_reason", None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None


def _default_client_factory(api_key: str) -> object:
    try:
        import anthropic
    except ImportError as exc:
        raise MissingAnthropicSdkError(
            "anthropic is not installed. Install project dependencies before running "
            "the Anthropic benchmark panel."
        ) from exc
    return anthropic.Anthropic(api_key=api_key)


def _build_env_mapping(env: Mapping[str, str] | None) -> dict[str, str]:
    normalized_env = _load_repo_root_dotenv()
    normalized_env.update(os.environ)
    if env is not None:
        normalized_env.update(env)
    return normalized_env


def _load_repo_root_dotenv() -> dict[str, str]:
    dotenv_path = _repo_root() / ".env"
    if not dotenv_path.is_file():
        return {}

    parsed: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            continue
        parsed[normalized_key] = _parse_dotenv_value(value)
    return parsed


def _parse_dotenv_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        return stripped[1:-1]
    return stripped


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_int_attr(value: object, attr_name: str) -> int | None:
    candidate = getattr(value, attr_name, None)
    if isinstance(candidate, int) and not isinstance(candidate, bool):
        return candidate
    return None


def _extract_text_from_content(content: object) -> str | None:
    if not isinstance(content, (list, tuple)):
        return None
    text_parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) != "text":
            continue
        text = getattr(block, "text", None)
        if _is_nonempty_string(text):
            text_parts.append(text.strip())
    if not text_parts:
        return None
    return "\n".join(text_parts)


def _extract_binary_labels_from_text(text: str) -> tuple[str, ...] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return _extract_binary_labels(payload)


def _extract_binary_labels(payload: object) -> tuple[str, ...] | None:
    if not isinstance(payload, Mapping):
        return None
    labels = payload.get("labels")
    if not isinstance(labels, (list, tuple)):
        return None
    normalized = tuple(str(label).strip().lower() for label in labels)
    if not normalized:
        return None
    return normalized
