"""M-estimator regression with designed experiments.

Wraps ``RobStatTM::lmrobM``. Maronna et al. (2019) §4.4. Use when the design
is fixed and there is no leverage outlier concern.

R return list:
  coefficients, scale, residuals, loss, converged, iter, fitted.values,
  rweights, control, init, qr, rank, cov, df.residual, degree.freedom,
  r.squared, ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd

from robstattm_py._converters import (
    extract_array,
    extract_bool,
    extract_float,
    extract_int,
)
from robstattm_py._r import r, r_pkg, rcall, rx2
from robstattm_py.regression._formula import (
    cleanup_r_var,
    coef_names_for,
    push_df_to_r,
)
from robstattm_py.regression._s3_methods import (
    LmrobdetMMSummary,
    hatvalues_manual,
    predict_manual,
    summary_of,
)
from robstattm_py.regression.control_m import LmrobMControl, _control_m_to_r


@dataclass(frozen=True, slots=True)
class LmrobMResult:
    """``lmrobM`` regression result."""

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    scale: float
    residuals: np.ndarray
    loss: float
    converged: bool
    iter: int
    fitted_values: np.ndarray
    rweights: np.ndarray
    rank: int
    cov: np.ndarray
    df_residual: int
    degree_freedom: int
    r_squared: float
    formula: str
    _r_fit: Any = field(default=None, repr=False, compare=False)
    _data: Any = field(default=None, repr=False, compare=False)
    # Live R control list this fit used (``None`` ⇒ R defaults); reused by the
    # refit-based S3 methods so they reproduce this exact model.
    _r_control: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        # strict=False deliberately: a repr must never raise, even on a fit whose
        # names and values somehow came back out of step.
        cf = ", ".join(
            f"{n}={v:.4g}"
            for n, v in zip(self.coef_names, self.coefficients, strict=False)
        )
        return (
            f"<LmrobMResult: {self.formula} | {cf} | "
            f"scale={self.scale:.4g}, R²={self.r_squared:.3f}, iter={self.iter}>"
        )

    def coef(self) -> pd.Series:
        """Return coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    # ----- S3 method ports (per project_memory/decisions.md D-012) -----
    # lmrobM's class is ``c("lmrobM", "lmrobdetMM")`` - does NOT inherit
    # from ``lmrob``, so robustbase's ``predict.lmrob`` / ``hatvalues.lmrob``
    # refuse to dispatch. RobStatTM ships no replacements either.
    #
    # Workaround (preserves strict-tier bit-equality): we compute predict
    # and hatvalues from the underlying R primitives - ``model.matrix() %*%
    # coef`` and ``diag(Q Q')`` of ``qr(sqrt(rweights) * X)`` respectively.
    # Both verified ``identical()`` on lmrobdetMM fits where R does
    # provide the S3 dispatch.

    def summary(self) -> LmrobdetMMSummary:
        """Port of R's ``summary.lmrobdetMM`` (lmrobM dispatches there)."""
        return summary_of(
            self.formula, self._data, self.coef_names, "lmrobM",
            r_control=self._r_control,
        )

    def predict(self, newdata: pd.DataFrame | None = None) -> np.ndarray:
        """Predictions on ``data`` (or ``newdata`` if given).

        Computed via ``model.matrix(formula, data) %*% coef(fit)`` because
        R's ``predict.lmrob`` does not dispatch to the lmrobM class
        hierarchy. Bit-for-bit identical to ``predict.lmrob`` on the MM
        family (verified).

        Note: ``se.fit`` is not supported, the lmrobM fit does not carry
        the qr decomposition needed for prediction standard errors.
        """
        return predict_manual(
            self.formula, self._data, "lmrobM", newdata, r_control=self._r_control,
        )

    def hatvalues(self) -> np.ndarray:
        """Hat-matrix diagonal computed via QR of ``sqrt(rweights) * X``.

        Bit-for-bit identical to ``hatvalues.lmrob`` on the MM family
        (verified). Provided here as a manual computation because R's
        ``hatvalues.lmrob`` does not dispatch to the lmrobM class
        hierarchy.
        """
        return hatvalues_manual(
            self.formula, self._data, "lmrobM", r_control=self._r_control,
        )


def lmrob_m(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
    control: LmrobMControl | None = None,
    bb: float | None = None,
    family: Literal["opt", "mopt", "bisquare", "huber", "moptv0", "optv0"] | None = None,
    efficiency: float | None = None,
    max_it: int | None = None,
) -> LmrobMResult:
    """Robust M-estimator regression (no high-breakdown S initialisation).

    Wraps ``RobStatTM::lmrobM``.

    Parameters
    ----------
    formula : str
        R-style ``"y ~ x1 + x2"``.
    data : pandas.DataFrame
    control : LmrobMControl, optional
        Full tuning object (see :func:`robstattm_py.lmrobm_control`). When
        given, takes precedence over the headline kwargs below.
    bb, family, efficiency, max_it
        Shortcuts for the most common single-knob overrides. Ignored if
        ``control`` is provided.

    Returns
    -------
    LmrobMResult

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> df = rpm.datasets.mineral()
    >>> fit = rpm.lmrob_m("zinc ~ copper", data=df)
    >>> # or with a control object:
    >>> ctrl = rpm.lmrobm_control(efficiency=0.95, family="bisquare")
    >>> fit2 = rpm.lmrob_m("zinc ~ copper", data=df, control=ctrl)
    """
    from robstattm_py.regression._formula import resolve_formula_args
    formula, data = resolve_formula_args(formula, data, X=X, y=y)

    ro = r()
    pkg = r_pkg("RobStatTM")
    push_df_to_r(data, var_name="rpm_data")
    rformula = ro.Formula(formula)

    # Resolve the control:
    #   1. explicit control= -> use as-is
    #   2. otherwise build from individual kwargs (headline knobs)
    #   3. else pass nothing (R defaults)
    if control is not None:
        if not isinstance(control, LmrobMControl):
            raise TypeError(
                f"control must be an LmrobMControl; got {type(control).__name__}"
            )
        if any(v is not None for v in (bb, family, efficiency, max_it)):
            raise TypeError(
                "Cannot mix `control=...` with individual knobs "
                "(bb/family/efficiency/max_it). Set them on the control "
                "object instead, or drop the `control=` kwarg."
            )
        r_control = _control_m_to_r(control)
    else:
        ctrl_overrides: dict = {}
        if bb is not None:
            ctrl_overrides["bb"] = float(bb)
        if efficiency is not None:
            ctrl_overrides["efficiency"] = float(efficiency)
        if family is not None:
            ctrl_overrides["family"] = family
        if max_it is not None:
            ctrl_overrides["max.it"] = int(max_it)
        r_control = (
            rcall(pkg.lmrobM_control, **ctrl_overrides) if ctrl_overrides else None
        )

    try:
        if r_control is not None:
            rfit = rcall(
                pkg.lmrobM, rformula,
                data=ro.globalenv["rpm_data"], control=r_control,
            )
        else:
            rfit = rcall(
                pkg.lmrobM, rformula,
                data=ro.globalenv["rpm_data"],
            )
        # Capture names while data is still in globalenv (dot formulas
        # need data context to expand).
        coef_names = coef_names_for(formula)
    finally:
        cleanup_r_var("rpm_data")

    return LmrobMResult(
        coefficients=extract_array(rx2(rfit, "coefficients")).astype(float).ravel(),
        coef_names=coef_names,
        scale=extract_float(rx2(rfit, "scale")),
        residuals=extract_array(rx2(rfit, "residuals")).astype(float).ravel(),
        loss=extract_float(rx2(rfit, "loss")),
        converged=extract_bool(rx2(rfit, "converged")),
        iter=extract_int(rx2(rfit, "iter")),
        fitted_values=extract_array(rx2(rfit, "fitted.values")).astype(float).ravel(),
        rweights=extract_array(rx2(rfit, "rweights")).astype(float).ravel(),
        rank=extract_int(rx2(rfit, "rank")),
        cov=np.asarray(rx2(rfit, "cov"), dtype=float),
        df_residual=extract_int(rx2(rfit, "df.residual")),
        degree_freedom=extract_int(rx2(rfit, "degree.freedom")),
        r_squared=extract_float(rx2(rfit, "r.squared")),
        formula=formula,
        _r_fit=rfit,
        # Defensive copy - see LmrobdetMMResult: the refit-based S3 methods
        # read this frame back, so snapshot it against later caller mutation.
        _data=data.copy(),
        _r_control=r_control,
    )
