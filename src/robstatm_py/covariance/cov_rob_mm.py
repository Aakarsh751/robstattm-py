"""MM robust covariance via ``RobStatTM::covRobMM`` (alias ``MMultiSHR``).

Maronna et al. 2019 §6.5. Recommended for moderate p (p < 10). For p ≥ 10
use ``cov_rob_rocke``.

R return list (RobStatTM 1.0.11):
  center, cov, cor, dist, wts, call, mu, V

``mu`` and ``V`` are the initial (Kurtosis-SD) estimates; ``center`` and ``cov``
are the final MM-refined estimates.

**Determinism:** ``covRobMM`` internally calls ``KurtSDNew`` which samples
random projections. Call :func:`robstatm_py.set_seed` immediately before
calling this wrapper to make results reproducible across runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._converters import extract_array
from robstatm_py._r import r_pkg, rcall, rx2
from robstatm_py.covariance._common import validate_2d_numeric
from robstatm_py.covariance.cov_classic import _maybe_array


@dataclass(frozen=True, slots=True)
class CovRobMMResult:
    """MM robust covariance result.

    Attributes
    ----------
    center : ndarray, shape (p,)
        Final MM-refined location estimate.
    cov : ndarray, shape (p, p)
        Final MM-refined covariance.
    cor : ndarray, shape (p, p) or None
    dist : ndarray, shape (n,)
        Squared Mahalanobis distances under the robust covariance.
    wts : ndarray, shape (n,)
        Case weights from the final IRLS iteration.
    mu : ndarray, shape (p,)
        Initial (Kurtosis-SD) location estimate.
    v : ndarray, shape (p, p)
        Initial (Kurtosis-SD) shape estimate.
    column_names : tuple[str, ...] | None
    classical : bool
        Always False; helpers use this to distinguish from CovClassicResult.
    """

    center: np.ndarray
    cov: np.ndarray
    cor: np.ndarray | None
    dist: np.ndarray
    wts: np.ndarray
    mu: np.ndarray
    v: np.ndarray
    column_names: tuple[str, ...] | None = None
    classical: bool = False
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        n = self.dist.shape[0]
        p = self.cov.shape[0]
        wmean = float(self.wts.mean())
        return f"<CovRobMMResult: n={n} p={p} mean_weight={wmean:.3f}>"

    def summary(self):
        """Port of R's ``summary.covRob`` (MM fit dispatches there).

        Returns
        -------
        :class:`robstatm_py.covariance._summary.CovSummary`
        """
        from robstatm_py.covariance._summary import summary_of_cov
        return summary_of_cov(
            self.cov, self.center, self.dist, self.cor, classical=False,
        )


def cov_rob_mm(
    X,
    *,
    maxit: int = 50,
    tolpar: float = 1e-4,
    corr: bool = False,
) -> CovRobMMResult:
    """MM-estimator for multivariate location and covariance.

    Wraps ``RobStatTM::covRobMM``. Maronna et al. (2019) §6.5.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
        Numeric data matrix.
    maxit : int, default 50
        Maximum MM-iterations.
    tolpar : float, default 1e-4
        Parameter-change convergence tolerance.
    corr : bool, default False
        Return correlation matrix in ``cor``.

    Returns
    -------
    CovRobMMResult

    Notes
    -----
    Internally uses ``KurtSDNew`` for initialization, which samples random
    projection directions. For reproducible output, call
    :func:`robstatm_py.set_seed` immediately before invoking this wrapper.

    Examples
    --------
    >>> import robstatm_py as rpm
    >>> rpm.set_seed(42)
    >>> result = rpm.cov_rob_mm(rpm.datasets.wine())
    >>> result.center.shape
    (13,)
    """
    arr, col_names = validate_2d_numeric(X, name="X")

    pkg = r_pkg("RobStatTM")
    rfit = rcall(
        pkg.covRobMM,
        arr,
        maxit=int(maxit),
        tolpar=float(tolpar),
        corr=bool(corr),
    )

    return CovRobMMResult(
        center=extract_array(rx2(rfit, "center")).astype(float).ravel(),
        cov=np.asarray(rx2(rfit, "cov"), dtype=float),
        cor=_maybe_array(rx2(rfit, "cor")),
        dist=extract_array(rx2(rfit, "dist")).astype(float).ravel(),
        wts=extract_array(rx2(rfit, "wts")).astype(float).ravel(),
        mu=extract_array(rx2(rfit, "mu")).astype(float).ravel(),
        v=np.asarray(rx2(rfit, "V"), dtype=float),
        column_names=col_names,
        _r_fit=rfit,
    )
