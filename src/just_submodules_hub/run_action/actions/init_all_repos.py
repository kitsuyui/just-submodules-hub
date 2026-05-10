"""Action handler: initialize all submodule repositories."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from just_submodules_hub.run_action.actions._helpers import (
    resolve_submodule_jobs,
    run_submodule_update,
    set_submodule_ignore_all,
    validate_positive_integer,
)
from just_submodules_hub.run_action.registry import action


@dataclass
class _InitAllReposArgs:
    """Parsed arguments for init-all-repos."""

    requested_jobs: str
    no_fetch: bool
    fetch_fallback: bool
    force: bool


def _build_init_all_repos_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the init-all-repos action."""
    parser = argparse.ArgumentParser(
        prog="init-all-repos",
        add_help=False,
        exit_on_error=False,
    )
    parser.add_argument("jobs_positional", nargs="?", default="", metavar="JOBS")
    parser.add_argument("--no-fetch", dest="no_fetch", action="store_true")
    parser.add_argument("--fetch-fallback", dest="fetch_fallback", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--jobs", default="", metavar="JOBS")
    return parser


def _parse_init_all_repos_args(args: list[str]) -> _InitAllReposArgs | int:
    """Parse args for init-all-repos.

    Returns an _InitAllReposArgs on success or an integer exit code on error.
    """
    parser = _build_init_all_repos_parser()
    try:
        ns, unknown = parser.parse_known_args(args)
    except argparse.ArgumentError as exc:
        msg = str(exc)
        # Normalize argparse message to "--FLAG requires a value" format
        if ": expected one argument" in msg:
            flag = msg.split(": expected one argument")[0].replace("argument ", "")
            print(f"{flag} requires a value", file=sys.stderr)
        else:
            print(f"unknown init-all option: {msg}", file=sys.stderr)
        return 2
    except SystemExit:
        print("unknown init-all option", file=sys.stderr)
        return 2
    if unknown:
        print(f"unknown init-all option: {unknown[0]}", file=sys.stderr)
        return 2
    # --jobs flag takes precedence over positional JOBS argument
    requested_jobs = ns.jobs or ns.jobs_positional
    # --fetch-fallback implies --no-fetch for the initial attempt
    no_fetch = ns.no_fetch or ns.fetch_fallback
    return _InitAllReposArgs(
        requested_jobs=requested_jobs,
        no_fetch=no_fetch,
        fetch_fallback=ns.fetch_fallback,
        force=ns.force,
    )


@action("init-all-repos")
def init_all_repos(args: list[str]) -> int:
    """Initialize all submodules and set ``ignore = all`` in the local git config."""
    parsed = _parse_init_all_repos_args(args)
    if isinstance(parsed, int):
        return parsed

    jobs = resolve_submodule_jobs(parsed.requested_jobs)
    if jobs:
        rc = validate_positive_integer(jobs, "JOBS")
        if rc != 0:
            return rc

    if parsed.no_fetch and parsed.fetch_fallback:
        rc = run_submodule_update(no_fetch=True, jobs=jobs, force=parsed.force)
        if rc != 0:
            print(
                "no-fetch submodule update failed; retrying with normal fetch",
                file=sys.stderr,
            )
            rc = run_submodule_update(no_fetch=False, jobs=jobs, force=parsed.force)
    else:
        rc = run_submodule_update(
            no_fetch=parsed.no_fetch, jobs=jobs, force=parsed.force
        )

    if rc != 0:
        return rc

    return set_submodule_ignore_all()
