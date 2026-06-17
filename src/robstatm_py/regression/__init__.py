"""Robust regression wrappers (MM, DCML, M, stepwise, linear-hypothesis test)."""
from robstatm_py.regression.control import LmrobdetControl, lmrobdet_control
from robstatm_py.regression.control_m import LmrobMControl, lmrobm_control
from robstatm_py.regression.lmrobdet_mm import (
    LmrobdetMMResult,
    drop1_lmrobdet,
    lmrobdet_mm,
)
from robstatm_py.regression.lmrobdet_dcml import LmrobdetDCMLResult, lmrobdet_dcml
from robstatm_py.regression.lmrob_m import LmrobMResult, lmrob_m
from robstatm_py.regression.pyinit import PyinitResult, pyinit
from robstatm_py.regression.refine_sm import RefineSMResult, refine_sm
from robstatm_py.regression.step import StepResult, step_lmrobdet
from robstatm_py.regression.linear_test import RobLinearTestResult, rob_linear_test
from robstatm_py.regression.inv_tr2 import invtr2
from robstatm_py.regression._s3_methods import (
    Drop1Result,
    LmrobdetMMPrediction,
    LmrobdetMMSummary,
)

__all__ = [
    "LmrobdetControl",
    "lmrobdet_control",
    "LmrobMControl",
    "lmrobm_control",
    "LmrobdetMMResult",
    "LmrobdetMMSummary",
    "LmrobdetMMPrediction",
    "lmrobdet_mm",
    "drop1_lmrobdet",
    "Drop1Result",
    "LmrobdetDCMLResult",
    "lmrobdet_dcml",
    "LmrobMResult",
    "lmrob_m",
    "PyinitResult",
    "pyinit",
    "RefineSMResult",
    "refine_sm",
    "StepResult",
    "step_lmrobdet",
    "RobLinearTestResult",
    "rob_linear_test",
    "invtr2",
]
