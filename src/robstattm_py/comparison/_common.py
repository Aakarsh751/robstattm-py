"""Shared machinery for the comparison wrappers (``lm``/``glm``/``lts``/``rlm``/``lmrob``).

Everything in ``robstattm_py.comparison`` wraps a **non-RobStatTM** R model so it
can be lined up against a RobStatTM robust fit (this is exactly what Doug Martin's
``methods("summary")`` list and the ``fit.models`` vignette are about). The models
come from three R packages:

* ``stats``      -> ``lm``, ``glm``     (always attached)
* ``MASS``       -> ``rlm``
* ``robustbase`` -> ``lmrob``, ``ltsReg``

The wrappers return **native Python** result objects in the same idiom as the rest
of RobStatTM-Py (frozen dataclasses, numpy/pandas fields, ``.summary()`` porting
R's ``summary.*``), so a Python user can read every number without touching rpy2.

Two R-side operations are shared here:

* :func:`fit_raw` fits once via :func:`~robstattm_py._r.rcall` (the safe primitive:
  no R source strings are built from Python values, see
  ``gotcha_rpy2_rcall_marshalling``) and pulls the common fit fields.
* :func:`summarize` / :func:`predict_classical` refit the model *by name in
  globalenv* so R's S3 dispatch (``summary.lm``, ``predict.lmrob``, ...) fires,
  then extract. This mirrors ``regression/_s3_methods.py``: the converted
  ``_r_fit`` has lost its S3 class on the rpy2 boundary, so it cannot be
  dispatched on directly.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import extract_array, extract_int
from robstattm_py._r import r, r_guard, r_pkg, require_r_pkg, rx2, rx2_opt
from robstattm_py.regression._formula import (
    coef_names_for,
    df_with_r_names,
    resolve_formula_args,
)

# Temp globalenv names used by the refit-based method ports. Prefixed so they
# never collide with the ``rpm_*`` names the RobStatTM S3 ports use, and removed
# in a finally block after each call.
_TEMP_VARS = (
    "rpm_cmp_fit",
    "rpm_cmp_data",
    "rpm_cmp_summ",
    "rpm_cmp_pred",
    "rpm_cmp_newdata",
)


# ---------------------------------------------------------------------------
# Shared result pieces
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ComparisonSummary:
    """Result of ``.summary()`` on any comparison fit.

    Mirrors R's ``summary(<fit>)`` for the classical/reference models. The
    coefficient table keeps **R's own column names** (they differ by model:
    ``lm`` has ``t value``/``Pr(>|t|)``, ``glm`` has ``z value``, ``rlm`` has
    no p-value column), so the table reads exactly like R's.

    Attributes
    ----------
    model : str
        Which estimator produced this (``"lm"``, ``"glm"``, ...).
    formula : str
    coefficients_table : pandas.DataFrame
        Index = coefficient names; columns = R's ``colnames(summary$coefficients)``.
    sigma : float or None
        Residual standard error where the model defines one.
    r_squared, adj_r_squared : float or None
        Present for ``lm``/``lmrob``/``ltsReg``; ``None`` for ``glm``/``rlm``.
    fstatistic : tuple or None
        ``(value, numdf, dendf)`` when R reports one.
    df : tuple or None
        R's ``summary$df``.
    residuals : numpy.ndarray
    """

    model: str
    formula: str
    coefficients_table: pd.DataFrame
    sigma: float | None
    r_squared: float | None
    adj_r_squared: float | None
    fstatistic: tuple | None
    df: tuple | None
    residuals: np.ndarray

    def __repr__(self) -> str:
        lines = [f"Call: {self.model}({self.formula})", "", "Coefficients:"]
        lines.append(
            self.coefficients_table.to_string(float_format=lambda v: f"{v:.5g}")
        )
        lines.append("")
        if self.sigma is not None:
            lines.append(f"Residual standard error: {self.sigma:.4g}")
        if self.r_squared is not None:
            lines.append(
                f"Multiple R-squared: {self.r_squared:.4g}, "
                f"Adjusted R-squared: {self.adj_r_squared:.4g}"
            )
        if self.fstatistic is not None:
            f, ndf, ddf = self.fstatistic
            lines.append(f"F-statistic: {f:.4g} on {int(ndf)} and {int(ddf)} DF")
        return "\n".join(lines).rstrip()

    def _repr_html_(self) -> str:
        parts: list[str] = []
        if self.sigma is not None:
            parts.append(f"Residual std error: {self.sigma:.4g}")
        if self.r_squared is not None:
            parts.append(f"R&sup2;: {self.r_squared:.4g}")
            parts.append(f"Adj R&sup2;: {self.adj_r_squared:.4g}")
        return (
            f"<div><b>summary ({self.model}):</b> <code>{self.formula}</code></div>"
            f"{self.coefficients_table.to_html(float_format='%.5g')}"
            f"<div>{' &middot; '.join(parts)}</div>"
        )


@dataclass(frozen=True, slots=True)
class ComparisonPrediction:
    """Result of ``.predict(se_fit=True)`` on a comparison fit.

    Mirrors R's ``predict(.., se.fit=TRUE)``.
    """

    fit: np.ndarray
    se_fit: np.ndarray
    df: int | None
    residual_scale: float | None


# ---------------------------------------------------------------------------
# One-shot fit (safe rcall path) + raw field extraction
# ---------------------------------------------------------------------------


def fit_raw(
    formula: str | None,
    data: Any,
    *,
    pkg_name: str,
    fn_attr: str,
    X=None,
    y=None,
    extra_named: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit ``pkg_name::fn_attr(formula, data=...)`` once and pull common fields.

    Returns a dict with ``coefficients``, ``coef_names``, ``residuals``,
    ``fitted_values``, ``rank``, ``df_residual``, ``formula``, ``data`` (a
    defensive copy) and ``r_fit`` (the converted handle). Model-specific extras
    are read by the caller from ``r_fit`` via :func:`opt_float` / :func:`rx2`.
    """
    formula, data = resolve_formula_args(formula, data, X=X, y=y)
    ro = r()
    pkg = r_pkg(pkg_name)
    rfun = getattr(pkg, fn_attr)

    ro.globalenv["rpm_data"] = df_with_r_names(data)
    rformula = ro.Formula(formula)
    try:
        with r_guard(hint="check data dtypes and column names"):
            r_fit = rfun(rformula, data=ro.globalenv["rpm_data"], **(extra_named or {}))
        # model.matrix needs the frame present to expand dot / factor formulas.
        coef_names = coef_names_for(formula)
    finally:
        ro.r("if (exists('rpm_data')) rm(rpm_data)")

    coef = extract_array(rx2(r_fit, "coefficients")).astype(float).ravel()
    resid = _opt_array(rx2_opt(r_fit, "residuals"))
    fitted = _opt_array(rx2_opt(r_fit, "fitted.values"))
    rank = rx2_opt(r_fit, "rank")
    df_res = rx2_opt(r_fit, "df.residual")
    return {
        "coefficients": coef,
        "coef_names": coef_names,
        "residuals": resid if resid is not None else np.empty(0),
        "fitted_values": fitted if fitted is not None else np.empty(0),
        "rank": extract_int(rank) if rank is not None else len(coef),
        "df_residual": extract_int(df_res) if df_res is not None else -1,
        "formula": formula,
        "data": data.copy(),
        "r_fit": r_fit,
    }


def _opt_array(rval) -> np.ndarray | None:
    if rval is None:
        return None
    try:
        arr = np.asarray(rval, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    return arr if arr.size else None


# ---------------------------------------------------------------------------
# Refit-in-globalenv method ports (S3 dispatch needs a live-classed object)
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _live_fit(formula: str, data: pd.DataFrame, call_head: str, require: str | None, extra: str):
    """Refit ``call_head(formula, data=rpm_cmp_data <extra>)`` into ``rpm_cmp_fit``.

    ``call_head`` is written in R, e.g. ``"lm"``, ``"glm"``, ``"MASS::rlm"``,
    ``"robustbase::lmrob"``. For non-base packages we require the namespace
    (without attaching it, so RobStatTM's own generics are never masked) and
    call ``pkg::fn`` so the function resolves regardless of the search path.
    """
    if data is None:
        raise ValueError(
            "fit must have access to its original data to dispatch S3 methods; "
            "pass the DataFrame directly to the wrapper"
        )
    ro = r()
    if require is not None:
        require_r_pkg(require)
    ro.globalenv["rpm_cmp_data"] = df_with_r_names(data)
    with r_guard():
        ro.r(f"rpm_cmp_fit <- {call_head}({formula}, data = rpm_cmp_data{extra})")
    try:
        yield ro
    finally:
        _cleanup(ro)


def _cleanup(ro) -> None:
    ro.r(
        "for (v in c("
        + ",".join(f"'{v}'" for v in _TEMP_VARS)
        + ")) if (exists(v)) rm(list=v)"
    )


def opt_float(ro, expr: str) -> float | None:
    """Evaluate ``expr`` in R, returning ``None`` for NULL / zero-length."""
    val = ro.r(expr)
    try:
        if len(val) == 0:
            return None
    except TypeError:  # NULLType has no __len__
        return None
    return float(val[0])


def summarize(
    formula: str,
    data: pd.DataFrame,
    *,
    model: str,
    call_head: str,
    require: str | None = None,
    extra: str = "",
) -> ComparisonSummary:
    """Refit and run R's ``summary()``, returning :class:`ComparisonSummary`."""
    with _live_fit(formula, data, call_head, require, extra) as ro:
        ro.r("rpm_cmp_summ <- summary(rpm_cmp_fit)")
        coefs = np.asarray(ro.r("rpm_cmp_summ$coefficients"), dtype=float)
        col_names = [str(c) for c in ro.r("colnames(rpm_cmp_summ$coefficients)")]
        row_names = [str(c) for c in ro.r("rownames(rpm_cmp_summ$coefficients)")]
        sigma = opt_float(ro, "rpm_cmp_summ$sigma")
        r_sq = opt_float(ro, "rpm_cmp_summ$r.squared")
        adj = opt_float(ro, "rpm_cmp_summ$adj.r.squared")
        fstat = _opt_tuple(ro, "rpm_cmp_summ$fstatistic")
        df_tup = _opt_tuple(ro, "rpm_cmp_summ$df", as_int=True)
        resid = _opt_array(ro.r("rpm_cmp_summ$residuals"))
        if resid is None:
            resid = _opt_array(ro.r("residuals(rpm_cmp_fit)"))

    if coefs.ndim == 1:
        coefs = coefs.reshape(1, -1)
    table = pd.DataFrame(coefs, index=row_names, columns=col_names)
    return ComparisonSummary(
        model=model,
        formula=formula,
        coefficients_table=table,
        sigma=sigma,
        r_squared=r_sq,
        adj_r_squared=adj,
        fstatistic=fstat,
        df=df_tup,
        residuals=resid if resid is not None else np.empty(0),
    )


def _opt_tuple(ro, expr: str, *, as_int: bool = False) -> tuple | None:
    val = ro.r(expr)
    try:
        if len(val) == 0:
            return None
    except TypeError:
        return None
    arr = np.asarray(val).ravel()
    if as_int:
        return tuple(int(x) for x in arr)
    return tuple(float(x) for x in arr)


def predict_classical(
    formula: str,
    data: pd.DataFrame,
    *,
    call_head: str,
    require: str | None = None,
    extra: str = "",
    newdata: pd.DataFrame | None = None,
    se_fit: bool = False,
    predict_args: str = "",
) -> np.ndarray | ComparisonPrediction:
    """Refit and run R's ``predict()`` (optionally with ``se.fit=TRUE``).

    ``predict_args`` is appended verbatim to the ``predict()`` call (e.g.
    ``", type = 'response'"`` for a glm); it is code the wrapper controls, never
    a user-supplied string.
    """
    with _live_fit(formula, data, call_head, require, extra) as ro:
        if newdata is not None:
            if not isinstance(newdata, pd.DataFrame):
                raise TypeError("newdata must be a pandas.DataFrame")
            ro.globalenv["rpm_cmp_newdata"] = df_with_r_names(newdata)
            base = "predict(rpm_cmp_fit, newdata = rpm_cmp_newdata"
        else:
            base = "predict(rpm_cmp_fit"

        if se_fit:
            ro.r(f"rpm_cmp_pred <- {base}, se.fit = TRUE{predict_args})")
            fit_arr = np.asarray(ro.r("rpm_cmp_pred$fit"), dtype=float).ravel()
            se_arr = np.asarray(ro.r("rpm_cmp_pred$se.fit"), dtype=float).ravel()
            df_val = _opt_int(ro, "rpm_cmp_pred$df")
            rs = opt_float(ro, "rpm_cmp_pred$residual.scale")
            return ComparisonPrediction(
                fit=fit_arr, se_fit=se_arr, df=df_val, residual_scale=rs
            )
        ro.r(f"rpm_cmp_pred <- {base}{predict_args})")
        return np.asarray(ro.r("rpm_cmp_pred"), dtype=float).ravel()


def _opt_int(ro, expr: str) -> int | None:
    val = ro.r(expr)
    try:
        if len(val) == 0:
            return None
    except TypeError:
        return None
    return int(val[0])


def vcov_of(
    formula: str,
    data: pd.DataFrame,
    *,
    call_head: str,
    require: str | None = None,
    extra: str = "",
) -> pd.DataFrame:
    """Refit and return R's ``vcov()`` as a labelled coefficient covariance."""
    with _live_fit(formula, data, call_head, require, extra) as ro:
        ro.r("rpm_cmp_v <- as.matrix(vcov(rpm_cmp_fit))")
        m = np.asarray(ro.r("rpm_cmp_v"), dtype=float)
        names = [str(x) for x in ro.r("colnames(rpm_cmp_v)")]
        ro.r("if (exists('rpm_cmp_v')) rm(rpm_cmp_v)")
    if m.ndim == 1:
        m = m.reshape(len(names), len(names))
    return pd.DataFrame(m, index=names, columns=names)


def confint_of(
    formula: str,
    data: pd.DataFrame,
    *,
    call_head: str,
    require: str | None = None,
    extra: str = "",
    level: float = 0.95,
) -> pd.DataFrame:
    """Refit and return R's ``confint()`` as a labelled interval table."""
    with _live_fit(formula, data, call_head, require, extra) as ro:
        ro.r(f"rpm_cmp_ci <- as.matrix(confint(rpm_cmp_fit, level = {float(level)}))")
        m = np.asarray(ro.r("rpm_cmp_ci"), dtype=float)
        rn = [str(x) for x in ro.r("rownames(rpm_cmp_ci)")]
        cn = [str(x) for x in ro.r("colnames(rpm_cmp_ci)")]
        ro.r("if (exists('rpm_cmp_ci')) rm(rpm_cmp_ci)")
    if m.ndim == 1:
        m = m.reshape(len(rn), len(cn))
    return pd.DataFrame(m, index=rn, columns=cn)
