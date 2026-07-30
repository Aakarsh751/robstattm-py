"""Rocke S-estimator robust covariance.

Wraps ``RobStatTM::covRobRocke`` (alias ``RockeMulti``). Maronna et al. (2019)
§6.4. Recommended for p ≥ 10 where the bisquare S-estimator degrades.

R return list: ``center``, ``cov``, ``cor``, ``dist``, ``wts``, ``call``,
``mu``, ``V``, ``sig``, ``gamma``.

Two extra scalar diagnostics compared with covRobMM:
- ``sig``: final M-scale value
- ``gamma``: Rocke ρ-function tuning constant chosen for this (n, p)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from robstattm_py._converters import extract_array, extract_float
from robstattm_py._r import r_pkg, rcall, rx2
from robstattm_py.covariance._common import validate_2d_numeric
from robstattm_py.covariance.cov_classic import _maybe_array


@dataclass(frozen=True, slots=True)
class CovRobRockeResult:
    """Rocke S-estimator covariance result.

    Same shape as :class:`CovRobMMResult` plus two scalars (``sig``, ``gamma``).

    Attributes
    ----------
    center : ndarray, shape (p,)
    cov : ndarray, shape (p, p)
    cor : ndarray, shape (p, p) or None
    dist : ndarray, shape (n,)
    wts : ndarray, shape (n,)
    mu : ndarray, shape (p,)
        Initial location (Kurtosis-SD).
    v : ndarray, shape (p, p)
        Initial shape (Kurtosis-SD).
    sig : float
        Final M-scale.
    gamma : float
        Rocke ρ tuning constant for this (n, p).
    column_names : tuple[str, ...] | None
    classical : bool
        Always False.
    """

    center: np.ndarray
    cov: np.ndarray
    cor: np.ndarray | None
    dist: np.ndarray
    wts: np.ndarray
    mu: np.ndarray
    v: np.ndarray
    sig: float
    gamma: float
    column_names: tuple[str, ...] | None = None
    classical: bool = False
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        n = self.dist.shape[0]
        p = self.cov.shape[0]
        return f"<CovRobRockeResult: n={n} p={p} sig={self.sig:.4g} gamma={self.gamma:.4g}>"

    def summary(self):
        """Port of R's ``summary.covRob`` (Rocke fit dispatches there).

        Returns
        -------
        :class:`robstattm_py.covariance._summary.CovSummary`
        """
        from robstattm_py.covariance._summary import summary_of_cov
        return summary_of_cov(
            self.cov, self.center, self.dist, self.cor, classical=False,
        )


def cov_rob_rocke(
    X,
    *,
    initial: Literal["K", "mve"] = "K",
    maxsteps: int = 5,
    propmin: float = 2,
    qs: float = 2,
    maxit: int = 50,
    tol: float = 1e-4,
    corr: bool = False,
) -> CovRobRockeResult:
    """Rocke translated-truncated S-estimator for covariance.

    Wraps ``RobStatTM::covRobRocke``. Maronna et al. (2019) §6.4.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    initial : {"K", "mve"}, default "K"
        Initial estimator. "K" = Kurtosis-SD (random; affected by seed);
        "mve" = Minimum Volume Ellipsoid (also stochastic).
    maxsteps : int, default 5
        Number of S-refinement steps after the initial estimate.
    propmin : float, default 2
        Lower bound on the proportion of observations used in the inner M-scale.
    qs : float, default 2
        Rocke ρ shape parameter.
    maxit : int, default 50
        Maximum outer iterations.
    tol : float, default 1e-4
        Convergence tolerance.
    corr : bool, default False
        Return correlation matrix.

    Returns
    -------
    CovRobRockeResult

    Notes
    -----
    Use :func:`robstattm_py.set_seed` before calling for reproducibility — the
    initial estimator samples random projection directions.
    """
    arr, col_names = validate_2d_numeric(X, name="X")

    pkg = r_pkg("RobStatTM")
    rfit = rcall(
        pkg.covRobRocke,
        arr,
        initial=initial,
        maxsteps=int(maxsteps),
        propmin=float(propmin),
        qs=float(qs),
        maxit=int(maxit),
        tol=float(tol),
        corr=bool(corr),
    )

    return CovRobRockeResult(
        center=extract_array(rx2(rfit, "center")).astype(float).ravel(),
        cov=np.asarray(rx2(rfit, "cov"), dtype=float),
        cor=_maybe_array(rx2(rfit, "cor")),
        dist=extract_array(rx2(rfit, "dist")).astype(float).ravel(),
        wts=extract_array(rx2(rfit, "wts")).astype(float).ravel(),
        mu=extract_array(rx2(rfit, "mu")).astype(float).ravel(),
        v=np.asarray(rx2(rfit, "V"), dtype=float),
        sig=extract_float(rx2(rfit, "sig")),
        gamma=extract_float(rx2(rfit, "gamma")),
        column_names=col_names,
        _r_fit=rfit,
    )
