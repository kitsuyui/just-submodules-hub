from __future__ import annotations

import csv
import json
import sys
from argparse import ArgumentTypeError
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from typing import Callable, Iterable, Iterator, Mapping, Sequence, TypeVar

from tqdm import tqdm


T = TypeVar("T")
R = TypeVar("R")

TQDM_BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"


@dataclass(frozen=True)
class BatchFailure:
    item: str
    message: str


def positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ArgumentTypeError("must be an integer") from exc
    if value < 1:
        raise ArgumentTypeError("must be >= 1")
    return value


@contextmanager
def progress_bar(
    *,
    total: int,
    desc: str,
    unit: str = "task",
    enabled: bool = True,
) -> Iterator[tqdm | None]:
    if not enabled:
        yield None
        return
    with tqdm(
        total=total,
        desc=desc,
        unit=unit,
        leave=False,
        dynamic_ncols=True,
        bar_format=TQDM_BAR_FORMAT,
        file=sys.stderr,
    ) as bar:
        yield bar


def tick(bar: tqdm | None, amount: int = 1) -> None:
    if bar is not None:
        bar.update(amount)


def run_parallel(
    items: Iterable[T],
    worker: Callable[[T], R],
    *,
    jobs: int,
    on_done: Callable[[], None] | None = None,
) -> tuple[list[R], list[BatchFailure]]:
    results: list[R] = []
    failures: list[BatchFailure] = []

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        future_map = {pool.submit(worker, item): item for item in items}
        for future in as_completed(future_map):
            item = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append(BatchFailure(str(item), str(exc)))
            finally:
                if on_done is not None:
                    on_done()

    return results, failures


def run_parallel_with_progress(
    items: Sequence[T],
    worker: Callable[[T], R],
    *,
    jobs: int,
    desc: str,
    unit: str = "task",
    enabled: bool = True,
) -> tuple[list[R], list[BatchFailure]]:
    with progress_bar(total=len(items), desc=desc, unit=unit, enabled=enabled) as bar:
        return run_parallel(items, worker, jobs=jobs, on_done=lambda: tick(bar))


def record_to_dict(record: object) -> dict[str, str]:
    if is_dataclass(record) and not isinstance(record, type):
        raw = asdict(record)
    elif isinstance(record, Mapping):
        raw = dict(record)
    else:
        raise TypeError(f"unsupported record type: {type(record).__name__}")
    return {str(key): "" if value is None else str(value) for key, value in raw.items()}


def print_tsv(records: Sequence[object], fields: Sequence[str]) -> None:
    writer = csv.DictWriter(sys.stdout, fieldnames=list(fields), dialect="excel-tab", lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(record_to_dict(record))


def print_jsonl(records: Sequence[object]) -> None:
    for record in records:
        print(json.dumps(record_to_dict(record), ensure_ascii=False, sort_keys=True))


def print_table(records: Sequence[object], fields: Sequence[str]) -> None:
    rows = [dict(zip(fields, fields, strict=True)), *(record_to_dict(record) for record in records)]
    widths = {field: max(len(row.get(field, "")) for row in rows) for field in fields}
    for index, row in enumerate(rows):
        print("  ".join(row.get(field, "").ljust(widths[field]) for field in fields))
        if index == 0:
            print("  ".join("-" * widths[field] for field in fields))


def print_records(records: Sequence[object], fields: Sequence[str], output_format: str) -> None:
    if output_format == "jsonl":
        print_jsonl(records)
    elif output_format == "tsv":
        print_tsv(records, fields)
    elif output_format == "table":
        print_table(records, fields)
    else:
        raise ValueError(f"unsupported output format: {output_format}")
