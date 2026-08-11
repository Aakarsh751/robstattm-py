"""Distance-Constrained MLE robust regression.

Wraps ``RobStatTM::lmrobdetDCML``. Maronna et al. (2019) §5.9. Boosts
efficiency over plain MM while preserving the MM breakdown point. Depends on
``pyinit`` and ``robustbase``.

R return list (RobStatTM 1.0.11):
  coefficients, cov, residuals, fitted.values, scale, t0, rank, converged,
  qr, df.residual, iter, rweightsMM, model, x, xlevels, call, terms, assign.

Public Python fields (numeric subset):
  coefficients, coef_names, cov, residuals, fitted_values, scale, t0, rank,
  converged, df_residual, iter, rweights_mm, formula, control.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as _replace
from typing import Any

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
    LmrobdetMMPrediction,
    LmrobdetMMSummary,
    hatvalues_of,
    predict_of,
    r_squared_classic,
    summary_of,
)
from robstattm_py.regression.control import LmrobdetControl, _control_to_r


@dataclass(frozen=True, slots=True)
class LmrobdetDCMLResult:
    """DCML regression result.

    Attributes mirror the R return list 1:1 (numeric subset). See module
    docstring for the full list.
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    cov: np.ndarray
    residuals: np.ndarray
    fitted_values: np.ndarray
    scale: float
    t0: float
    rank: int
    converged: bool
    df_residual: int
    iter: int
    rweights_mm: np.ndarray
    formula: str
    control: LmrobdetControl
    _r_fit: Any = field(default=None, repr=False, compare=False)
    _data: Any = field(default=None, repr=False, compare=False)
    # Live R control list this fit used (``None`` ⇒ R defaults); reused by the
    # refit-based S3 methods so they reproduce this exact model. See
    # ``LmrobdetMMResult._r_control``.
    _r_control: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        cf = ", ".join(
            f"{n}={v:.4g}"
            for n, v in zip(self.coef_names, self.coefficients, strict=False)
        )
        return (
            f"<LmrobdetDCMLResult: {self.formula} | {cf} | "
            f"scale={self.scale:.4g}, t0={self.t0:.4g}, iter={self.iter}>"
        )

    def coef(self) -> pd.Series:
        """Return coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    # ----- S3 method ports (per project_memory/decisions.md D-012) -----
    # lmrobdetDCML's summary dispatches to ``summary.lmrobdetMM`` (verified).

    def summary(self) -> LmrobdetMMSummary:
        """Port of R's ``summary.lmrobdetMM`` (DCML dispatches there)."""
        return summary_of(
            self.formula, self._data, self.coef_names, "lmrobdetDCML",
            r_control=self._r_control,
        )

    def predict(
        self,
        newdata: pd.DataFrame | None = None,
        *,
        se_fit: bool = False,
    ) -> np.ndarray | LmrobdetMMPrediction:
        """Port of R's ``predict.lmrob`` on an ``lmrobdetDCML`` fit."""
        return predict_of(
            self.formula, self._data, "lmrobdetDCML", newdata, se_fit=se_fit,
            r_control=self._r_control,
        )

    def hatvalues(self) -> np.ndarray:
        """Port of R's ``hatvalues.lmrob`` on an ``lmrobdetDCML`` fit."""
        return hatvalues_of(self.formula, self._data, "lmrobdetDCML", r_control=self._r_control)

    def r_squared_classic(self) -> float:
        """Classical (least-squares) R² for the DCML fit.

        R's ``lmrobdetDCML`` does NOT populate ``$r.squared`` on the fit
        (verified — the DCML algorithm has no canonical robust-R²
        statistic). Therefore ``self.summary().r_squared`` is ``None``
        for DCML fits, matching R.

        This method returns the **classical** statistic
        ``1 - sum(residuals^2) / sum((y - mean(y))^2)``. It is *not* the
        robust R² that ``lmrobdetMM`` reports. Use only when the
        classical interpretation is what you want.

        Examples
        --------
        >>> import robstattm_py as rpm
        >>> df = rpm.datasets.mineral()
        >>> fit = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        >>> assert fit.summary().r_squared is None    # R parity
        >>> r2 = fit.r_squared_classic()              # classical fallback
        """
        return r_squared_classic(
            self.formula, self._data, "lmrobdetDCML", r_control=self._r_control,
        )


def lmrobdet_dcml(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
    control: LmrobdetControl | None = None,
    family: str | None = None,
    efficiency: float | None = None,
) -> LmrobdetDCMLResult:
    """Distance-Constrained MLE robust regression.

    Wraps ``RobStatTM::lmrobdetDCML``. Same interface as :func:`lmrobdet_mm`,
    including the ``(X, y)`` array form (see UI doc §3).
    """
    from robstattm_py.regression._formula import resolve_formula_args
    formula, data = resolve_formula_args(formula, data, X=X, y=y)
    # Below is the original validation kept as defensive paranoia:
    if not isinstance(formula, str):
        raise TypeError(f"formula must be a str; got {type(formula).__name__}")
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"data must be a pandas.DataFrame; got {type(data).__name__}")
    if data.empty:
        raise ValueError("data is empty")

    base = control or LmrobdetControl()
    overrides: dict = {}
    if family is not None:
        overrides["family"] = family
    if efficiency is not None:
        overrides["efficiency"] = efficiency
    if overrides:
        base = _replace(base, **overrides)

    ro = r()
    pkg = r_pkg("RobStatTM")
    push_df_to_r(data, var_name="rpm_data")
    rformula = ro.Formula(formula)

    is_default = base == LmrobdetControl()
    # Build the R control list once (when non-default) so the same object backs
    # both this fit and the refit-based S3 methods later.
    r_control = None if is_default else _control_to_r(base)
    try:
        if r_control is None:
            # Let R fill defaults — building a partial control list and
            # passing it has triggered "non-conformable arrays" in DCML.
            rfit = rcall(
                pkg.lmrobdetDCML, rformula,
                data=ro.globalenv["rpm_data"],
                _hint="check data dtypes / column names match the formula",
            )
        else:
            rfit = rcall(
                pkg.lmrobdetDCML, rformula,
                data=ro.globalenv["rpm_data"], control=r_control,
                _hint="check data dtypes / column names match the formula",
            )
        coef_names = coef_names_for(formula)
    finally:
        cleanup_r_var("rpm_data")

    return LmrobdetDCMLResult(
        coefficients=extract_array(rx2(rfit, "coefficients")).astype(float).ravel(),
        coef_names=coef_names,
        cov=np.asarray(rx2(rfit, "cov"), dtype=float),
        residuals=extract_array(rx2(rfit, "residuals")).astype(float).ravel(),
        fitted_values=extract_array(rx2(rfit, "fitted.values")).astype(float).ravel(),
        scale=extract_float(rx2(rfit, "scale")),
        t0=extract_float(rx2(rfit, "t0")),
        rank=extract_int(rx2(rfit, "rank")),
        converged=extract_bool(rx2(rfit, "converged")),
        df_residual=extract_int(rx2(rfit, "df.residual")),
        iter=extract_int(rx2(rfit, "iter")),
        rweights_mm=extract_array(rx2(rfit, "rweightsMM")).astype(float).ravel(),
        formula=formula,
        control=base,
        _r_fit=rfit,
        # Defensive copy — see LmrobdetMMResult: the refit-based S3 methods
        # read this frame back, so snapshot it against later caller mutation.
        _data=data.copy(),
        _r_control=r_control,
    )
