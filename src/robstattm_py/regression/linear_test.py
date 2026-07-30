"""Robust likelihood-ratio test for nested MM fits.

Wraps ``RobStatTM::rob.linear.test``. Maronna et al. (2019) §4.7.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from robstattm_py._r import r, r_pkg
from robstattm_py.regression.lmrobdet_mm import LmrobdetMMResult
from robstattm_py.regression._formula import df_with_r_names


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
    object1: LmrobdetMMResult,
    object2: LmrobdetMMResult,
) -> RobLinearTestResult:
    """Robust likelihood-ratio-style test for nested MM fits.

    Wraps ``RobStatTM::rob.linear.test``. Compares ``object1`` (full) against
    ``object2`` (reduced). Both fits must have been built via
    :func:`lmrobdet_mm` so their original data is available for the R-side
    re-fit.
    """
    if not (isinstance(object1, LmrobdetMMResult) and isinstance(object2, LmrobdetMMResult)):
        raise TypeError("both objects must be LmrobdetMMResult")
    if object1._data is None or object2._data is None:
        raise ValueError("both fits must have their original DataFrame attached")

    ro = r()
    _ = r_pkg("RobStatTM")
    ro.globalenv["rpm_rlt_data1"] = df_with_r_names(object1._data)
    ro.globalenv["rpm_rlt_data2"] = df_with_r_names(object2._data)
    f1_str = object1.formula
    f2_str = object2.formula
    # Rebuild each fit with its *own* control (the converted _r_fit lost its S3
    # class), so the test compares the user's actual models — not default ones.
    cleanup_vars = [
        "rpm_rlt_data1", "rpm_rlt_data2",
        "rpm_rlt_o1", "rpm_rlt_o2", "rpm_rlt_result",
    ]
    if object1._r_control is not None:
        ro.globalenv["rpm_rlt_ctrl1"] = object1._r_control
        cleanup_vars.append("rpm_rlt_ctrl1")
        o1_cmd = f"rpm_rlt_o1 <- lmrobdetMM({f1_str}, data=rpm_rlt_data1, control=rpm_rlt_ctrl1); "
    else:
        o1_cmd = f"rpm_rlt_o1 <- lmrobdetMM({f1_str}, data=rpm_rlt_data1); "
    if object2._r_control is not None:
        ro.globalenv["rpm_rlt_ctrl2"] = object2._r_control
        cleanup_vars.append("rpm_rlt_ctrl2")
        o2_cmd = f"rpm_rlt_o2 <- lmrobdetMM({f2_str}, data=rpm_rlt_data2, control=rpm_rlt_ctrl2); "
    else:
        o2_cmd = f"rpm_rlt_o2 <- lmrobdetMM({f2_str}, data=rpm_rlt_data2); "
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
