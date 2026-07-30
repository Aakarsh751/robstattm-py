"""Robust generalized linear models — wraps ``robustbase::glmrob``.

Maronna et al. (2019) §7.x (epilepsy example). Robust GLM fitting for binomial
and Poisson responses. ``robustbase`` is already a RobStatTM dependency (CORE),
so this wrapper is normally available.

Single entry point:

* :func:`glmrob` → ``robustbase::glmrob``

Methods used by the epilepsy example: ``"Mqle"`` (robust quasi-likelihood / RQL,
the default) and ``"MT"``. Both are *deterministic* — no ``set_seed`` needed.
We fit *inside* R-space (push the data frame, build the formula + family) so the
result equals R exactly, then read the fields with ``rx2`` and ``residuals()``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import extract_array
from robstattm_py._r import r, require_r_pkg

_FAMILIES = {"poisson", "binomial"}


def _opt_scalar(ro, expr: str) -> float:
    """Read a scalar that may be NULL (e.g. tcc/dispersion for method='MT')."""
    if bool(ro.r(f"is.null({expr})")[0]):
        return float("nan")
    val = ro.r(expr)
    return float(np.asarray(val, dtype=float).ravel()[0])


@dataclass(frozen=True, slots=True)
class GlmrobResult:
    """Robust GLM fit (``robustbase::glmrob``).

    Attributes
    ----------
    coefficients : ndarray, shape (p,)
        Robust coefficients.
    coef_names : tuple[str, ...]
    cov : ndarray, shape (p, p)
        Coefficient covariance.
    std_errors : ndarray, shape (p,)
        ``sqrt(diag(cov))`` — convenience.
    residuals : ndarray, shape (n,)
        Deviance residuals (``residuals(fit)``) for ``method="Mqle"``; for
        ``method="MT"`` (where ``residuals()`` is undefined) the stored working
        residuals (``fit$residuals``).
    fitted_values : ndarray, shape (n,)
    linear_predictors : ndarray, shape (n,)
    weights_r : ndarray, shape (n,)
        Residual robustness weights (``w.r``).
    weights_x : ndarray, shape (n,)
        Design robustness weights (``w.x``).
    dispersion : float
    tcc : float
        Tuning constant c.
    iter : int
    converged : bool
    method : str
        ``"Mqle"`` / ``"MT"`` / ...
    family : str
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    cov: np.ndarray
    std_errors: np.ndarray
    residuals: np.ndarray
    fitted_values: np.ndarray
    linear_predictors: np.ndarray
    weights_r: np.ndarray
    weights_x: np.ndarray
    dispersion: float
    tcc: float
    iter: int
    converged: bool
    method: str
    family: str
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<GlmrobResult: family={self.family!r} method={self.method!r} "
            f"p={self.coefficients.shape[0]} converged={self.converged}>"
        )


def glmrob(
    formula: str,
    data: "pd.DataFrame",
    *,
    family: str = "poisson",
    method: str | None = None,
    weights_on_x: str = "none",
    **control_kwargs: Any,
) -> GlmrobResult:
    """Robust generalized linear model (``robustbase::glmrob``).

    Parameters
    ----------
    formula : str
        Model formula, e.g. ``"y ~ x1 + x2 + x3 + x4"``.
    data : pandas.DataFrame
        Model data.
    family : {"poisson", "binomial"}, default "poisson"
    method : {"Mqle", "MT", "BY", "WBY"}, optional
        Estimation method. ``None`` → R default ``"Mqle"`` (RQL).
    weights_on_x : {"none", "hat", "robCov", "covMcd"}, default "none"
        How to downweight leverage points.
    **control_kwargs
        Extra control arguments passed through as ``glmrob(..., name=value)``
        (e.g. ``tcc``, ``maxit``). Snake_case names are sent verbatim.

    Returns
    -------
    GlmrobResult

    Raises
    ------
    robstattm_py.RobStatTMSetupError
        If the ``robustbase`` R package is not installed.
    ValueError
        If ``family`` is unsupported.

    Notes
    -----
    Deterministic for ``method`` in {"Mqle", "MT"}. No seeding required.
    """
    if family not in _FAMILIES:
        raise ValueError(f"family must be one of {_FAMILIES}; got {family!r}")

    require_r_pkg("robustbase")  # ensure installed (namespace only; no attach -> avoid masking RobStatTM::BYlogreg etc.)
    ro = r()

    kw = [f"family={family}", f"weights.on.x={weights_on_x!r}".replace("'", '"')]
    if method is not None:
        kw.append(f"method={method!r}".replace("'", '"'))
    for k, v in control_kwargs.items():
        rk = k.replace("_", ".")
        if isinstance(v, bool):
            kw.append(f"{rk}={'TRUE' if v else 'FALSE'}")
        elif isinstance(v, str):
            kw.append(f"{rk}={v!r}".replace("'", '"'))
        else:
            kw.append(f"{rk}={float(v)}")
    kw_str = ", ".join(kw)

    pushed: list[str] = []
    try:
        ro.globalenv["rpm_glmrob_df"] = data
        pushed.append("rpm_glmrob_df")
        ro.r(
            f"rpm_glmrob_fit <- robustbase::glmrob({formula}, "
            f"data=rpm_glmrob_df, {kw_str})"
        )
        pushed.append("rpm_glmrob_fit")

        coef = extract_array(ro.r("rpm_glmrob_fit$coefficients")).astype(float).ravel()
        cov = np.asarray(ro.r("rpm_glmrob_fit$cov"), dtype=float)
        if cov.ndim == 1:
            cov = cov.reshape(coef.shape[0], coef.shape[0])

        # `residuals(fit)` (deviance residuals) works for Mqle but raises for MT
        # ("need non-robust working residuals"). Fall back to the stored
        # working-residuals field so the wrapper never errors on a valid fit.
        resid = extract_array(
            ro.r(
                "tryCatch(as.numeric(residuals(rpm_glmrob_fit)), "
                "error=function(e) as.numeric(rpm_glmrob_fit$residuals))"
            )
        ).astype(float).ravel()

        result = GlmrobResult(
            coefficients=coef,
            coef_names=tuple(str(n) for n in ro.r("names(rpm_glmrob_fit$coefficients)")),
            cov=cov,
            std_errors=np.sqrt(np.diag(cov)),
            residuals=resid,
            fitted_values=extract_array(ro.r("rpm_glmrob_fit$fitted.values")).astype(float).ravel(),
            linear_predictors=extract_array(
                ro.r("rpm_glmrob_fit$linear.predictors")
            ).astype(float).ravel(),
            weights_r=extract_array(ro.r("rpm_glmrob_fit$w.r")).astype(float).ravel(),
            weights_x=extract_array(ro.r("rpm_glmrob_fit$w.x")).astype(float).ravel(),
            # dispersion / tcc are NULL for method="MT"
            dispersion=_opt_scalar(ro, "rpm_glmrob_fit$dispersion"),
            tcc=_opt_scalar(ro, "rpm_glmrob_fit$tcc"),
            iter=int(np.asarray(ro.r("rpm_glmrob_fit$iter")).ravel()[0]),
            converged=bool(ro.r("rpm_glmrob_fit$converged")[0]),
            method=str(ro.r("rpm_glmrob_fit$method")[0]),
            family=family,
            _r_fit=_fetch_raw("rpm_glmrob_fit"),
        )
    finally:
        if pushed:
            names = ", ".join(f"'{n}'" for n in pushed)
            ro.r(f"for (v in c({names})) if (exists(v)) rm(list=v)")

    return result


def _fetch_raw(r_name: str):
    """Return a global R object WITHOUT numpy/pandas conversion (for ``.to_r()``)."""
    from rpy2.robjects import conversion, default_converter, r as _rr

    with conversion.localconverter(default_converter):
        return _rr(r_name)
