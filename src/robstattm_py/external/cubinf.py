"""Conditionally Unbiased Bounded-Influence GLM estimates — wraps ``robcbi``.

Maronna et al. (2019) §7.x (epilepsy example, CUBIF estimator). Künsch,
Stefanski & Carroll (1989). Bounded-influence estimates for Bernoulli, Binomial
and Poisson GLMs. Requires the CRAN-archived package ``robcbi`` (which imports
the Fortran package ``robeth`` — see ``docs/research/cubinf.md`` for install).

Single entry point:

* :func:`cubinf` → ``robcbi::cubinf``

``cubinf`` takes a *design matrix* ``X`` (variables in columns) and a response
``y``; with ``intercept=False`` (the default) the caller supplies the intercept
column — exactly as ``epilepsy.R`` does. We fit *inside* R-space (push ``X``/``y``,
build the family + control) so the result equals R exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstattm_py._converters import extract_array, validate_1d_numeric
from robstattm_py._r import r, require_r_pkg, rx2_opt
from robstattm_py.covariance._common import validate_2d_numeric

_FAMILIES = {"poisson", "binomial"}


@dataclass(frozen=True, slots=True)
class CubinfResult:
    """CUBIF GLM fit (``robcbi::cubinf``).

    Attributes
    ----------
    coefficients : ndarray, shape (p,)
        Coefficient estimates.
    coef_names : tuple[str, ...]
    cov : ndarray, shape (p, p)
        Estimated coefficient covariance.
    std_errors : ndarray, shape (p,)
        ``sqrt(diag(cov))`` — convenience.
    fitted_values : ndarray, shape (n,)
    residuals : ndarray, shape (n,)
        Working residuals.
    deviance_residuals : ndarray, shape (n,)
        ``rsdev`` — deviance residuals.
    linear_predictors : ndarray, shape (n,)
    rank : int
    df_residual : float
    converged : bool
    iter : int
    family : str
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    cov: np.ndarray
    std_errors: np.ndarray
    fitted_values: np.ndarray
    residuals: np.ndarray
    deviance_residuals: np.ndarray
    linear_predictors: np.ndarray
    rank: int
    df_residual: float
    converged: bool
    iter: int
    family: str
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<CubinfResult: family={self.family!r} "
            f"p={self.coefficients.shape[0]} converged={self.converged}>"
        )


def _opt_arr(ro, expr: str) -> np.ndarray:
    val = ro.r(expr)
    if val is None or len(val) == 0:
        return np.empty(0)
    return extract_array(val).astype(float).ravel()


def cubinf(
    X,
    y,
    *,
    family: str = "poisson",
    intercept: bool = False,
    null_dev: bool = True,
    ufact: float = 0.0,
    **control_kwargs: Any,
) -> CubinfResult:
    """CUBIF estimate for a discrete GLM (``robcbi::cubinf``).

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
        Design matrix (variables in columns). Supply your own intercept column
        when ``intercept=False`` (the default), as ``epilepsy.R`` does.
    y : array_like, shape (n,)
        Response (counts for Poisson; 0/1 or factor for Bernoulli).
    family : {"poisson", "binomial"}, default "poisson"
    intercept : bool, default False
        If True, ``cubinf`` prepends an intercept column.
    null_dev : bool, default True
        Whether to compute the null deviance (``null.dev`` control arg).
    ufact : float, default 0.0
        Bounded-influence tuning factor (``cubinf.control(ufact=...)``).
        ``epilepsy.R`` uses ``ufact=1.1``.
    **control_kwargs
        Other ``cubinf.control`` arguments by name (e.g. ``tlo``, ``mxt``).

    Returns
    -------
    CubinfResult

    Raises
    ------
    robstattm_py.RobStatTMSetupError
        If the ``robcbi`` R package (or its ``robeth`` dependency) is not installed.
    ValueError
        If ``family`` is unsupported.

    Notes
    -----
    Deterministic. ``X`` column names (if a DataFrame) are preserved as
    ``coef_names``.
    """
    if family not in _FAMILIES:
        raise ValueError(f"family must be one of {_FAMILIES}; got {family!r}")

    arr, col_names = validate_2d_numeric(X, name="X")
    y_arr = validate_1d_numeric(y, name="y")
    if y_arr.shape[0] != arr.shape[0]:
        raise ValueError(f"y length {y_arr.shape[0]} != X rows {arr.shape[0]}")

    require_r_pkg("robcbi")  # ensure installed (namespace only; imports robeth)
    ro = r()

    ctrl = [f"ufact={float(ufact)}", f"null.dev={'TRUE' if null_dev else 'FALSE'}"]
    for k, v in control_kwargs.items():
        rk = k.replace("_", ".")
        if isinstance(v, bool):
            ctrl.append(f"{rk}={'TRUE' if v else 'FALSE'}")
        else:
            ctrl.append(f"{rk}={float(v)}")
    ctrl_str = ", ".join(ctrl)

    pushed: list[str] = []
    try:
        ro.globalenv["rpm_cubinf_x"] = arr
        ro.globalenv["rpm_cubinf_y"] = y_arr
        pushed += ["rpm_cubinf_x", "rpm_cubinf_y"]
        if col_names is not None:
            cn = "c(" + ", ".join(f'"{c}"' for c in col_names) + ")"
            ro.r(f"colnames(rpm_cubinf_x) <- {cn}")

        ro.r(
            f"rpm_cubinf_fit <- robcbi::cubinf(rpm_cubinf_x, drop(rpm_cubinf_y), "
            f"family={family}(), intercept={'TRUE' if intercept else 'FALSE'}, "
            f"control=robcbi::cubinf.control({ctrl_str}))"
        )
        pushed.append("rpm_cubinf_fit")

        coef = extract_array(ro.r("rpm_cubinf_fit$coefficients")).astype(float).ravel()
        cov = np.asarray(ro.r("rpm_cubinf_fit$cov"), dtype=float)
        if cov.ndim == 1:
            cov = cov.reshape(coef.shape[0], coef.shape[0])
        # `names()` on an unnamed vector returns R NULL, which rpy2 hands back as
        # a NULLType — not Python None, and not sized. Testing `is not None`
        # alone let it reach len() and raise. A design matrix built from a plain
        # numpy array has no dimnames, so this is the common case, not the edge
        # case: it made cubinf unusable from the (X, y) form entirely.
        names = ro.r("names(rpm_cubinf_fit$coefficients)")
        try:
            named = tuple(str(n) for n in names)
        except TypeError:  # NULLType, or anything else not iterable
            named = ()
        coef_names = (
            named
            if len(named) == coef.shape[0]
            else (col_names or tuple(f"V{i + 1}" for i in range(coef.shape[0])))
        )

        df_resid = rx2_opt(ro.r("rpm_cubinf_fit"), "df.residual")
        rank = rx2_opt(ro.r("rpm_cubinf_fit"), "rank")
        conv = rx2_opt(ro.r("rpm_cubinf_fit"), "converged")
        it = rx2_opt(ro.r("rpm_cubinf_fit"), "iter")

        result = CubinfResult(
            coefficients=coef,
            coef_names=coef_names,
            cov=cov,
            std_errors=np.sqrt(np.diag(cov)),
            fitted_values=_opt_arr(ro, "rpm_cubinf_fit$fitted.values"),
            residuals=_opt_arr(ro, "rpm_cubinf_fit$residuals"),
            deviance_residuals=_opt_arr(ro, "rpm_cubinf_fit$rsdev"),
            linear_predictors=_opt_arr(ro, "rpm_cubinf_fit$linear.predictors"),
            rank=int(np.asarray(rank).ravel()[0]) if rank is not None else coef.shape[0],
            df_residual=float(np.asarray(df_resid).ravel()[0]) if df_resid is not None else float("nan"),
            converged=bool(np.asarray(conv).ravel()[0]) if conv is not None else True,
            iter=int(np.asarray(it).ravel()[0]) if it is not None else 0,
            family=family,
            _r_fit=_fetch_raw("rpm_cubinf_fit"),
        )
    finally:
        if pushed:
            names = ", ".join(f"'{n}'" for n in pushed)
            ro.r(f"for (v in c({names})) if (exists(v)) rm(list=v)")

    return result


def _fetch_raw(r_name: str):
    """Return a global R object WITHOUT numpy/pandas conversion (for ``.to_r()``)."""
    from rpy2.robjects import conversion, default_converter
    from rpy2.robjects import r as _rr

    with conversion.localconverter(default_converter):
        return _rr(r_name)
