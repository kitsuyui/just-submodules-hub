from __future__ import annotations

import threading
from dataclasses import dataclass

import pytest

from just_submodules_hub.submodule_batch import (
    positive_int,
    print_records,
    run_parallel,
    run_parallel_with_progress,
)


@dataclass(frozen=True)
class Row:
    repo: str
    status: str


def test_run_parallel_collects_results_and_failures() -> None:
    seen: list[str] = []

    def worker(item: str) -> str:
        if item == "bad":
            raise RuntimeError("boom")
        return item.upper()

    results, failures = run_parallel(
        ["good", "bad"],
        worker,
        jobs=2,
        on_done=lambda: seen.append("done"),
    )

    assert results == ["GOOD"]
    assert [(failure.item, failure.message) for failure in failures] == [
        ("bad", "boom"),
    ]
    assert seen == ["done", "done"]


def test_run_parallel_returns_results_in_completion_order() -> None:
    both_started = threading.Barrier(2)
    fast_completed = threading.Event()

    def worker(item: str) -> str:
        both_started.wait(timeout=1)
        if item == "slow":
            fast_completed.wait(timeout=1)
            return "slow"
        fast_completed.set()
        return "fast"

    results, failures = run_parallel(["slow", "fast"], worker, jobs=2)

    assert results == ["fast", "slow"]
    assert failures == []


def test_run_parallel_with_progress_can_disable_progress() -> None:
    results, failures = run_parallel_with_progress(
        ["a", "b"],
        lambda item: item.upper(),
        jobs=2,
        desc="test",
        enabled=False,
    )
    assert sorted(results) == ["A", "B"]
    assert failures == []


def test_positive_int_rejects_invalid_values() -> None:
    assert positive_int("3") == 3
    for value in ("0", "-1", "abc"):
        try:
            positive_int(value)
        except Exception:
            pass
        else:
            raise AssertionError(f"positive_int should reject {value}")


def test_print_records_supports_tsv_jsonl_and_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [Row(repo="repo/github.com/example/a", status="noop")]

    print_records(rows, ("repo", "status"), "tsv")
    assert capsys.readouterr().out == "repo\tstatus\nrepo/github.com/example/a\tnoop\n"

    print_records(rows, ("repo", "status"), "jsonl")
    assert (
        capsys.readouterr().out
        == '{"repo": "repo/github.com/example/a", "status": "noop"}\n'
    )

    print_records(rows, ("repo", "status"), "table")
    out = capsys.readouterr().out
    assert "repo                       status" in out
    assert "repo/github.com/example/a  noop" in out
