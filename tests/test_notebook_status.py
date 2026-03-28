from __future__ import annotations

import pytest

from core.kaggle.notebook_status import NotebookStatus


def test_notebook_status_requires_positive_refresh_every():
    with pytest.raises(ValueError, match="positive integer"):
        NotebookStatus(refresh_every=0)


def test_notebook_status_renders_with_injected_notebook_backend():
    events: list[tuple[str, str]] = []

    def _display(value: str) -> None:
        events.append(("display", value))

    def _clear_output(*, wait: bool) -> None:
        events.append(("clear", str(wait)))

    status = NotebookStatus(
        refresh_every=5,
        display_fn=_display,
        clear_output_fn=_clear_output,
        markdown_factory=lambda text: text,
        monotonic_fn=lambda: 125.0,
    )

    status.start("Narrative", detail="running", processed=0, total=20)
    status.update(detail="halfway", processed=10, total=20)
    status.finish(detail="done", processed=20, total=20)

    assert events[0] == ("clear", "True")
    assert events[1][0] == "display"
    assert "Narrative." in events[1][1]
    assert "progress: 0/20 (0.0%)" in events[1][1]
    assert events[2] == ("clear", "True")
    assert "Narrative..." in events[3][1]
    assert "progress: 10/20 (50.0%)" in events[3][1]
    assert events[4] == ("clear", "True")
    assert "Narrative\n" in events[5][1]
    assert "progress: 20/20 (100.0%)" in events[5][1]


def test_notebook_status_skips_non_refresh_updates_by_default():
    outputs: list[str] = []
    status = NotebookStatus(
        refresh_every=5,
        print_fn=outputs.append,
        monotonic_fn=lambda: 10.0,
    )

    status.start("Narrative", detail="running", processed=0, total=20)
    status.update(detail="quiet", processed=3, total=20)
    status.update(detail="visible", processed=5, total=20)

    assert len(outputs) == 2
    assert "quiet" not in "\n".join(outputs)
    assert "visible" in outputs[-1]


def test_notebook_status_requires_start_before_update_or_finish():
    status = NotebookStatus(print_fn=lambda _: None)

    with pytest.raises(RuntimeError, match="before start"):
        status.update(detail="nope")

    with pytest.raises(RuntimeError, match="before start"):
        status.finish(detail="nope")
