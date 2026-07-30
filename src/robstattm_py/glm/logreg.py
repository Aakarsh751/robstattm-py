"""Robust logistic regression — Bianco–Yohai family.

Wraps ``RobStatTM::BYlogreg``, ``WBYlogreg``, ``WMLlogreg``. Maronna et al.
(2019) §7.2.

BY/WBY return list names:
  convergence, objective, coefficients, standard.deviation, fitted.values,
  residual.deviances.

WML return list names (different — no convergence/objective; has xweights/cov):
  xweights, coefficients, standard.deviation, fitted.values, cov,
  residual.deviances.

Python field map (R dotted -> Python snake_case):
  ``standard.deviation`` -> ``standard_deviation``
  ``fitted.values``      -> ``fitted_values``
  ``residual.deviances`` -> ``residual_deviances``

For BY/WBY, ``fitted.values`` and ``residual.deviances`` are returned as
``(1, n)`` row matrices in R; we ravel to ``(n,)`` per the Pythonic
docs/user_interface.md contract. Numerical values are bit-identical.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from robstattm_py._converters import (
    extract_array,
    extract_bool,
    extract_float,
    validate_1d_numeric,
)
from robstattm_py._errors import RobStatTMRError
from robstattm_py._r import r_pkg, rcall, rx2
from robstattm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class LogregResult:
    """Robust-logistic-regression result (shared across BY / WBY / WML).

    Attributes
    ----------
    coefficients : ndarray, shape (p+1,)
        Includes intercept first if ``intercept=True``.
    standard_deviation : ndarray, shape (p+1,)
    fitted_values : ndarray, shape (n,)
        Estimated success probabilities in [0, 1]. Raveled from R's
        ``(1, n)`` for BY/WBY.
    residual_deviances : ndarray, shape (n,)
    method : str
        Which estimator produced this (e.g. ``"BYlogreg"``).
    objective : float or None
        Objective at convergence. ``None`` for ``WMLlogreg`` (R does not
        return it).
    converged : bool or None
        Convergence flag. ``None`` for ``WMLlogreg``.
    xweights : ndarray or None, shape (n,)
        Subsample weights used by WML. ``None`` for BY/WBY.
    cov : ndarray or None, shape (p+1, p+1)
        Coefficient covariance matrix returned by WML. ``None`` for BY/WBY.
    """

    coefficients: np.ndarray
    standard_deviation: np.ndarray
    fitted_values: np.ndarray
    residual_deviances: np.ndarray
    method: str
    objective: Optional[float] = None
    converged: Optional[bool] = None
    xweights: Optional[np.ndarray] = None
    cov: Optional[np.ndarray] = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        bits = [f"p+1={self.coefficients.shape[0]}"]
        if self.objective is not None:
            bits.append(f"obj={self.objective:.4g}")
        if self.converged is not None:
            bits.append(f"converged={self.converged}")
        return f"<LogregResult[{self.method}]: {' '.join(bits)}>"


def _validate_logreg_inputs(X, y):
    arr, _ = validate_2d_numeric(X, name="X")
    y_arr = validate_1d_numeric(y, name="y")
    if y_arr.shape[0] != arr.shape[0]:
        raise ValueError(
            f"y length {y_arr.shape[0]} != X rows {arr.shape[0]}"
        )
    # logistic: y must be 0/1
    uniq = set(np.unique(y_arr).tolist())
    if not uniq.issubset({0.0, 1.0}):
        raise ValueError(f"y must be binary 0/1; got values {sorted(uniq)}")
    return arr, y_arr


def _call_logreg(
    rfun_name: str,
    X,
    y,
    *,
    intercept: bool,
    extra_kwargs: dict,
) -> LogregResult:
    arr, y_arr = _validate_logreg_inputs(X, y)
    pkg = r_pkg("RobStatTM")
    rfun = getattr(pkg, rfun_name)

    # R expects y as a (n, 1) column matrix (checks ncol(y) internally).
    y_col = y_arr.reshape(-1, 1)
    # R has `intercept=1` (numeric) not TRUE in formals
    kwargs = {"intercept": 1 if intercept else 0}
    kwargs.update(extra_kwargs)
    rfit = rcall(rfun, arr, y_col, **kwargs)

    # Field set differs between BY/WBY and WML; probe optionals via try/except.
    def _opt(name: str):
        try:
            return rx2(rfit, name)
        except (KeyError, ValueError):
            return None

    # On (quasi-)separable or otherwise degenerate data, RobStatTM's logistic
    # routines can return a truncated, non-converged object whose names are only
    # ``convergence``/``objective``/``coef`` — with no ``coefficients`` field.
    # Detect that here and raise a clear error, instead of letting the mandatory
    # extraction below fail with an opaque rpy2 ``ValueError: x not in list``
    # (see project_memory/blockers.md B-009).
    if _opt("coefficients") is None:
        conv = _opt("convergence")
        converged = extract_bool(conv) if conv is not None else False
        raise RobStatTMRError(
            f"{rfun_name} did not produce a usable fit (converged={converged}). "
            "R returned an incomplete result with no 'coefficients' — the response "
            "is likely (quasi-)separable or the design is degenerate for robust "
            "logistic regression. Condition the data, drop collinear/over-powerful "
            "predictors, or try a different estimator.",
            hint="perfectly separable binary data is the most common cause",
        )

    kw: dict[str, Any] = dict(
        coefficients=extract_array(rx2(rfit, "coefficients")).astype(float).ravel(),
        standard_deviation=extract_array(rx2(rfit, "standard.deviation")).astype(float).ravel(),
        fitted_values=extract_array(rx2(rfit, "fitted.values")).astype(float).ravel(),
        residual_deviances=extract_array(rx2(rfit, "residual.deviances")).astype(float).ravel(),
        method=rfun_name,
        _r_fit=rfit,
    )
    obj_r = _opt("objective")
    if obj_r is not None:
        kw["objective"] = extract_float(obj_r)
    conv_r = _opt("convergence")
    if conv_r is not None:
        kw["converged"] = extract_bool(conv_r)
    xw_r = _opt("xweights")
    if xw_r is not None:
        kw["xweights"] = extract_array(xw_r).astype(bool).ravel()
    cov_r = _opt("cov")
    if cov_r is not None:
        kw["cov"] = extract_array(cov_r).astype(float)
    return LogregResult(**kw)


def by_logreg(
    X,
    y,
    *,
    intercept: bool = True,
    const: float = 0.5,
    kmax: int = 1000,
    maxhalf: int = 10,
) -> LogregResult:
    """Bianco–Yohai M-estimator for logistic regression.

    Wraps ``RobStatTM::BYlogreg`` (alias ``logregBY``). Maronna et al.
    (2019) §7.2. Depends on ``robustbase`` (uses ``covMcd`` internally).

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    y : array_like, shape (n,)
        Binary 0/1 vector.
    intercept : bool, default True
    const : float, default 0.5
    kmax : int, default 1000
    maxhalf : int, default 10

    Returns
    -------
    LogregResult
    """
    return _call_logreg(
        "BYlogreg", X, y, intercept=intercept,
        extra_kwargs={"const": float(const), "kmax": int(kmax), "maxhalf": int(maxhalf)},
    )


def wby_logreg(
    X,
    y,
    *,
    intercept: bool = True,
    const: float = 0.5,
    kmax: int = 1000,
    maxhalf: int = 10,
) -> LogregResult:
    """Weighted Bianco–Yohai redescending M-estimator for logistic regression.

    Wraps ``RobStatTM::WBYlogreg`` (alias ``logregWBY``). Primary GLM
    recommendation in Maronna et al. (2019) §7.2.
    """
    return _call_logreg(
        "WBYlogreg", X, y, intercept=intercept,
        extra_kwargs={"const": float(const), "kmax": int(kmax), "maxhalf": int(maxhalf)},
    )


def wml_logreg(
    X,
    y,
    *,
    intercept: bool = True,
) -> LogregResult:
    """Weighted maximum-likelihood robust logistic regression.

    Wraps ``RobStatTM::WMLlogreg`` (alias ``logregWML``). Maronna et al.
    (2019) §7.2.
    """
    return _call_logreg(
        "WMLlogreg", X, y, intercept=intercept, extra_kwargs={},
    )
