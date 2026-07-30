"""Robust elastic-net S/MM estimator — wraps the external ``pense`` package.

Maronna et al. (2019) §5.1. Penalized S-estimator with an elastic-net penalty
(MM-lasso is the ``alpha=1`` special case). Requires the CRAN package
``pense`` (installed separately; see ``robstattm_py.check_setup()``).

Two entry points, mirroring the R API (pense ≥ 2.x):

* :func:`pense`     — fit the full regularization path (``pense::pense``)
* :func:`pense_cv`  — fit with k-fold cross-validation (``pense::pense_cv``)

Coefficients are extracted exactly as the R user would: via the package's
``coef()`` method at each lambda (path) or at ``lambda="min"`` (CV). This
guarantees bit-for-bit agreement with ``coef(fit, lambda=...)`` in R.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import extract_array, validate_1d_numeric
from robstattm_py._r import r, r_pkg, rcall
from robstattm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class PenseResult:
    """Full-path robust elastic-net fit (``pense::pense``).

    Attributes
    ----------
    coefficients : ndarray, shape (p+1, n_lambda)
        Coefficient matrix; row 0 is the intercept, rows 1..p the slopes.
        Column j is the fit at ``lambda_path[j]``. Extracted via R's
        ``coef(fit, lambda=...)`` so it matches R exactly.
    intercepts : ndarray, shape (n_lambda,)
        Convenience view of ``coefficients[0, :]``.
    slopes : ndarray, shape (p, n_lambda)
        Convenience view of ``coefficients[1:, :]``.
    coef_names : tuple[str, ...]
        Length p+1, ``("(Intercept)", "X1", ...)`` as R names them.
    lambda_path : ndarray, shape (n_lambda,)
        Penalty levels, descending.
    alpha : float
        Elastic-net mixing (1 = lasso, 0 = ridge).
    bdp : float
        Breakdown point used by the S-loss.
    """

    coefficients: np.ndarray
    intercepts: np.ndarray
    slopes: np.ndarray
    coef_names: tuple[str, ...]
    lambda_path: np.ndarray
    alpha: float
    bdp: float
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<PenseResult: p+1={self.coefficients.shape[0]} "
            f"n_lambda={self.coefficients.shape[1]} alpha={self.alpha:g} "
            f"bdp={self.bdp:g}>"
        )


@dataclass(frozen=True, slots=True)
class PenseCVResult:
    """Cross-validated robust elastic-net fit (``pense::pense_cv``).

    Attributes
    ----------
    coef_min : ndarray, shape (p+1,)
        Coefficients at the CV-optimal lambda (``coef(fit, lambda="min")``).
        Row 0 is the intercept.
    coef_names : tuple[str, ...]
    lambda_min : float
        The lambda minimising the CV curve.
    lambda_path : ndarray, shape (n_lambda,)
    cv_avg : ndarray, shape (n_lambda,)
        Mean CV metric per lambda.
    cv_se : ndarray, shape (n_lambda,)
        CV standard error per lambda.
    cvres : pandas.DataFrame
        The full R ``cvres`` table (lambda_index, solution_index, cvavg,
        cvse, alpha, lambda).
    alpha : float
    bdp : float
    """

    coef_min: np.ndarray
    coef_names: tuple[str, ...]
    lambda_min: float
    lambda_path: np.ndarray
    cv_avg: np.ndarray
    cv_se: np.ndarray
    cvres: pd.DataFrame
    alpha: float
    bdp: float
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<PenseCVResult: p+1={self.coef_min.shape[0]} "
            f"lambda_min={self.lambda_min:.4g} alpha={self.alpha:g}>"
        )


def _validate_xy(X, y):
    arr, _ = validate_2d_numeric(X, name="X")
    y_arr = validate_1d_numeric(y, name="y")
    if y_arr.shape[0] != arr.shape[0]:
        raise ValueError(f"y length {y_arr.shape[0]} != X rows {arr.shape[0]}")
    return arr, y_arr


def pense(
    X,
    y,
    *,
    alpha: float = 0.5,
    nlambda: int = 50,
    bdp: float = 0.25,
    intercept: bool = True,
    standardize: bool = True,
) -> PenseResult:
    """Fit the robust elastic-net path (``pense::pense``).

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    y : array_like, shape (n,)
    alpha : float, default 0.5
        Elastic-net mixing parameter (1 = lasso, 0 = ridge).
    nlambda : int, default 50
        Number of automatically chosen penalty levels.
    bdp : float, default 0.25
        Breakdown point of the S-loss.
    intercept : bool, default True
    standardize : bool, default True

    Returns
    -------
    PenseResult

    Raises
    ------
    robstattm_py.RobStatTMSetupError
        If the ``pense`` R package is not installed.

    Notes
    -----
    Stochastic (PY initial estimators). Call :func:`robstattm_py.set_seed`
    before for reproducibility. Coefficients are pulled via R's
    ``coef(fit, lambda=...)`` at every path point, so they equal R exactly.
    """
    arr, y_arr = _validate_xy(X, y)
    r_pkg("pense")  # ensure installed/attached
    ro = r()

    # Fit *inside* R so the S3 class survives for coef() dispatch — the
    # auto-conversion context strips class info when an R object is held in
    # Python and pushed back to globalenv (see discoveries.md).
    ro.globalenv["rpm_pense_x"] = arr
    ro.globalenv["rpm_pense_y"] = y_arr
    try:
        ro.r(
            f"rpm_pense_fit <- pense::pense(rpm_pense_x, drop(rpm_pense_y), "
            f"alpha={float(alpha)}, nlambda={int(nlambda)}, bdp={float(bdp)}, "
            f"intercept={'TRUE' if intercept else 'FALSE'}, "
            f"standardize={'TRUE' if standardize else 'FALSE'})"
        )
        lambda_path = extract_array(ro.r("rpm_pense_fit$lambda[[1]]")).astype(float).ravel()
        # Build the (p+1, n_lambda) coefficient matrix via R's coef() method,
        # matching exactly what a user would get with coef(fit, lambda=L).
        coefmat = np.asarray(
            ro.r(
                "sapply(rpm_pense_fit$lambda[[1]], "
                "function(L) as.numeric(coef(rpm_pense_fit, lambda=L)))"
            ),
            dtype=float,
        )
        if coefmat.ndim == 1:
            coefmat = coefmat.reshape(-1, 1)
        names = ro.r(
            "names(coef(rpm_pense_fit, lambda=rpm_pense_fit$lambda[[1]][1]))"
        )
        coef_names = tuple(str(n) for n in names)
        bdp_used = float(ro.r("rpm_pense_fit$bdp")[0])
        alpha_used = float(ro.r("rpm_pense_fit$alpha")[0])
        rfit = _fetch_raw("rpm_pense_fit")
    finally:
        ro.r("for (v in c('rpm_pense_x','rpm_pense_y','rpm_pense_fit')) "
             "if (exists(v)) rm(list=v)")

    return PenseResult(
        coefficients=coefmat,
        intercepts=coefmat[0, :].copy(),
        slopes=coefmat[1:, :].copy(),
        coef_names=coef_names,
        lambda_path=lambda_path,
        alpha=alpha_used,
        bdp=bdp_used,
        _r_fit=rfit,
    )


def pense_cv(
    X,
    y,
    *,
    alpha: float = 0.5,
    nlambda: int = 50,
    bdp: float = 0.25,
    cv_k: int = 5,
    cv_repl: int = 1,
    intercept: bool = True,
    standardize: bool = True,
) -> PenseCVResult:
    """Cross-validated robust elastic-net fit (``pense::pense_cv``).

    Parameters
    ----------
    X, y : data
    alpha : float, default 0.5
    nlambda : int, default 50
    bdp : float, default 0.25
    cv_k : int, default 5
        Number of CV folds.
    cv_repl : int, default 1
        Number of CV replications.
    intercept, standardize : bool

    Returns
    -------
    PenseCVResult

    Notes
    -----
    Stochastic (CV folds + PY initials). Use :func:`robstattm_py.set_seed`
    before for reproducibility. ``coef_min`` is ``coef(fit, lambda="min")``.
    """
    arr, y_arr = _validate_xy(X, y)
    r_pkg("pense")  # ensure installed/attached
    ro = r()

    # Fit inside R (preserves S3 class for coef() dispatch).
    ro.globalenv["rpm_pcv_x"] = arr
    ro.globalenv["rpm_pcv_y"] = y_arr
    try:
        # Trailing `; 0L` so ro.r() returns a trivial scalar rather than the
        # cvfit object (which holds data.frames the auto-converter chokes on).
        ro.r(
            f"rpm_pense_cv <- pense::pense_cv(rpm_pcv_x, drop(rpm_pcv_y), "
            f"alpha={float(alpha)}, nlambda={int(nlambda)}, bdp={float(bdp)}, "
            f"cv_k={int(cv_k)}, cv_repl={int(cv_repl)}, "
            f"intercept={'TRUE' if intercept else 'FALSE'}, "
            f"standardize={'TRUE' if standardize else 'FALSE'}); 0L"
        )
        coef_min = extract_array(
            ro.r("as.numeric(coef(rpm_pense_cv, lambda='min'))")
        ).astype(float).ravel()
        names = ro.r("names(coef(rpm_pense_cv, lambda='min'))")
        coef_names = tuple(str(n) for n in names)
        lambda_path = extract_array(ro.r("rpm_pense_cv$lambda[[1]]")).astype(float).ravel()
        cv_avg = extract_array(ro.r("rpm_pense_cv$cvres$cvavg")).astype(float).ravel()
        cv_se = extract_array(ro.r("rpm_pense_cv$cvres$cvse")).astype(float).ravel()
        lambda_min = float(
            ro.r("rpm_pense_cv$cvres$lambda[which.min(rpm_pense_cv$cvres$cvavg)]")[0]
        )
        # Build cvres column-by-column (whole-data.frame auto-conversion is
        # fragile when a column carries NULL names under the active converter).
        cvres_cols = list(ro.r("names(rpm_pense_cv$cvres)"))
        cvres_data = {
            str(c): extract_array(ro.r(f"rpm_pense_cv$cvres[['{c}']]")).astype(float).ravel()
            for c in cvres_cols
        }
        cvres_df = pd.DataFrame(cvres_data)
        bdp_used = float(ro.r("rpm_pense_cv$bdp")[0])
        alpha_used = float(ro.r("rpm_pense_cv$alpha")[0])
        # Fetch the raw cvfit under the plain default_converter so the active
        # numpy/pandas converter does not try (and fail) to convert its
        # embedded data.frames.
        rfit = _fetch_raw("rpm_pense_cv")
    finally:
        ro.r("for (v in c('rpm_pcv_x','rpm_pcv_y','rpm_pense_cv')) "
             "if (exists(v)) rm(list=v)")

    return PenseCVResult(
        coef_min=coef_min,
        coef_names=coef_names,
        lambda_min=lambda_min,
        lambda_path=lambda_path,
        cv_avg=cv_avg,
        cv_se=cv_se,
        cvres=cvres_df,
        alpha=alpha_used,
        bdp=bdp_used,
        _r_fit=rfit,
    )


def _fetch_raw(r_name: str):
    """Return a global R object WITHOUT numpy/pandas conversion.

    The active converter would try to convert embedded data.frames (e.g. in a
    pense_cvfit) and crash. Fetching under ``default_converter`` keeps the
    object as a raw rpy2 R object, suitable for ``.to_r()`` round-trips.
    """
    from rpy2.robjects import conversion, default_converter, r as _rr

    with conversion.localconverter(default_converter):
        return _rr(r_name)
