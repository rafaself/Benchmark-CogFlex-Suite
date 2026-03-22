from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

__all__ = [
    "ModelMode",
    "ModelRunConfig",
    "ModelUsage",
    "ModelRequest",
    "ModelRawResult",
    "ModelExecutionRecord",
    "ModelAdapter",
]


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


class ModelMode(StrEnum):
    BINARY = "binary"
    NARRATIVE = "narrative"


@dataclass(frozen=True, slots=True)
class ModelRunConfig:
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive or None")


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        for field_name in ("input_tokens", "output_tokens", "total_tokens"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative or None")


@dataclass(frozen=True, slots=True)
class ModelRequest:
    provider_name: str
    model_name: str
    prompt_text: str
    mode: ModelMode

    def __post_init__(self) -> None:
        if not _is_nonempty_string(self.provider_name):
            raise ValueError("provider_name must be a non-empty string")
        if not _is_nonempty_string(self.model_name):
            raise ValueError("model_name must be a non-empty string")
        if not _is_nonempty_string(self.prompt_text):
            raise ValueError("prompt_text must be a non-empty string")
        object.__setattr__(self, "mode", ModelMode(self.mode))


@dataclass(frozen=True, slots=True)
class ModelRawResult:
    provider_name: str
    model_name: str
    mode: ModelMode
    response_text: str | None = None
    duration_seconds: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    usage: ModelUsage | None = None

    def __post_init__(self) -> None:
        if not _is_nonempty_string(self.provider_name):
            raise ValueError("provider_name must be a non-empty string")
        if not _is_nonempty_string(self.model_name):
            raise ValueError("model_name must be a non-empty string")
        object.__setattr__(self, "mode", ModelMode(self.mode))
        if self.response_text is not None and not isinstance(self.response_text, str):
            raise TypeError("response_text must be a string or None")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative or None")
        if self.error_type is not None and not _is_nonempty_string(self.error_type):
            raise ValueError("error_type must be a non-empty string or None")
        if self.error_message is not None and not isinstance(self.error_message, str):
            raise TypeError("error_message must be a string or None")
        if self.usage is not None and not isinstance(self.usage, ModelUsage):
            raise TypeError("usage must be a ModelUsage or None")

    @property
    def succeeded(self) -> bool:
        return self.error_type is None

    @classmethod
    def from_request(
        cls,
        request: ModelRequest,
        *,
        response_text: str | None = None,
        duration_seconds: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        usage: ModelUsage | None = None,
    ) -> "ModelRawResult":
        return cls(
            provider_name=request.provider_name,
            model_name=request.model_name,
            mode=request.mode,
            response_text=response_text,
            duration_seconds=duration_seconds,
            error_type=error_type,
            error_message=error_message,
            usage=usage,
        )


@dataclass(frozen=True, slots=True)
class ModelExecutionRecord:
    request: ModelRequest
    config: ModelRunConfig
    raw_result: ModelRawResult

    def __post_init__(self) -> None:
        if not isinstance(self.request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        if not isinstance(self.config, ModelRunConfig):
            raise TypeError("config must be a ModelRunConfig")
        if not isinstance(self.raw_result, ModelRawResult):
            raise TypeError("raw_result must be a ModelRawResult")


@runtime_checkable
class ModelAdapter(Protocol):
    def generate(
        self,
        request: ModelRequest,
        config: ModelRunConfig,
    ) -> ModelRawResult: ...
