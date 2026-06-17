"""Bench / performance helpers — UI doc §11.

Provides ``rpm.set_n_jobs(n)``, ``rpm.bench.timer(fit)``, and
``rpm.r_started()`` (re-exported from ``_r``).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class TimerResult:
    """Output of :func:`timer`.

    Attributes
    ----------
    total_seconds : float
        Wall-clock time of the call.
    r_seconds : float
        Approximate R-side time (Sys.time before/after the call), captured
        from R when possible. Falls back to ``total_seconds`` when not.
    py_overhead_seconds : float
        ``total_seconds - r_seconds`` — bridge / conversion overhead.
    """

    total_seconds: float
    r_seconds: float
    py_overhead_seconds: float

    def __repr__(self) -> str:
        return (
            f"<TimerResult: total={self.total_seconds*1000:.1f}ms, "
            f"R={self.r_seconds*1000:.1f}ms, "
            f"bridge={self.py_overhead_seconds*1000:.1f}ms>"
        )


def timer(callable_: Callable[[], object], *, repeat: int = 1) -> TimerResult:
    """Time a Python callable that ends in a single R call.

    Parameters
    ----------
    callable_ : callable
        Zero-arg callable; e.g. ``lambda: rpm.lmrobdet_mm(...)``.
    repeat : int, default 1
        Run ``repeat`` times and report the best wall time.

    Returns
    -------
    TimerResult

    Examples
    --------
    >>> import robstatm_py as rpm
    >>> df = rpm.datasets.mineral()
    >>> t = rpm.bench.timer(lambda: rpm.lmrobdet_mm("zinc ~ copper", data=df))
    >>> t.total_seconds > 0
    True
    """
    if repeat < 1:
        raise ValueError(f"repeat must be >= 1, got {repeat}")

    from robstatm_py._r import r as _rmod

    best_total = float("inf")
    best_r = float("inf")
    for _ in range(repeat):
        ro = _rmod()
        t_r0 = float(ro.r("as.numeric(Sys.time())")[0])
        t_py0 = time.perf_counter()
        callable_()
        t_py1 = time.perf_counter()
        t_r1 = float(ro.r("as.numeric(Sys.time())")[0])
        total = t_py1 - t_py0
        r_t = max(t_r1 - t_r0, 0.0)
        if total < best_total:
            best_total = total
            best_r = r_t
    return TimerResult(
        total_seconds=best_total,
        r_seconds=best_r,
        py_overhead_seconds=max(best_total - best_r, 0.0),
    )


def set_n_jobs(n: int) -> int:
    """Set the R-side ``options(mc.cores=n)`` for parallel wrappers.

    Affects estimators that fan out internally — currently only
    ``pyinit`` candidate evaluation. Returns the previous value (or 1).

    Parameters
    ----------
    n : int
        Number of cores; must be >= 1.

    Returns
    -------
    int
        The previous ``mc.cores`` value.
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"n must be a positive int, got {n!r}")
    from robstatm_py._r import r as _rmod
    ro = _rmod()
    prev = ro.r("getOption('mc.cores', 1L)")
    try:
        prev_int = int(prev[0])
    except Exception:
        prev_int = 1
    ro.r(f"options(mc.cores = {int(n)})")
    return prev_int
