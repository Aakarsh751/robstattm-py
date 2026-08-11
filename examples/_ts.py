"""Simulation helpers shared by the Chapter 8 time-series examples.

All five simulated Chapter-8 scripts draw their series from R's RNG under a
fixed seed and then contaminate them. Reproducing that here rather than using
``numpy.random`` is deliberate: the point of these examples is to be comparable
with the R scripts line by line, and an independently drawn sample from the same
distribution would support the same conclusions while printing different
numbers.

``arima.sim`` is called through R for the same reason — it is the exact
generator the scripts use, including its burn-in convention.
"""
from __future__ import annotations

import numpy as np

import robstattm_py as rpm


def arima_sim(
    *,
    seed: int,
    n: int,
    n_innov: int,
    ar: tuple[float, ...] = (),
    ma: tuple[float, ...] = (),
) -> np.ndarray:
    """Draw a series from R's ``arima.sim`` under ``set.seed(seed)``.

    Mirrors the Chapter-8 scripts' call shape: draw ``n_innov`` innovations
    first, then hand them to ``arima.sim`` with ``n.start = n_innov - n``. The
    order matters — the innovations are consumed from the same stream.
    """
    rpm.set_seed(seed)
    from robstattm_py._r import r

    ro = r()
    parts = []
    if ar:
        parts.append("ar = c(" + ", ".join(repr(float(a)) for a in ar) + ")")
    if ma:
        parts.append("ma = c(" + ", ".join(repr(float(m)) for m in ma) + ")")
    model = "list(" + ", ".join(parts) + ")"

    ro.r(f"rpm_ts_innov <- rnorm({n_innov})")
    try:
        series = np.asarray(
            ro.r(
                f"as.vector(arima.sim(model = {model}, n = {n}, "
                f"innov = rpm_ts_innov, n.start = {n_innov - n}))"
            ),
            dtype=float,
        )
    finally:
        ro.r("if (exists('rpm_ts_innov')) rm(rpm_ts_innov)")
    return series


def runif(n: int) -> np.ndarray:
    """Draw ``n`` uniforms from R's RNG, continuing the current stream."""
    from robstattm_py._r import r

    return np.asarray(r().r(f"runif({n})"), dtype=float)


def rnorm(n: int, mean: float = 0.0, sd: float = 1.0) -> np.ndarray:
    """Draw ``n`` normals from R's RNG, continuing the current stream."""
    from robstattm_py._r import r

    return np.asarray(r().r(f"rnorm({n}, {mean}, {sd})"), dtype=float)


def additive_outliers(series: np.ndarray, *, every: int, size: float) -> np.ndarray:
    """Add a spike of ``size`` at every ``every``-th observation (1-based).

    The equispaced contamination pattern ``ar1.R`` and ``ar3.R`` use.
    """
    out = series.copy()
    out[every - 1 :: every] += size
    return out


def acf(series: np.ndarray, lag_max: int) -> np.ndarray:
    """Sample autocorrelations at lags 1..``lag_max`` — R's ``acf``."""
    x = np.asarray(series, dtype=float)
    centred = x - x.mean()
    denominator = np.dot(centred, centred)
    return np.array(
        [np.dot(centred[k:], centred[:-k]) / denominator for k in range(1, lag_max + 1)]
    )
