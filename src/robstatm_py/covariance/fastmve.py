"""Fast Minimum Volume Ellipsoid initial covariance.

Wraps ``RobStatTM::fastmve``. C-backed; used as the ``initial="mve"`` option
of ``covRobRocke``.

R return list: ``center``, ``cov``, ``scale``, ``best``, ``nsamp``, ``nsing``.

``best`` is an integer index vector (R 1-based); Python returns it 0-based.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._converters import extract_array, extract_float, extract_int
from robstatm_py._r import r_pkg, rcall, rx2
from robstatm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class FastMVEResult:
    """Fast MVE result.

    Attributes
    ----------
    center : ndarray, shape (p,)
    cov : ndarray, shape (p, p)
    scale : float
    best : ndarray of int, shape (k,)
        Indices of the chosen "best" subset. **Zero-based** (R-side is 1-based;
        converted here so ``X[best]`` works directly in Python).
    nsamp : int
        Number of subsets sampled.
    nsing : int
        Number of singular subsets encountered.
    column_names : tuple[str, ...] | None
    """

    center: np.ndarray
    cov: np.ndarray
    scale: float
    best: np.ndarray
    nsamp: int
    nsing: int
    column_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return f"<FastMVEResult: p={self.center.shape[0]} scale={self.scale:.4g} nsamp={self.nsamp}>"


def fastmve(
    X,
    *,
    nsamp: int = 500,
) -> FastMVEResult:
    """Fast minimum volume ellipsoid robust covariance.

    Wraps ``RobStatTM::fastmve``. Random subsampling — use
    :func:`robstatm_py.set_seed` for reproducibility.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    nsamp : int, default 500
        Number of random subsets to try.

    Returns
    -------
    FastMVEResult
        ``best`` indices are 0-based for Python compatibility (R returns 1-based).
    """
    arr, col_names = validate_2d_numeric(X, name="X")
    pkg = r_pkg("RobStatTM")
    rfit = rcall(pkg.fastmve, arr, nsamp=int(nsamp))
    best_1based = extract_array(rx2(rfit, "best")).astype(int).ravel()
    best_0based = best_1based - 1
    return FastMVEResult(
        center=extract_array(rx2(rfit, "center")).astype(float).ravel(),
        cov=np.asarray(rx2(rfit, "cov"), dtype=float),
        scale=extract_float(rx2(rfit, "scale")),
        best=best_0based,
        nsamp=extract_int(rx2(rfit, "nsamp")),
        nsing=extract_int(rx2(rfit, "nsing")),
        column_names=col_names,
        _r_fit=rfit,
    )
