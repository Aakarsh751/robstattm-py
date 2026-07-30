"""Synthetic-data + R-parity helpers for the exploration pipeline tests.

These are plain functions (not pytest fixtures), so they live here rather than
in ``conftest.py``. Each exploration test module imports them after putting the
exploration directory on ``sys.path``::

    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from _synth import make_regression_df, push_to_r, reval, rm_r

Design notes
------------
* Data synthesis uses ``numpy.random.default_rng(seed)`` — a stream that is
  **independent of R's Mersenne-Twister**. So the synthetic data is fully
  determined by ``seed`` regardless of any ``rpm.set_seed`` call. Estimator
  stochasticity (subsampling, random projections) lives in *R's* RNG, which the
  tests seed separately on both sides via ``rpm.set_seed`` / ``set.seed``.
* float64 numpy → R double and float64 pandas columns → R data.frame doubles are
  exact (IEEE-754), so pushing the *same* array to both sides gives bit-identical
  inputs — a precondition for the strict (``atol=0, rtol=0``) comparisons.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from robstattm_py._r import r


# ---------------------------------------------------------------------------
# R globalenv plumbing
# ---------------------------------------------------------------------------


def push_to_r(name: str, value) -> None:
    """Assign a numpy array / pandas DataFrame to R globalenv under ``name``."""
    r().globalenv[name] = value


def reval(expr: str):
    """Evaluate an R expression string; return the converted result."""
    return r().r(expr)


def rm_r(*names: str) -> None:
    """Remove the named R globalenv variables (if they exist)."""
    if not names:
        return
    vec = ",".join(f"'{n}'" for n in names)
    r().r(f"for (v in c({vec})) if (exists(v)) rm(list=v)")


# ---------------------------------------------------------------------------
# Synthetic data generators (deterministic in ``seed``)
# ---------------------------------------------------------------------------


def make_regression_df(
    *,
    n: int = 60,
    p: int = 3,
    seed: int = 0,
    outlier_frac: float = 0.0,
    outlier_mag: float = 12.0,
    leverage: bool = False,
    b0: float = 2.0,
) -> pd.DataFrame:
    """Gaussian linear-model frame with optional vertical / leverage outliers.

    Returns a DataFrame with columns ``y, x1, ..., xp`` (clean, dot-free names so
    the same R formula parses on both sides).
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    beta = rng.uniform(-2.0, 2.0, size=p)
    y = b0 + X @ beta + rng.normal(scale=0.5, size=n)
    k = int(round(outlier_frac * n))
    if k:
        idx = rng.choice(n, size=k, replace=False)
        y[idx] += outlier_mag * rng.choice([-1.0, 1.0], size=k)
        if leverage:
            X[idx, 0] += outlier_mag  # high-leverage bad points
    cols = [f"x{i + 1}" for i in range(p)]
    df = pd.DataFrame(X, columns=cols)
    df.insert(0, "y", y)
    return df


def make_cov_data(
    *,
    n: int = 80,
    p: int = 5,
    seed: int = 0,
    contam_frac: float = 0.0,
    contam_mag: float = 8.0,
) -> np.ndarray:
    """Correlated multivariate Gaussian with optional row contamination."""
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(p, p))
    cov = A @ A.T + p * np.eye(p)
    chol = np.linalg.cholesky(cov)
    X = rng.normal(size=(n, p)) @ chol.T + rng.uniform(-1.0, 1.0, size=p)
    k = int(round(contam_frac * n))
    if k:
        idx = rng.choice(n, size=k, replace=False)
        X[idx] += contam_mag
    return np.ascontiguousarray(X, dtype=np.float64)


def make_binary_xy(
    *,
    n: int = 120,
    p: int = 3,
    seed: int = 0,
    contam_frac: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Binary-response design for robust logistic regression.

    Returns ``(X, y)`` with ``y`` in ``{0, 1}`` and both classes guaranteed
    present. ``contam_frac`` flips a fraction of labels on shifted-``X`` rows
    (mislabelled outliers).
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    beta = rng.uniform(-1.5, 1.5, size=p)
    prob = 1.0 / (1.0 + np.exp(-(X @ beta)))
    y = (rng.random(n) < prob).astype(np.float64)
    if y.min() == y.max():  # guard against a degenerate single-class draw
        y[: n // 2] = 0.0
        y[n // 2:] = 1.0
    k = int(round(contam_frac * n))
    if k:
        idx = rng.choice(n, size=k, replace=False)
        X[idx] += 6.0
        y[idx] = 1.0 - y[idx]
    return np.ascontiguousarray(X, dtype=np.float64), y


def make_univariate(
    *,
    n: int = 40,
    seed: int = 0,
    outlier_frac: float = 0.1,
    outlier_mag: float = 10.0,
) -> np.ndarray:
    """1-D sample with a few gross outliers (for location/scale M-estimators)."""
    rng = np.random.default_rng(seed)
    u = rng.normal(loc=3.0, scale=2.0, size=n)
    k = int(round(outlier_frac * n))
    if k:
        idx = rng.choice(n, size=k, replace=False)
        u[idx] += outlier_mag * rng.choice([-1.0, 1.0], size=k)
    return np.ascontiguousarray(u, dtype=np.float64)
