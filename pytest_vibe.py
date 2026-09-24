from __future__ import annotations

import math
import os
import warnings

import pytest
from setproctitle import setproctitle

_WORKER_COUNT_ENV_VAR = "PYTEST_XDIST_AUTO_NUM_WORKERS"
_LOCAL_NICENESS = 10


def _available_cpu_count() -> int:
    sched_getaffinity = getattr(os, "sched_getaffinity", None)
    if sched_getaffinity is not None:
        try:
            return len(sched_getaffinity(0))
        except OSError:
            pass
    return os.cpu_count() or 1


# Runner-specific signals, not the generic ``CI`` variable. ``CI`` is routinely
# exported in developer shells (and inherited by every child process), so keying
# off it would unthrottle local runs and saturate the machine. Dedicated CI
# runners set one of these instead.
_CI_RUNNER_ENV_VARS = ("BUILDKITE", "GITHUB_ACTIONS")


def _is_ci() -> bool:
    return any(
        os.environ.get(var, "").lower() in {"1", "true", "yes"}
        for var in _CI_RUNNER_ENV_VARS
    )


_IS_XDIST_WORKER = False


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    global _IS_XDIST_WORKER
    _IS_XDIST_WORKER = hasattr(config, "workerinput")
    if _IS_XDIST_WORKER or _is_ci():
        return
    if nice := getattr(os, "nice", None):
        nice(_LOCAL_NICENESS)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logstart(nodeid: str, location: tuple[str, int | None, str]) -> None:
    if _IS_XDIST_WORKER:
        setproctitle("pytest-xdist worker")


def _default_worker_count(cpu_count: int) -> int:
    return max(1, math.ceil(cpu_count / 2) - 1)


@pytest.hookimpl(tryfirst=True)
def pytest_xdist_auto_num_workers() -> int:
    configured_worker_count = os.environ.get(_WORKER_COUNT_ENV_VAR)
    if configured_worker_count is not None:
        try:
            worker_count = int(configured_worker_count)
        except ValueError:
            worker_count = 0

        if worker_count > 0:
            return worker_count

        warnings.warn(
            f"{_WORKER_COUNT_ENV_VAR} must be a positive integer; using the default",
            stacklevel=2,
        )

    cpu_count = _available_cpu_count()
    # Only throttle interactive/local runs to keep developer machines usable.
    # CI runs the full suite and needs every available core for parallelism.
    if _is_ci():
        return cpu_count
    return _default_worker_count(cpu_count)
