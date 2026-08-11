"""Robust likelihood-ratio test for nested MM fits.

Wraps ``RobStatTM::rob.linear.test``. Maronna et al. (2019) §4.7.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from robstattm_py._r import r, r_pkg
from robstattm_py.regression._formula import df_with_r_names
from robstattm_py.regression.lmrob_m import LmrobMResult
from robstattm_py.regression.lmrobdet_mm import LmrobdetMMResult

#: R fitter to replay each result type with. ``rob.linear.test`` accepts both
#: (``R/lmrobdet.R``: ``'lmrobdetMM' %in% class(.) | 'lmrobM' %in% class(.)``),
#: and the R help page's own example for it uses ``lmrobM`` — as does the book's
#: Example 4.2. Refitting an M fit as MM would silently test a different pair of
#: models, so the mapping is on the result class rather than assumed.
_R_FITTER = {
    LmrobdetMMResult: "lmrobdetMM",
    LmrobMResult: "lmrobM",
}


@dataclass(frozen=True, slots=True)
class RobLinearTestResult:
    """Robust LR-style test result.

    Attributes
    ----------
    test : float
        Test statistic.
    chisq_pvalue : float
        χ² approximation p-value.
    f_pvalue : float
        F approximation p-value.
    df : tuple[int, int]
        (numerator, denominator) degrees of freedom.
    """

    test: float
    chisq_pvalue: float
    f_pvalue: float
    df: tuple[int, int]
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<RobLinearTestResult: stat={self.test:.4g} "
            f"chisq_p={self.chisq_pvalue:.4f} F_p={self.f_pvalue:.4f} df={self.df}>"
        )


def rob_linear_test(
    object1: LmrobdetMMResult | LmrobMResult,
    object2: LmrobdetMMResult | LmrobMResult,
) -> RobLinearTestResult:
    """Robust likelihood-ratio-style test for nested M or MM fits.

    Wraps ``RobStatTM::rob.linear.test``. Compares ``object1`` (full) against
    ``object2`` (reduced). Both fits must have been built via
    :func:`lmrobdet_mm` or :func:`lmrob_m` from a DataFrame, so their original
    data is available for the R-side re-fit.

    R requires both fits to share a rho family and tuning constant, and raises
    if they do not; that check is left to R rather than duplicated here.
    """
    for name, obj in (("object1", object1), ("object2", object2)):
        if type(obj) not in _R_FITTER:
            raise TypeError(
                f"{name} must be an lmrobdet_mm or lmrob_m result; "
                f"got {type(obj).__name__}"
            )
    if object1._data is None or object2._data is None:
        raise ValueError("both fits must have their original DataFrame attached")

    ro = r()
    _ = r_pkg("RobStatTM")
    ro.globalenv["rpm_rlt_data1"] = df_with_r_names(object1._data)
    ro.globalenv["rpm_rlt_data2"] = df_with_r_names(object2._data)
    # Rebuild each fit with its *own* fitter and control (the converted _r_fit
    # lost its S3 class), so the test compares the user's actual models.
    cleanup_vars = [
        "rpm_rlt_data1", "rpm_rlt_data2",
        "rpm_rlt_o1", "rpm_rlt_o2", "rpm_rlt_result",
    ]

    def _refit_cmd(obj, slot: str) -> str:
        fitter = _R_FITTER[type(obj)]
        if obj._r_control is None:
            return f"rpm_rlt_o{slot} <- {fitter}({obj.formula}, data=rpm_rlt_data{slot}); "
        ctrl = f"rpm_rlt_ctrl{slot}"
        ro.globalenv[ctrl] = obj._r_control
        cleanup_vars.append(ctrl)
        return (
            f"rpm_rlt_o{slot} <- {fitter}({obj.formula}, "
            f"data=rpm_rlt_data{slot}, control={ctrl}); "
        )

    o1_cmd = _refit_cmd(object1, "1")
    o2_cmd = _refit_cmd(object2, "2")
    try:
        ro.r(
            o1_cmd + o2_cmd
            + "rpm_rlt_result <- rob.linear.test(rpm_rlt_o1, rpm_rlt_o2)"
        )
        test = float(ro.r("rpm_rlt_result$test")[0])
        cp = float(ro.r("rpm_rlt_result$chisq.pvalue")[0])
        fp = float(ro.r("rpm_rlt_result$F.pvalue")[0])
        df_arr = ro.r("as.integer(rpm_rlt_result$df)")
        df = (int(df_arr[0]), int(df_arr[1]))
        rfit = ro.r("rpm_rlt_result")
    finally:
        ro.r(
            "for (v in c("
            + ",".join(f"'{v}'" for v in cleanup_vars)
            + ")) if (exists(v)) rm(list=v)"
        )

    return RobLinearTestResult(
        test=test,
        chisq_pvalue=cp,
        f_pvalue=fp,
        df=df,
        _r_fit=rfit,
    )
