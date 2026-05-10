from __future__ import annotations

import sys

from just_submodules_hub.run_action.actions._helpers import (
    resolve_submodule_jobs,
    run_submodule_update,
    set_submodule_ignore_all,
    validate_positive_integer,
)
from just_submodules_hub.run_action.registry import action


@action("init-all-repos")
def init_all_repos(args: list[str]) -> int:
    requested_jobs = ""
    no_fetch = False
    fetch_fallback = False
    force = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--no-fetch":
            no_fetch = True
        elif arg == "--fetch-fallback":
            fetch_fallback = True
            no_fetch = True
        elif arg == "--force":
            force = True
        elif arg == "--jobs":
            i += 1
            if i >= len(args) or not args[i]:
                print("--jobs requires a value", file=sys.stderr)
                return 2
            requested_jobs = args[i]
        elif arg.startswith("--jobs="):
            requested_jobs = arg[len("--jobs=") :]
        elif arg.startswith("--"):
            print(f"unknown init-all option: {arg}", file=sys.stderr)
            return 2
        else:
            if requested_jobs:
                print(f"unexpected init-all argument: {arg}", file=sys.stderr)
                return 2
            requested_jobs = arg
        i += 1

    jobs = resolve_submodule_jobs(requested_jobs)
    if jobs:
        rc = validate_positive_integer(jobs, "JOBS")
        if rc != 0:
            return rc

    if no_fetch and fetch_fallback:
        rc = run_submodule_update(no_fetch=True, jobs=jobs, force=force)
        if rc != 0:
            print(
                "no-fetch submodule update failed; retrying with normal fetch",
                file=sys.stderr,
            )
            rc = run_submodule_update(no_fetch=False, jobs=jobs, force=force)
    else:
        rc = run_submodule_update(no_fetch=no_fetch, jobs=jobs, force=force)

    if rc != 0:
        return rc

    return set_submodule_ignore_all()
