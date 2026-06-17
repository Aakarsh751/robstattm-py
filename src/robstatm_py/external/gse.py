"""Generalized S-Estimators for missing / cell-wise contaminated data.

Wraps the external ``GSE`` CRAN package (Maronna et al. 2019 §6.12.2, §6.13):

* :func:`gse`  → ``GSE::GSE``  — robust location/scatter with missing data
* :func:`tsgs` → ``GSE::TSGS`` — two-step GSE for cell-wise outliers

Both R functions return S4 objects; we read their slots directly via rpy2's
``.slots[...]`` (the public accessors ``getLocation`` / ``getScatter`` /
``getDist`` return the same slot values — verified in
``tests/external/test_gse.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from robstatm_py._r import r, r_pkg, rcall
from robstatm_py.covariance._common import validate_2d_numeric


def _slot_array(robj: Any, name: str) -> np.ndarray:
    """Read an S4 slot as a float numpy array."""
    return np.asarray(robj.slots[name], dtype=float)


def _slot_float(robj: Any, name: str) -> float:
    return float(np.asarray(robj.slots[name], dtype=float).ravel()[0])


def _slot_int(robj: Any, name: str) -> int:
    return int(np.asarray(robj.slots[name]).ravel()[0])


@dataclass(frozen=True, slots=True)
class GSEResult:
    """Generalized S-Estimator result (``GSE::GSE``).

    Attributes
    ----------
    mu : ndarray, shape (p,)
        Robust location (slot ``mu``; equals ``getLocation``).
    cov : ndarray, shape (p, p)
        Robust scatter (slot ``S``; equals ``getScatter``).
    pmd : ndarray, shape (n,)
        Partial squared Mahalanobis distances (slot ``pmd``; ``getDist``).
    pmd_adj : ndarray, shape (n,)
        Adjusted partial Mahalanobis distances (slot ``pmd.adj``).
    weights : ndarray, shape (n,)
        Case weights from the final iteration.
    ximp : ndarray, shape (n, p)
        Data matrix with missing entries imputed.
    sc : float
        Final generalized S-scale.
    iter : int
        Iterations to convergence.
    eps : float
        Final convergence criterion value.
    column_names : tuple[str, ...] | None
    """

    mu: np.ndarray
    cov: np.ndarray
    pmd: np.ndarray
    pmd_adj: np.ndarray
    weights: np.ndarray
    ximp: np.ndarray
    sc: float
    iter: int
    eps: float
    column_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<GSEResult: n={self.pmd.shape[0]} p={self.cov.shape[0]} "
            f"sc={self.sc:.4g} iter={self.iter}>"
        )


@dataclass(frozen=True, slots=True)
class TSGSResult:
    """Two-Step GSE result for cell-wise outliers (``GSE::TSGS``).

    Same shape as :class:`GSEResult` plus the filtered data matrix ``xf``.

    Attributes
    ----------
    mu : ndarray, shape (p,)
    cov : ndarray, shape (p, p)
    pmd : ndarray, shape (n,)
    pmd_adj : ndarray, shape (n,)
    weights : ndarray, shape (n,)
    ximp : ndarray, shape (n, p)
        Imputed data.
    xf : ndarray, shape (n, p)
        Filtered data (flagged cells set to NaN by the first step).
    sc : float
    iter : int
    eps : float
    column_names : tuple[str, ...] | None
    """

    mu: np.ndarray
    cov: np.ndarray
    pmd: np.ndarray
    pmd_adj: np.ndarray
    weights: np.ndarray
    ximp: np.ndarray
    xf: np.ndarray
    sc: float
    iter: int
    eps: float
    column_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<TSGSResult: n={self.pmd.shape[0]} p={self.cov.shape[0]} "
            f"sc={self.sc:.4g} iter={self.iter}>"
        )


def gse(
    X,
    *,
    tol: float = 1e-4,
    maxiter: int = 150,
    method: Literal["bisquare", "rocke"] = "bisquare",
) -> GSEResult:
    """Generalized S-Estimator of location and scatter with missing data.

    Wraps ``GSE::GSE``. Missing entries in ``X`` (NaN) are handled natively.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
        May contain NaN (missing) entries — that is the point of GSE.
    tol : float, default 1e-4
    maxiter : int, default 150
    method : {"bisquare", "rocke"}, default "bisquare"
        Loss family for the generalized S-scale.

    Returns
    -------
    GSEResult

    Raises
    ------
    robstatm_py.RobStatTMSetupError
        If the ``GSE`` R package is not installed.

    Notes
    -----
    Uses a stochastic EMVE initial estimate — call
    :func:`robstatm_py.set_seed` before for reproducibility.
    """
    arr, col_names = validate_2d_numeric(X, name="X", allow_nan=True)
    pkg = r_pkg("GSE")
    rfit = rcall(
        pkg.GSE,
        arr,
        tol=float(tol),
        maxiter=int(maxiter),
        method=method,
        _hint="GSE fit failed; check X shape and method in {bisquare, rocke}",
    )
    return GSEResult(
        mu=_slot_array(rfit, "mu").ravel(),
        cov=_slot_array(rfit, "S"),
        pmd=_slot_array(rfit, "pmd").ravel(),
        pmd_adj=_slot_array(rfit, "pmd.adj").ravel(),
        weights=_slot_array(rfit, "weights").ravel(),
        ximp=_slot_array(rfit, "ximp"),
        sc=_slot_float(rfit, "sc"),
        iter=_slot_int(rfit, "iter"),
        eps=_slot_float(rfit, "eps"),
        column_names=col_names,
        _r_fit=rfit,
    )


def tsgs(
    X,
    *,
    filter: Literal["UBF-DDC", "UBF", "DDC", "UF"] = "UBF-DDC",
    partial_impute: bool = False,
    tol: float = 1e-4,
    maxiter: int = 150,
    method: Literal["bisquare", "rocke"] = "bisquare",
) -> TSGSResult:
    """Two-Step Generalized S-Estimator for cell-wise outliers.

    Wraps ``GSE::TSGS``. Maronna et al. (2019) §6.13.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    filter : {"UBF-DDC", "UBF", "DDC", "UF"}, default "UBF-DDC"
        Cell-flagging filter used in step 1.
    partial_impute : bool, default False
    tol : float, default 1e-4
    maxiter : int, default 150
    method : {"bisquare", "rocke"}, default "bisquare"

    Returns
    -------
    TSGSResult

    Notes
    -----
    Stochastic — use :func:`robstatm_py.set_seed` before for reproducibility.
    """
    arr, col_names = validate_2d_numeric(X, name="X", allow_nan=True)
    pkg = r_pkg("GSE")
    kwargs = {
        "filter": filter,
        "partial.impute": bool(partial_impute),
        "tol": float(tol),
        "maxiter": int(maxiter),
        "method": method,
    }
    rfit = rcall(pkg.TSGS, arr, _hint="TSGS fit failed; check X shape", **kwargs)
    return TSGSResult(
        mu=_slot_array(rfit, "mu").ravel(),
        cov=_slot_array(rfit, "S"),
        pmd=_slot_array(rfit, "pmd").ravel(),
        pmd_adj=_slot_array(rfit, "pmd.adj").ravel(),
        weights=_slot_array(rfit, "weights").ravel(),
        ximp=_slot_array(rfit, "ximp"),
        xf=_slot_array(rfit, "xf"),
        sc=_slot_float(rfit, "sc"),
        iter=_slot_int(rfit, "iter"),
        eps=_slot_float(rfit, "eps"),
        column_names=col_names,
        _r_fit=rfit,
    )
