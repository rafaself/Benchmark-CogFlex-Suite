from __future__ import annotations

from dataclasses import dataclass
from core.kaggle.run_logging import BenchmarkRunLogger
from core.kaggle.types import (
    BinaryResponse,
    parse_binary_response,
    parse_narrative_response,
    score_episode,
)
from core.parser import (
    NarrativeParsedResult,
    NarrativeParseStatus,
    ParseStatus,
    ParsedPrediction,
)
from tasks.ruleshift_benchmark.protocol import PROBE_COUNT

__all__ = [
    "OPERATIONAL_FAILURE_STATUS",
    "BinaryEpisodeExecution",
    "NarrativeEpisodeExecution",
    "run_binary_episode",
    "run_narrative_episode",
]

OPERATIONAL_FAILURE_STATUS = "operational_failure"


@dataclass(frozen=True, slots=True)
class BinaryEpisodeExecution:
    parsed_prediction: ParsedPrediction
    score: tuple[int, int]
    status: str


@dataclass(frozen=True, slots=True)
class NarrativeEpisodeExecution:
    parsed_result: NarrativeParsedResult
    score: tuple[int, int]
    status: str


def run_binary_episode(
    *,
    llm: object,
    prompt_binary: str,
    probe_targets: tuple,
    logger: BenchmarkRunLogger,
    phase: str,
    task_mode: str,
    episode_id: str | None,
) -> BinaryEpisodeExecution:
    logger.log_episode_started(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
    )
    logger.log_provider_call_started(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
    )

    try:
        response = llm.prompt(prompt_binary, schema=BinaryResponse)
    except Exception as exc:
        return _binary_operational_failure(
            exc,
            logger=logger,
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            failure_stage="provider_call",
        )

    logger.log_provider_call_succeeded(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
    )

    try:
        parsed_prediction = parse_binary_response(response)
    except Exception as exc:
        return _binary_operational_failure(
            exc,
            logger=logger,
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            failure_stage="response_parse",
        )

    if parsed_prediction.status is ParseStatus.VALID:
        logger.log_response_parsed(
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            status=parsed_prediction.status.value,
            parse_status=parsed_prediction.status.value,
        )
    else:
        logger.log_response_parse_failed(
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            status=parsed_prediction.status.value,
            parse_status=parsed_prediction.status.value,
        )

    try:
        predictions = (
            tuple(label.value for label in parsed_prediction.labels)
            if parsed_prediction.status is ParseStatus.VALID
            else None
        )
        score = score_episode(predictions, probe_targets)
    except Exception as exc:
        return _binary_operational_failure(
            exc,
            logger=logger,
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            failure_stage="episode_scoring",
        )

    logger.log_episode_scored(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        level="info" if parsed_prediction.status is ParseStatus.VALID else "warning",
        status=parsed_prediction.status.value,
        num_correct=score[0],
        total=score[1],
    )
    return BinaryEpisodeExecution(
        parsed_prediction=parsed_prediction,
        score=score,
        status=parsed_prediction.status.value,
    )


def run_narrative_episode(
    *,
    llm: object,
    prompt_narrative: str,
    probe_targets: tuple,
    logger: BenchmarkRunLogger,
    phase: str,
    task_mode: str,
    episode_id: str | None,
) -> NarrativeEpisodeExecution:
    logger.log_episode_started(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
    )
    logger.log_provider_call_started(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
    )

    try:
        response = llm.prompt(prompt_narrative)
    except Exception as exc:
        return _narrative_operational_failure(
            exc,
            logger=logger,
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            failure_stage="provider_call",
        )

    logger.log_provider_call_succeeded(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
    )

    try:
        parsed_result = parse_narrative_response(response)
    except Exception as exc:
        return _narrative_operational_failure(
            exc,
            logger=logger,
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            failure_stage="response_parse",
        )

    if parsed_result.status is NarrativeParseStatus.VALID:
        logger.log_response_parsed(
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            status=parsed_result.status.value,
            parse_status=parsed_result.status.value,
        )
    else:
        logger.log_response_parse_failed(
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            status=parsed_result.status.value,
            parse_status=parsed_result.status.value,
            failure_detail=parsed_result.failure_detail,
        )

    try:
        predictions = (
            tuple(label.value for label in parsed_result.output.final_decision)
            if parsed_result.status is NarrativeParseStatus.VALID and parsed_result.output is not None
            else None
        )
        score = score_episode(predictions, probe_targets)
    except Exception as exc:
        return _narrative_operational_failure(
            exc,
            logger=logger,
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            failure_stage="episode_scoring",
        )

    logger.log_episode_scored(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        level="info" if parsed_result.status is NarrativeParseStatus.VALID else "warning",
        status=parsed_result.status.value,
        num_correct=score[0],
        total=score[1],
    )
    return NarrativeEpisodeExecution(
        parsed_result=parsed_result,
        score=score,
        status=parsed_result.status.value,
    )


def _binary_operational_failure(
    exc: BaseException,
    *,
    logger: BenchmarkRunLogger,
    phase: str,
    task_mode: str,
    episode_id: str | None,
    failure_stage: str,
) -> BinaryEpisodeExecution:
    _log_operational_failure(
        exc,
        logger=logger,
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        failure_stage=failure_stage,
    )
    score = (0, PROBE_COUNT)
    logger.log_episode_scored(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        level="error",
        status=OPERATIONAL_FAILURE_STATUS,
        num_correct=score[0],
        total=score[1],
        failure_stage=failure_stage,
    )
    return BinaryEpisodeExecution(
        parsed_prediction=ParsedPrediction.skipped_provider_failure(),
        score=score,
        status=OPERATIONAL_FAILURE_STATUS,
    )


def _narrative_operational_failure(
    exc: BaseException,
    *,
    logger: BenchmarkRunLogger,
    phase: str,
    task_mode: str,
    episode_id: str | None,
    failure_stage: str,
) -> NarrativeEpisodeExecution:
    _log_operational_failure(
        exc,
        logger=logger,
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        failure_stage=failure_stage,
    )
    score = (0, PROBE_COUNT)
    logger.log_episode_scored(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        level="error",
        status=OPERATIONAL_FAILURE_STATUS,
        num_correct=score[0],
        total=score[1],
        failure_stage=failure_stage,
    )
    return NarrativeEpisodeExecution(
        parsed_result=NarrativeParsedResult.skipped_provider_failure(),
        score=score,
        status=OPERATIONAL_FAILURE_STATUS,
    )


def _log_operational_failure(
    exc: BaseException,
    *,
    logger: BenchmarkRunLogger,
    phase: str,
    task_mode: str,
    episode_id: str | None,
    failure_stage: str,
) -> None:
    detail = _format_operational_failure_detail(failure_stage, exc)
    if failure_stage == "provider_call":
        logger.log_provider_call_failed(
            phase=phase,
            task_mode=task_mode,
            episode_id=episode_id,
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            failure_stage=failure_stage,
            detail=detail,
        )
    logger.log_exception(
        exc,
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        failure_stage=failure_stage,
    )
    logger.log_response_parse_failed(
        phase=phase,
        task_mode=task_mode,
        episode_id=episode_id,
        status=OPERATIONAL_FAILURE_STATUS,
        level="error",
        parse_status=OPERATIONAL_FAILURE_STATUS,
        failure_stage=failure_stage,
        detail=detail,
    )


def _format_operational_failure_detail(
    failure_stage: str,
    exc: BaseException,
) -> str:
    return (
        f"Operational failure during {failure_stage}: "
        f"{type(exc).__name__}: {exc}"
    )
