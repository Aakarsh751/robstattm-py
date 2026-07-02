"""Robust ARIMA estimation — wraps the external ``robustarima`` package.

Maronna et al. (2019) Chapter 8. The *filtered tau-estimate* fits a
regression-ARIMA model resistant to additive outliers and returns a robustly
"cleaned" series. Requires the CRAN package ``robustarima`` (installed
separately; see ``robstatm_py.check_setup()``).

Single entry point, mirroring the R API:

* :func:`arima_rob` → ``robustarima::arima.rob``

``arima.rob`` is *deterministic* given its input series (the randomness in the
Chapter-8 example scripts lives upstream in ``arima.sim`` / ``rnorm``). We fit
*inside* R-space (push the response to ``globalenv``, build the formula in R) so
the result equals R exactly, then read the fields with ``rx2``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstatm_py._converters import extract_array
from robstatm_py._r import r, require_r_pkg, rx2, rx2_opt


@dataclass(frozen=True, slots=True)
class ArimaRobResult:
    """Robust ARIMA fit (``robustarima::arima.rob``).

    Attributes
    ----------
    ar : ndarray, shape (p,)
        Autoregressive coefficients (``model$ar``); empty if ``p == 0``.
    ma : ndarray, shape (q,)
        Moving-average coefficients (``model$ma``); empty if ``q == 0``.
    ar_names, ma_names : tuple[str, ...]
        ``("AR(1)", ...)`` / ``("MA(1)", ...)`` as R names them.
    regcoef : ndarray, shape (n_reg,)
        Regression coefficients (``regcoef``); for a ``~ 1`` model this is the
        mean of the differenced series.
    regcoef_names : tuple[str, ...]
    regcoef_cov : ndarray, shape (n_reg, n_reg)
        Covariance of ``regcoef``.
    innov : ndarray, shape (n,)
        Innovations (leading entries are NaN during the AR warm-up).
    y_robust : ndarray, shape (n,)
        Robustly cleaned (AO-filtered) series.
    y_cleaned : ndarray, shape (n,)
        Cleaned series.
    regresid : ndarray
        Regression residuals.
    sigma_innov, sigma_regresid, sigma_first : float
        Innovations / regression-residual / first-stage scales.
    d, sd, sfreq, freq : int
        Differencing / seasonal-differencing / seasonal-freq / freq from ``model``.
    tuning_c, tauef : float
        Tau tuning constant and efficiency factor.
    n_predict : int
    innov_outlier : bool
    column_name : str | None
        Name of the response, if known.
    """

    ar: np.ndarray
    ma: np.ndarray
    ar_names: tuple[str, ...]
    ma_names: tuple[str, ...]
    regcoef: np.ndarray
    regcoef_names: tuple[str, ...]
    regcoef_cov: np.ndarray
    innov: np.ndarray
    y_robust: np.ndarray
    y_cleaned: np.ndarray
    regresid: np.ndarray
    sigma_innov: float
    sigma_regresid: float
    sigma_first: float
    d: int
    sd: int
    sfreq: int
    freq: int
    tuning_c: float
    tauef: float
    n_predict: int
    innov_outlier: bool
    column_name: str | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        order = f"p={self.ar.shape[0]} q={self.ma.shape[0]}"
        return (
            f"<ArimaRobResult: {order} n={self.y_robust.shape[0]} "
            f"sigma_innov={self.sigma_innov:.4g}>"
        )


def _arr(ro, expr: str) -> np.ndarray:
    return extract_array(ro.r(expr)).astype(float).ravel()


def _scalar(ro, expr: str) -> float:
    v = ro.r(expr)
    return float(np.asarray(v, dtype=float).ravel()[0])


def arima_rob(
    formula: str | None = None,
    data: "pd.DataFrame | None" = None,
    *,
    y=None,
    p: int = 0,
    q: int = 0,
    d: int = 0,
    sd: int = 0,
    freq: int = 1,
    sfreq: int | None = None,
    sma: bool = False,
    max_p: int | None = None,
    auto_ar: bool = False,
    n_predict: int = 20,
    tol: float = 1e-6,
    max_fcal: int = 2000,
    iter: bool = False,
    innov_outlier: bool = False,
    critv: float | None = None,
) -> ArimaRobResult:
    """Robust ARIMA estimation via the filtered tau-estimate (``arima.rob``).

    Two calling styles:

    * **Vector** — ``arima_rob(y=series, p=2, sd=1, sfreq=12)`` fits ``y ~ 1``.
      This matches every Chapter-8 example script.
    * **Formula + data** — ``arima_rob("col ~ 1", df, p=3)`` pushes ``df`` to R
      and builds the formula there.

    Parameters
    ----------
    formula : str, optional
        An R formula string (e.g. ``"resex ~ 1"``). Requires ``data``.
    data : pandas.DataFrame, optional
        Data for ``formula``.
    y : array_like, optional
        A bare numeric response vector (fits ``y ~ 1``). Mutually exclusive with
        ``formula``.
    p, q, d : int, default 0
        AR order, MA order, differencing.
    sd : int, default 0
        Seasonal differencing.
    freq, sfreq : int
        Frequency and seasonal frequency.
    sma : bool, default False
        Include a seasonal MA term.
    max_p : int, optional
    auto_ar : bool, default False
        Automatic AR-order selection. May emit a benign non-convergence warning.
    n_predict : int, default 20
    tol : float, default 1e-6
    max_fcal : int, default 2000
    iter : bool, default False
    innov_outlier : bool, default False
    critv : float, optional

    Returns
    -------
    ArimaRobResult

    Raises
    ------
    robstatm_py.RobStatTMSetupError
        If the ``robustarima`` R package is not installed.
    ValueError
        If neither / both of ``formula`` and ``y`` are given.

    Notes
    -----
    Deterministic given the input series; ``arima.sim``-based example scripts must
    reproduce the same seeded series in R for strict-tier parity.
    """
    if (formula is None) == (y is None):
        raise ValueError("provide exactly one of `formula` (with `data`) or `y`")

    require_r_pkg("robustarima")  # ensure installed (namespace only; no search-path attach)
    ro = r()

    # Build the kwargs string shared by both call styles.
    kw = [
        f"p={int(p)}", f"q={int(q)}", f"d={int(d)}", f"sd={int(sd)}",
        f"freq={int(freq)}",
        f"sma={'TRUE' if sma else 'FALSE'}",
        f"auto.ar={'TRUE' if auto_ar else 'FALSE'}",
        f"n.predict={int(n_predict)}",
        f"tol={float(tol)}", f"max.fcal={int(max_fcal)}",
        f"iter={'TRUE' if iter else 'FALSE'}",
        f"innov.outlier={'TRUE' if innov_outlier else 'FALSE'}",
    ]
    if sfreq is not None:
        kw.append(f"sfreq={int(sfreq)}")
    if max_p is not None:
        kw.append(f"max.p={int(max_p)}")
    if critv is not None:
        kw.append(f"critv={float(critv)}")
    kw_str = ", ".join(kw)

    col_name: str | None = None
    pushed: list[str] = []
    try:
        if y is not None:
            yarr = np.asarray(y, dtype=float).ravel()
            ro.globalenv["rpm_arima_y"] = yarr
            pushed.append("rpm_arima_y")
            fml = "rpm_arima_y ~ 1"
            data_arg = ""
        else:
            if data is None:
                raise ValueError("`formula` requires `data`")
            ro.globalenv["rpm_arima_df"] = data
            pushed.append("rpm_arima_df")
            fml = str(formula)
            data_arg = ", data=rpm_arima_df"
            col_name = fml.split("~")[0].strip()

        ro.r(
            f"rpm_arima_fit <- robustarima::arima.rob({fml}{data_arg}, {kw_str})"
        )
        pushed.append("rpm_arima_fit")
        fit = ro.r("rpm_arima_fit")

        model = rx2(fit, "model")
        ar_r = rx2_opt(model, "ar")
        ma_r = rx2_opt(model, "ma")
        ar = extract_array(ar_r).astype(float).ravel() if ar_r is not None else np.empty(0)
        ma = extract_array(ma_r).astype(float).ravel() if ma_r is not None else np.empty(0)
        ar_names = (
            tuple(str(n) for n in ro.r("names(rpm_arima_fit$model$ar)"))
            if ar_r is not None else ()
        )
        ma_names = (
            tuple(str(n) for n in ro.r("names(rpm_arima_fit$model$ma)"))
            if ma_r is not None else ()
        )

        regcoef = _arr(ro, "rpm_arima_fit$regcoef")
        regcoef_names = tuple(str(n) for n in ro.r("names(rpm_arima_fit$regcoef)"))
        regcoef_cov = np.asarray(ro.r("rpm_arima_fit$regcoef.cov"), dtype=float)
        if regcoef_cov.ndim == 1:
            regcoef_cov = regcoef_cov.reshape(regcoef.shape[0], regcoef.shape[0])

        result = ArimaRobResult(
            ar=ar,
            ma=ma,
            ar_names=ar_names,
            ma_names=ma_names,
            regcoef=regcoef,
            regcoef_names=regcoef_names,
            regcoef_cov=regcoef_cov,
            innov=_arr(ro, "rpm_arima_fit$innov"),
            y_robust=_arr(ro, "rpm_arima_fit$y.robust"),
            y_cleaned=_arr(ro, "rpm_arima_fit$y.cleaned"),
            regresid=_arr(ro, "rpm_arima_fit$regresid"),
            sigma_innov=_scalar(ro, "rpm_arima_fit$sigma.innov"),
            sigma_regresid=_scalar(ro, "rpm_arima_fit$sigma.regresid"),
            sigma_first=_scalar(ro, "rpm_arima_fit$sigma.first"),
            d=int(_scalar(ro, "rpm_arima_fit$model$d")),
            sd=int(_scalar(ro, "rpm_arima_fit$model$sd")),
            sfreq=int(_scalar(ro, "rpm_arima_fit$model$sfreq")),
            freq=int(_scalar(ro, "rpm_arima_fit$model$freq")),
            tuning_c=_scalar(ro, "rpm_arima_fit$tuning.c"),
            tauef=_scalar(ro, "rpm_arima_fit$tauef"),
            n_predict=int(_scalar(ro, "rpm_arima_fit$n.predict")),
            innov_outlier=bool(ro.r("rpm_arima_fit$innov.outlier")[0]),
            column_name=col_name,
            _r_fit=_fetch_raw("rpm_arima_fit"),
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
