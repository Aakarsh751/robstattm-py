"""Robust covariance dispatcher, ``RobStatTM::covRob`` / ``Multirobu``.

The two R names are aliases for the *same* function (verified via
``identical(covRob, Multirobu)``). The dispatcher selects between MM (for
small ``p``) and Rocke (for large ``p``) automatically when
``type="auto"`` (default). Users who want to force a specific estimator
can pass ``type="MM"`` or ``type="Rocke"``.

Maronna et al. (2019) §6.5–6.6.

R return list (RobStatTM 1.0.11):
  center, cov, cor, dist, wts, call, mu, V

This is the same shape as :class:`robstattm_py.CovRobMMResult` and
:class:`robstattm_py.CovRobRockeResult`. We expose a separate
:class:`CovRobResult` so callers can introspect ``estimator_type`` to know
which path was taken.

**Determinism:** ``covRob`` calls into ``KurtSDNew`` (random projections).
Use :func:`robstattm_py.set_seed` immediately before the call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from robstattm_py._converters import extract_array
from robstattm_py._r import r_pkg, rcall, rx2
from robstattm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class CovRobResult:
    """Result of :func:`cov_rob`.

    Attributes
    ----------
    center : ndarray, shape (p,)
        Final robust location estimate.
    cov : ndarray, shape (p, p)
        Final robust covariance / shape matrix.
    cor : ndarray or None
        Robust correlation matrix when ``corr=True`` was passed; otherwise
        ``None``.
    dist : ndarray, shape (n,)
        Robust (squared) Mahalanobis distances.
    wts : ndarray, shape (n,)
        Case weights at convergence.
    mu : ndarray, shape (p,)
        Initial location (Kurtosis-SD when the underlying path is MM, Rocke
        otherwise).
    v : ndarray, shape (p, p)
        Initial covariance / shape matrix.
    estimator_type : str
        ``"MM"`` or ``"Rocke"``, which sub-estimator R chose / was forced.
    column_names : tuple[str, ...] or None
    """

    center: np.ndarray
    cov: np.ndarray
    cor: np.ndarray | None
    dist: np.ndarray
    wts: np.ndarray
    mu: np.ndarray
    v: np.ndarray
    estimator_type: str
    column_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        p = self.center.shape[0]
        n = self.dist.shape[0]
        return (
            f"<CovRobResult[{self.estimator_type}]: n={n} p={p} "
            f"center=({self.center[0]:.4g}, ...)>"
        )

    def summary(self):
        """Port of R's ``summary.covRob``.

        Returns
        -------
        :class:`robstattm_py.covariance._summary.CovSummary`
            ``(cov, center, evals, eval_names, dist, cor, classical=False)``.
            Strict-tier identical to R's
            ``summary(covRob(X, ...))``.
        """
        from robstattm_py.covariance._summary import summary_of_cov
        return summary_of_cov(
            self.cov, self.center, self.dist, self.cor, classical=False,
        )


def _infer_type(p: int) -> str:
    """Mirror R's auto-selection rule: MM for p<10, Rocke for p>=10.

    Used purely for the returned ``estimator_type`` label when R does the
    selection internally. This reproduces ``covRob``'s own branch
    (``if (p >= 10) RockeMulti(...) else MMultiSHR(...)``, R/Multirobu.R:56);
    keep it in sync if RobStatTM ever changes that threshold.
    """
    return "MM" if p < 10 else "Rocke"


def cov_rob(
    X,
    *,
    type: Literal["auto", "MM", "Rocke"] = "auto",
    maxit: int = 50,
    tol: float = 1e-4,
    corr: bool = False,
) -> CovRobResult:
    """Robust covariance dispatcher, port of ``RobStatTM::covRob`` / ``Multirobu``.

    Auto-selects between MM (``p < 10``) and Rocke (``p >= 10``) when
    ``type="auto"``.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    type : {"auto", "MM", "Rocke"}, default "auto"
    maxit : int, default 50
    tol : float, default 1e-4
    corr : bool, default False
        If ``True``, populate ``cor`` with the robust correlation matrix.

    Returns
    -------
    CovRobResult

    Notes
    -----
    The R function ``covRob`` and ``Multirobu`` are aliases (verified
    ``identical()``). Both ship in RobStatTM's NAMESPACE.

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> df = rpm.datasets.wine()
    >>> rpm.set_seed(42)
    >>> fit = rpm.cov_rob(df, type="auto")
    >>> fit.estimator_type
    'Rocke'
    """
    if type not in {"auto", "MM", "Rocke"}:
        raise ValueError(
            f"type must be one of 'auto', 'MM', 'Rocke'; got {type!r}"
        )

    arr, col_names = validate_2d_numeric(X, name="X")
    pkg = r_pkg("RobStatTM")
    rfit = rcall(
        pkg.covRob,
        arr,
        type=type,
        maxit=int(maxit),
        tol=float(tol),
        corr=bool(corr),
    )

    center = extract_array(rx2(rfit, "center")).astype(float).ravel()
    cov = np.asarray(rx2(rfit, "cov"), dtype=float)
    dist = extract_array(rx2(rfit, "dist")).astype(float).ravel()
    wts = extract_array(rx2(rfit, "wts")).astype(float).ravel()
    mu = extract_array(rx2(rfit, "mu")).astype(float).ravel()
    v = np.asarray(rx2(rfit, "V"), dtype=float)

    cor_obj = rx2(rfit, "cor")
    if cor_obj is None or (hasattr(cor_obj, "__len__") and len(cor_obj) == 0):
        cor: np.ndarray | None = None
    else:
        try:
            cor = np.asarray(cor_obj, dtype=float)
            if cor.size == 0:
                cor = None
        except (TypeError, ValueError):
            cor = None

    resolved_type = type if type != "auto" else _infer_type(arr.shape[1])

    return CovRobResult(
        center=center,
        cov=cov,
        cor=cor,
        dist=dist,
        wts=wts,
        mu=mu,
        v=v,
        estimator_type=resolved_type,
        column_names=col_names,
        _r_fit=rfit,
    )
