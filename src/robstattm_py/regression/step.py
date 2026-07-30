"""Robust stepwise model selection via RFPE.

Wraps ``RobStatTM::step.lmrobdetMM``. Maronna et al. (2019) §5.6.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from robstattm_py._r import r, r_pkg, rcall
from robstattm_py.regression.lmrobdet_mm import LmrobdetMMResult
from robstattm_py.regression._formula import df_with_r_names


@dataclass(frozen=True, slots=True)
class StepResult:
    """Stepwise selection result.

    Attributes
    ----------
    final_formula : str
        Formula of the selected model.
    anova_rfpe : np.ndarray
        RFPE trace across steps (column of the R ``anova`` table).
    coefficients : np.ndarray
        Coefficients of the selected fit.
    coef_names : tuple[str, ...]
    scale : float
        Robust scale of the selected fit.
    """

    final_formula: str
    anova_rfpe: np.ndarray
    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    scale: float
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<StepResult: final={self.final_formula} "
            f"steps={len(self.anova_rfpe)}>"
        )


def step_lmrobdet(
    fit: LmrobdetMMResult,
    *,
    direction: Literal["backward"] = "backward",
    trace: bool = False,
    steps: int = 1000,
) -> StepResult:
    """Robust stepwise model selection (RFPE).

    Wraps ``RobStatTM::step.lmrobdetMM``. Currently only "backward" direction
    is supported by the underlying R implementation.

    Parameters
    ----------
    fit : LmrobdetMMResult
        Starting MM fit. Must have been built from a DataFrame so the data is
        available for the R-side re-fit (``fit._data is not None``).
    direction : Literal["backward"], default "backward"
    trace : bool, default False
    steps : int, default 1000

    Returns
    -------
    StepResult
    """
    if not isinstance(fit, LmrobdetMMResult):
        raise TypeError("fit must be a LmrobdetMMResult")
    if fit._data is None:
        raise ValueError(
            "fit must have access to its original data; pass the DataFrame "
            "directly to lmrobdet_mm rather than reconstructing a fit"
        )

    ro = r()
    _ = r_pkg("RobStatTM")  # ensure attached
    # Re-fit and step in a single R script so model.frame is built correctly.
    # Reuse the input fit's *own* control (the converted _r_fit has no S3
    # class, so we must rebuild it) — otherwise the stepwise search would run
    # on a default-control model instead of the user's.
    ro.globalenv["rpm_step_data"] = df_with_r_names(fit._data)
    formula_str = fit.formula
    cleanup_vars = ["rpm_step_data", "rpm_step_input", "rpm_step_result"]
    if fit._r_control is not None:
        ro.globalenv["rpm_step_ctrl"] = fit._r_control
        cleanup_vars.append("rpm_step_ctrl")
        fit_cmd = (
            f"rpm_step_input <- lmrobdetMM({formula_str}, data=rpm_step_data, "
            f"control=rpm_step_ctrl); "
        )
    else:
        fit_cmd = f"rpm_step_input <- lmrobdetMM({formula_str}, data=rpm_step_data); "
    try:
        ro.r(
            fit_cmd
            + f"rpm_step_result <- step.lmrobdetMM(rpm_step_input, "
            f"direction='{direction}', "
            f"trace={'TRUE' if trace else 'FALSE'}, "
            f"steps={int(steps)})"
        )
        final_formula = str(
            ro.r("paste(deparse(rpm_step_result$call$formula), collapse=' ')")[0]
        )
        # Fallback: if the call doesn't have $formula, look at $formula field
        if "$" in final_formula or final_formula in {"NULL", ""}:
            final_formula = str(
                ro.r("paste(deparse(rpm_step_result$formula), collapse=' ')")[0]
            )
        rfpe = np.asarray(ro.r("rpm_step_result$anova$RFPE"), dtype=float)
        coef = np.asarray(ro.r("coef(rpm_step_result)"), dtype=float)
        coef_names_obj = ro.r("names(coef(rpm_step_result))")
        coef_names = tuple(str(n) for n in coef_names_obj) if coef_names_obj is not None else ()
        scale = float(ro.r("rpm_step_result$scale")[0])
        rfit_returned = ro.r("rpm_step_result")
    finally:
        ro.r(
            "for (v in c("
            + ",".join(f"'{v}'" for v in cleanup_vars)
            + ")) if (exists(v)) rm(list=v)"
        )

    return StepResult(
        final_formula=final_formula,
        anova_rfpe=rfpe,
        coefficients=coef,
        coef_names=coef_names,
        scale=scale,
        _r_fit=rfit_returned,
    )
