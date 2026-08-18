"""Shared S3-method helpers for the lmrob* family of regression wrappers.

All three R functions (``lmrobdetMM``, ``lmrobdetDCML``, ``lmrobM``) return
objects that dispatch to ``summary.lmrobdetMM``, ``predict.lmrob``, and
``hatvalues.lmrob``. The Python wrappers therefore share one set of helper
functions and one summary/prediction dataclass.

Verified empirically against RobStatTM 1.0.11: ``class(summary(fit))`` ==
``"summary.lmrobdetMM"`` for all three fit types.

Per ``project_memory/discoveries.md`` (2026-06-11), S3 dispatch from a
converted rpy2 ListVector is impossible because the auto-conversion
context strips the S3 class attribute. The pattern below is therefore
"refit on the R side in globalenv, dispatch there, extract, cleanup".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from robstattm_py._r import r, r_guard, r_pkg
from robstattm_py.regression._formula import df_with_r_names

# ---------------------------------------------------------------------------
# Result dataclasses (shared across lmrobdetMM / lmrobdetDCML / lmrobM)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LmrobdetMMSummary:
    """Result of ``.summary()`` on any lmrob* result.

    Mirrors R's ``summary(<lmrobdetMM>)`` output. Strict-tier
    field-for-field tests live in the matching test files.

    Attributes
    ----------
    coefficients_table : pandas.DataFrame
        Columns ``["Estimate", "Std. Error", "t value", "Pr(>|t|)"]``,
        index = coefficient names.
    cov : numpy.ndarray, shape (p, p)
    residuals : numpy.ndarray, shape (n,)
    scale : float
    sigma : float
    r_squared : float
    adj_r_squared : float
    df : tuple[int, int, int]
    converged : bool
    iter : int
    formula : str
    """

    coefficients_table: pd.DataFrame
    cov: np.ndarray
    residuals: np.ndarray
    scale: float
    sigma: float
    df: tuple
    converged: bool
    iter: int
    formula: str
    r_squared: float | None = None
    adj_r_squared: float | None = None

    def __repr__(self) -> str:
        lines = [f"Call: lmrobdetMM-family({self.formula})", "", "Coefficients:"]
        lines.append(self.coefficients_table.to_string(float_format=lambda v: f"{v:.5g}"))
        lines.append("")
        lines.append(f"Robust residual standard error: {self.scale:.4g}")
        if self.r_squared is not None:
            lines.append(
                f"Multiple R-squared: {self.r_squared:.4g}, "
                f"Adjusted R-squared: {self.adj_r_squared:.4g}"
            )
        lines.append(
            f"Convergence in {self.iter} IRWLS iterations"
            if self.converged else f"NOT converged after {self.iter} iterations"
        )
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        r2_html = (
            f"R²: {self.r_squared:.4g} · Adj R²: {self.adj_r_squared:.4g} · "
            if self.r_squared is not None else ""
        )
        return (
            f"<div><b>summary:</b> <code>{self.formula}</code></div>"
            f"{self.coefficients_table.to_html(float_format='%.5g')}"
            f"<div>Residual scale: {self.scale:.4g} · {r2_html}"
            f"iter: {self.iter} · converged: {self.converged}</div>"
        )


@dataclass(frozen=True, slots=True)
class LmrobdetMMPrediction:
    """Result of ``.predict(se_fit=True)`` on any lmrob* fit.

    Mirrors R's ``predict(.., se.fit=TRUE)``.
    """

    fit: np.ndarray
    se_fit: np.ndarray
    df: int
    residual_scale: float


@dataclass(frozen=True, slots=True)
class Drop1Result:
    """Result of ``.drop1()`` on an :class:`LmrobdetMMResult`.

    Port of R's ``drop1.lmrobdetMM``, the single-term-deletion table that
    reports the Robust Final Prediction Error (RFPE) for the full model and
    for each sub-model obtained by dropping one term.

    Attributes
    ----------
    table : pandas.DataFrame
        Index is the row labels (``"<none>"`` then the dropped term labels);
        columns are ``["Df", "RFPE"]`` exactly as R's anova object. The
        ``"<none>"`` row has ``Df = NaN``.
    terms : tuple[str, ...]
        Row labels (``"<none>"`` included), in R's order.
    df : numpy.ndarray
        Degrees of freedom dropped per row (NaN for ``"<none>"``).
    rfpe : numpy.ndarray
        RFPE per row.
    scale : float
        Residual scale used to compute the RFPE values.
    formula : str
        Formula of the model the deletions are measured against.
    """

    table: pd.DataFrame
    terms: tuple
    df: np.ndarray
    rfpe: np.ndarray
    scale: float
    formula: str

    @property
    def recommended(self) -> str:
        """Row label with the lowest RFPE.

        If this is ``"<none>"`` the full model is preferred; otherwise it is
        the single term whose deletion most improves the RFPE.
        """
        return str(self.terms[int(np.argmin(self.rfpe))])

    def __repr__(self) -> str:
        return (
            f"<Drop1Result: {self.formula} | {len(self.terms)} rows | "
            f"best={self.recommended!r}>\n"
            + self.table.to_string(float_format=lambda v: f"{v:.5g}")
        )

    def _repr_html_(self) -> str:
        return (
            f"<div><b>drop1:</b> <code>{self.formula}</code> · "
            f"recommended: <code>{self.recommended}</code></div>"
            + self.table.to_html(float_format="%.5g")
        )


# ---------------------------------------------------------------------------
# Refit / cleanup helpers
# ---------------------------------------------------------------------------


def _refit_in_globalenv(
    formula: str,
    data: pd.DataFrame,
    rfn_name: str,
    varname: str,
    r_control=None,
) -> None:
    """Push ``data`` to R and refit ``rfn_name(formula, data=...)`` into ``varname``.

    When ``r_control`` is given (the live R control list the original fit
    used), it is passed through as ``control=`` so the refit reproduces the
    *same* model, not a default-control one.  This is essential for
    parity: ``.summary()`` / ``.predict()`` / ``.hatvalues()`` on a fit built
    with a non-default control must reflect that control, not R's defaults.

    Caller is responsible for the matching cleanup via
    :func:`_cleanup_method_vars` in a finally block.
    """
    if data is None:
        raise ValueError(
            "fit must have access to its original data to dispatch S3 "
            "methods; pass the DataFrame directly to the wrapper"
        )
    ro = r()
    _ = r_pkg("RobStatTM")
    ro.globalenv["rpm_methods_data"] = df_with_r_names(data)
    # The refit reproduces the model, so it re-emits the same R warnings the
    # original fit did (non-convergence, NaNs, ...) and can hit the same R
    # errors. Guard it so both surface to the Python user (RobStatTMWarning /
    # RobStatTMRError) instead of vanishing into rpy2's console callback.
    with r_guard():
        if r_control is not None:
            ro.globalenv["rpm_methods_ctrl"] = r_control
            ro.r(
                f"{varname} <- {rfn_name}({formula}, data=rpm_methods_data, "
                f"control=rpm_methods_ctrl)"
            )
        else:
            ro.r(f"{varname} <- {rfn_name}({formula}, data=rpm_methods_data)")


def _cleanup_method_vars(*names: str) -> None:
    ro = r()
    ro.r(
        "for (v in c("
        + ",".join(f"'{n}'" for n in (*names, "rpm_methods_data", "rpm_methods_ctrl"))
        + ")) if (exists(v)) rm(list=v)"
    )


# ---------------------------------------------------------------------------
# Method ports
# ---------------------------------------------------------------------------


def summary_of(
    formula: str,
    data: pd.DataFrame,
    coef_names: tuple[str, ...],
    rfn_name: str,
    r_control=None,
) -> LmrobdetMMSummary:
    """Run R's ``summary()`` on a freshly refit model and return the dataclass."""
    ro = r()
    _refit_in_globalenv(formula, data, rfn_name, "rpm_methods_fit", r_control)
    try:
        ro.r("rpm_methods_summ <- summary(rpm_methods_fit)")
        coefs = np.asarray(ro.r("rpm_methods_summ$coefficients"), dtype=float)
        cov = np.asarray(ro.r("rpm_methods_summ$cov"), dtype=float)
        resids = np.asarray(ro.r("rpm_methods_summ$residuals"), dtype=float).ravel()
        scale = float(ro.r("rpm_methods_summ$scale")[0])
        sigma = float(ro.r("rpm_methods_summ$sigma")[0])
        # r.squared / adj.r.squared are present on lmrobdetMM and lmrobM
        # summaries but absent on lmrobdetDCML summaries (verified). When
        # absent, R returns NULL (rpy2's NULLType, which has no __len__).
        def _opt_scalar(expr: str):
            val = ro.r(expr)
            try:
                if len(val) == 0:
                    return None
            except TypeError:  # NULLType
                return None
            return float(val[0])

        r_sq = _opt_scalar("rpm_methods_summ$r.squared")
        adj_r_sq = _opt_scalar("rpm_methods_summ$adj.r.squared")
        df_arr = np.asarray(ro.r("rpm_methods_summ$df"), dtype=int).ravel()
        converged = bool(ro.r("rpm_methods_summ$converged")[0])
        it = int(ro.r("rpm_methods_summ$iter")[0])
    finally:
        _cleanup_method_vars("rpm_methods_fit", "rpm_methods_summ")

    table = pd.DataFrame(
        coefs,
        index=list(coef_names),
        columns=["Estimate", "Std. Error", "t value", "Pr(>|t|)"],
    )
    return LmrobdetMMSummary(
        coefficients_table=table,
        cov=cov,
        residuals=resids,
        scale=scale,
        sigma=sigma,
        r_squared=r_sq,
        adj_r_squared=adj_r_sq,
        df=tuple(int(x) for x in df_arr),
        converged=converged,
        iter=it,
        formula=formula,
    )


def predict_of(
    formula: str,
    data: pd.DataFrame,
    rfn_name: str,
    newdata: pd.DataFrame | None = None,
    *,
    se_fit: bool = False,
    r_control=None,
):
    """Run R's ``predict()`` on a freshly refit model."""
    ro = r()
    _refit_in_globalenv(formula, data, rfn_name, "rpm_methods_fit", r_control)
    cleanup = ["rpm_methods_fit"]
    try:
        if newdata is not None:
            if not isinstance(newdata, pd.DataFrame):
                raise TypeError("newdata must be a pandas.DataFrame")
            ro.globalenv["rpm_methods_newdata"] = df_with_r_names(newdata)
            cleanup.append("rpm_methods_newdata")
            base = "predict(rpm_methods_fit, newdata=rpm_methods_newdata"
        else:
            base = "predict(rpm_methods_fit"

        if se_fit:
            ro.r(f"rpm_methods_pred <- {base}, se.fit=TRUE)")
            cleanup.append("rpm_methods_pred")
            fit_arr = np.asarray(ro.r("rpm_methods_pred$fit"), dtype=float).ravel()
            se_arr = np.asarray(ro.r("rpm_methods_pred$se.fit"), dtype=float).ravel()
            df_val = int(ro.r("rpm_methods_pred$df")[0])
            rs_raw = ro.r("rpm_methods_pred$residual.scale")
            rs = float(rs_raw[0]) if len(rs_raw) else float("nan")
            return LmrobdetMMPrediction(
                fit=fit_arr, se_fit=se_arr, df=df_val, residual_scale=rs,
            )
        else:
            ro.r(f"rpm_methods_pred <- {base})")
            cleanup.append("rpm_methods_pred")
            return np.asarray(ro.r("rpm_methods_pred"), dtype=float).ravel()
    finally:
        _cleanup_method_vars(*cleanup)


def hatvalues_of(formula: str, data: pd.DataFrame, rfn_name: str, r_control=None) -> np.ndarray:
    """Run R's ``hatvalues()`` on a freshly refit model."""
    ro = r()
    _refit_in_globalenv(formula, data, rfn_name, "rpm_methods_fit", r_control)
    try:
        return np.asarray(ro.r("hatvalues(rpm_methods_fit)"), dtype=float).ravel()
    finally:
        _cleanup_method_vars("rpm_methods_fit")


# ---------------------------------------------------------------------------
# Manual primitives used when R's S3 dispatch is unavailable
# ---------------------------------------------------------------------------
#
# Background (2026-06-11): ``lmrobM`` fits have class
# ``c("lmrobM", "lmrobdetMM")`` - they do NOT inherit from ``lmrob``, so
# robustbase's ``predict.lmrob`` and ``hatvalues.lmrob`` refuse to dispatch
# ("no applicable method"). RobStatTM also ships no replacement methods.
#
# Workaround: the underlying primitives are well-defined and we can call
# them from R directly, preserving strict-tier bit-equality:
#
#   predict   = model.matrix(formula, newdata|data) %*% coef(fit)
#               (verified identical() to predict.lmrob on MM fits)
#   hatvalues = diag(Q Q^T) where Q = qr.Q(qr(sqrt(rweights) * X))
#               (matches the source of hatvalues.lmrob in robustbase)
#
# We use these whenever the S3 path is unavailable.


def predict_manual(
    formula: str,
    data: pd.DataFrame,
    rfn_name: str,
    newdata: pd.DataFrame | None = None,
    r_control=None,
) -> np.ndarray:
    """Compute predictions via ``model.matrix() %*% coef(fit)`` in R.

    Equivalent to ``predict.lmrob(fit, newdata, type='response')`` but
    works for fits whose class hierarchy doesn't trigger R's S3 dispatch
    (notably ``lmrobM``). Numerically identical: `identical()` returns
    TRUE on lmrobdetMM fits.
    """
    ro = r()
    _refit_in_globalenv(formula, data, rfn_name, "rpm_methods_fit", r_control)
    cleanup = ["rpm_methods_fit"]
    try:
        if newdata is not None:
            if not isinstance(newdata, pd.DataFrame):
                raise TypeError("newdata must be a pandas.DataFrame")
            ro.globalenv["rpm_methods_newdata"] = df_with_r_names(newdata)
            cleanup.append("rpm_methods_newdata")
            # Use formula(fit) and pass data explicitly so model.matrix
            # doesn't need to resolve the response from any environment.
            ro.r(
                "rpm_methods_pred <- as.numeric("
                "model.matrix(delete.response(terms(formula(rpm_methods_fit))), "
                "data=rpm_methods_newdata) %*% coef(rpm_methods_fit))"
            )
        else:
            ro.r(
                "rpm_methods_pred <- as.numeric("
                "model.matrix(formula(rpm_methods_fit), "
                "data=rpm_methods_data) %*% coef(rpm_methods_fit))"
            )
        cleanup.append("rpm_methods_pred")
        return np.asarray(ro.r("rpm_methods_pred"), dtype=float).ravel()
    finally:
        _cleanup_method_vars(*cleanup)


def hatvalues_manual(formula: str, data: pd.DataFrame, rfn_name: str, r_control=None) -> np.ndarray:
    """Compute hat-matrix diagonal via QR of ``sqrt(rweights) * X`` in R.

    Equivalent to robustbase's ``hatvalues.lmrob`` source. Numerically
    identical: ``identical()`` returns TRUE on lmrobdetMM fits.
    """
    ro = r()
    _refit_in_globalenv(formula, data, rfn_name, "rpm_methods_fit", r_control)
    try:
        ro.r(
            "rpm_methods_hat_X  <- model.matrix(formula(rpm_methods_fit), "
            "                                   data=rpm_methods_data); "
            "rpm_methods_hat_w  <- rpm_methods_fit$rweights; "
            "rpm_methods_hat_Q  <- qr.Q(qr(sqrt(rpm_methods_hat_w) * "
            "                                  rpm_methods_hat_X)); "
            "rpm_methods_hat    <- diag(rpm_methods_hat_Q %*% "
            "                            t(rpm_methods_hat_Q))"
        )
        out = np.asarray(ro.r("rpm_methods_hat"), dtype=float).ravel()
    finally:
        _cleanup_method_vars(
            "rpm_methods_fit", "rpm_methods_hat_X", "rpm_methods_hat_w",
            "rpm_methods_hat_Q", "rpm_methods_hat",
        )
    return out


def r_squared_classic(formula: str, data: pd.DataFrame, rfn_name: str, r_control=None) -> float:
    """Compute the *classical* (least-squares) R² for any fit.

    Used by ``LmrobdetDCMLResult.r_squared_classic`` because R's
    ``lmrobdetDCML`` does not populate ``$r.squared`` on the fit (the
    DCML algorithm has no natural robust-R² statistic, see
    ``project_memory/discoveries.md`` 2026-06-11).

    This returns the **classical** statistic
    ``1 - sum(residuals^2) / sum((y - mean(y))^2)``, NOT the robust R².
    Use it only when you understand the semantic difference.
    """
    ro = r()
    _refit_in_globalenv(formula, data, rfn_name, "rpm_methods_fit", r_control)
    try:
        ro.r(
            "rpm_methods_y  <- model.response(model.frame("
            "                       formula(rpm_methods_fit), "
            "                       data=rpm_methods_data)); "
            "rpm_methods_r2 <- 1 - sum(rpm_methods_fit$residuals^2) / "
            "                       sum((rpm_methods_y - "
            "                            mean(rpm_methods_y))^2)"
        )
        val = float(ro.r("rpm_methods_r2")[0])
    finally:
        _cleanup_method_vars(
            "rpm_methods_fit", "rpm_methods_y", "rpm_methods_r2",
        )
    return val


def rfpe_of(
    formula: str,
    data: pd.DataFrame,
    *,
    both_vals: bool = False,
    r_control=None,
):
    """Run R's ``lmrobdetMM.RFPE()`` on a freshly refit ``lmrobdetMM`` model.

    Only valid for lmrobdetMM fits, DCML and lmrobM are not RFPE-scored.
    """
    ro = r()
    _refit_in_globalenv(formula, data, "lmrobdetMM", "rpm_methods_fit", r_control)
    try:
        if both_vals:
            ro.r("rpm_methods_rfpe <- lmrobdetMM.RFPE(rpm_methods_fit, bothVals=TRUE)")
            a = float(ro.r("rpm_methods_rfpe$minRhoMM.C")[0])
            b = float(ro.r("rpm_methods_rfpe$penaltyRFPE")[0])
            return (a, b)
        return float(ro.r("lmrobdetMM.RFPE(rpm_methods_fit)")[0])
    finally:
        _cleanup_method_vars("rpm_methods_fit", "rpm_methods_rfpe")


def drop1_of(
    formula: str,
    data: pd.DataFrame,
    r_control,
    *,
    scope=None,
    scale: float | None = None,
) -> Drop1Result:
    """Run R's ``drop1.lmrobdetMM()`` on a freshly refit ``lmrobdetMM`` model.

    The fit is rebuilt in ``globalenv`` via a literal R command (so its
    ``$call`` is clean and ``drop1``'s internal ``update()`` can re-evaluate
    each sub-model). ``lmrobdetMM`` is deterministic (Pena-Yohai initial), so
    the result reproduces a direct R ``drop1(lmrobdetMM(...))`` bit-for-bit
    without any seeding.

    Parameters
    ----------
    formula : str
    data : pandas.DataFrame
    r_control : rpy2 object or None
        The R control list (from ``_control_to_r``) when the fit used a
        non-default control; ``None`` to refit with ``lmrobdetMM`` defaults.
    scope : sequence[str] or str, optional
        Term labels to consider for dropping. ``None`` drops every term
        (R's default). A single string is treated as one term label.
    scale : float, optional
        Residual scale for the RFPE. If ``None``, the fit's own scale is used.

    Returns
    -------
    Drop1Result
    """
    if data is None:
        raise ValueError(
            "fit must have access to its original data to compute drop1; "
            "pass the DataFrame directly to lmrobdet_mm"
        )
    ro = r()
    _ = r_pkg("RobStatTM")
    ro.globalenv["rpm_drop_data"] = df_with_r_names(data)
    cleanup = ["rpm_drop_data", "rpm_drop_fit", "rpm_drop_aod"]
    try:
        with r_guard():
            if r_control is not None:
                ro.globalenv["rpm_drop_ctrl"] = r_control
                cleanup.append("rpm_drop_ctrl")
                ro.r(
                    f"rpm_drop_fit <- lmrobdetMM({formula}, data=rpm_drop_data, "
                    f"control=rpm_drop_ctrl)"
                )
            else:
                ro.r(f"rpm_drop_fit <- lmrobdetMM({formula}, data=rpm_drop_data)")

        call_args = ["rpm_drop_fit"]
        if scope is not None:
            terms_list = [scope] if isinstance(scope, str) else list(scope)
            for t in terms_list:
                if not isinstance(t, str):
                    raise TypeError("scope must be a string or a sequence of term-label strings")
            vec = "c(" + ", ".join('"' + t + '"' for t in terms_list) + ")"
            call_args.append(vec)
        drop_call = "drop1(" + ", ".join(call_args)
        if scale is not None:
            drop_call += f", scale={float(scale)}"
        drop_call += ")"
        ro.r(f"rpm_drop_aod <- {drop_call}")

        terms = tuple(str(t) for t in ro.r("rownames(rpm_drop_aod)"))
        df_arr = np.asarray(ro.r("as.numeric(rpm_drop_aod$Df)"), dtype=float).ravel()
        rfpe = np.asarray(ro.r("as.numeric(rpm_drop_aod$RFPE)"), dtype=float).ravel()
        scale_used = (
            float(scale) if scale is not None
            else float(ro.r("rpm_drop_fit$scale")[0])
        )
    finally:
        ro.r(
            "for (v in c("
            + ",".join(f"'{n}'" for n in cleanup)
            + ")) if (exists(v)) rm(list=v)"
        )

    table = pd.DataFrame({"Df": df_arr, "RFPE": rfpe}, index=list(terms))
    return Drop1Result(
        table=table,
        terms=terms,
        df=df_arr,
        rfpe=rfpe,
        scale=scale_used,
        formula=formula,
    )
