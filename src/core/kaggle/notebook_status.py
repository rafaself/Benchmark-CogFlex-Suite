from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

__all__ = ["NotebookStatus"]


class NotebookStatus:
    """Compact in-place status renderer for notebook execution phases."""

    def __init__(
        self,
        *,
        refresh_every: int = 10,
        display_fn: Callable[[Any], None] | None = None,
        clear_output_fn: Callable[..., None] | None = None,
        markdown_factory: Callable[[str], Any] | None = None,
        print_fn: Callable[[str], None] | None = None,
        monotonic_fn: Callable[[], float] | None = None,
    ) -> None:
        if refresh_every <= 0:
            raise ValueError("refresh_every must be a positive integer")

        self.refresh_every = refresh_every
        self._display_fn = display_fn
        self._clear_output_fn = clear_output_fn
        self._markdown_factory = markdown_factory
        self._print_fn = print if print_fn is None else print_fn
        self._prefer_text_output = print_fn is not None
        self._monotonic_fn = time.monotonic if monotonic_fn is None else monotonic_fn
        self._phase: str | None = None
        self._started_at: float | None = None
        self._display_backend_ready = all(
            value is not None
            for value in (self._display_fn, self._clear_output_fn, self._markdown_factory)
        )

        if not self._display_backend_ready and not self._prefer_text_output:
            self._load_notebook_backend()

    def start(
        self,
        phase: str,
        *,
        detail: str,
        processed: int | None = None,
        total: int | None = None,
        warnings: int = 0,
        errors: int = 0,
    ) -> None:
        self._phase = phase
        self._started_at = self._monotonic_fn()
        self._render(
            detail=detail,
            processed=processed,
            total=total,
            warnings=warnings,
            errors=errors,
            final=False,
        )

    def update(
        self,
        *,
        detail: str,
        processed: int | None = None,
        total: int | None = None,
        warnings: int = 0,
        errors: int = 0,
        force: bool = False,
    ) -> None:
        if self._phase is None:
            raise RuntimeError("NotebookStatus.update() called before start()")

        if not force and not self._should_refresh(processed=processed, total=total):
            return

        self._render(
            detail=detail,
            processed=processed,
            total=total,
            warnings=warnings,
            errors=errors,
            final=False,
        )

    def finish(
        self,
        *,
        detail: str,
        processed: int | None = None,
        total: int | None = None,
        warnings: int = 0,
        errors: int = 0,
    ) -> None:
        if self._phase is None:
            raise RuntimeError("NotebookStatus.finish() called before start()")

        self._render(
            detail=detail,
            processed=processed,
            total=total,
            warnings=warnings,
            errors=errors,
            final=True,
        )

    def _should_refresh(self, *, processed: int | None, total: int | None) -> bool:
        if processed is None or total in (None, 0):
            return True
        return processed >= total or processed % self.refresh_every == 0

    def _render(
        self,
        *,
        detail: str,
        processed: int | None,
        total: int | None,
        warnings: int,
        errors: int,
        final: bool,
    ) -> None:
        if self._phase is None:
            raise RuntimeError("NotebookStatus._render() called before start()")

        lines = [f"{self._phase}{self._status_suffix(processed=processed, final=final)}", detail]
        progress = self._progress_text(processed=processed, total=total)
        if progress is not None:
            lines.append(f"progress: {progress}")
        lines.append(
            f"warnings: {warnings} | errors: {errors} | elapsed: {self._format_elapsed()}"
        )
        text = "\n".join(lines)

        if self._display_backend_ready:
            assert self._clear_output_fn is not None
            assert self._display_fn is not None
            assert self._markdown_factory is not None
            self._clear_output_fn(wait=True)
            self._display_fn(self._markdown_factory(f"```text\n{text}\n```"))
            return

        self._print_fn(text)

    def _load_notebook_backend(self) -> None:
        try:
            from IPython.display import Markdown, clear_output, display
        except Exception:
            return

        self._display_fn = display
        self._clear_output_fn = clear_output
        self._markdown_factory = Markdown
        self._display_backend_ready = True

    def _status_suffix(self, *, processed: int | None, final: bool) -> str:
        if final:
            return ""
        tick = 0 if processed is None else processed // self.refresh_every
        return (".", "..", "...")[tick % 3]

    def _progress_text(self, *, processed: int | None, total: int | None) -> str | None:
        if processed is None or total in (None, 0):
            return None
        return f"{processed}/{total} ({processed / total:.1%})"

    def _format_elapsed(self) -> str:
        if self._started_at is None:
            return "00:00"

        elapsed = max(0, int(self._monotonic_fn() - self._started_at))
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
