"""RobStatTM-Py, Python wrappers for the RobStatTM R package.

Public flat re-exports (see dev/design/user_interface.md §2.1). Submodule access is
also supported: ``from robstattm_py.univariate import loc_scale_m``.

Importing this module is cheap, R is not started until the first wrapper call
(see ``_r.py`` for the lazy ``importr`` pattern, and ``decisions.md`` D-009).
"""
from __future__ import annotations

def _detect_version() -> str:
    """Return the installed distribution's version.

    Read from installed metadata rather than hardcoded here, so the number can
    never drift from what pip actually installed, a discrepancy that makes bug
    reports impossible to interpret. The fallback covers running from a source
    checkout that was never installed.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("robstattm-py")
    except PackageNotFoundError:  # pragma: no cover - uninstalled checkout
        return "0.0.0+unknown"


__version__ = _detect_version()

from robstattm_py._errors import (
    RobStatTMError,
    RobStatTMRError,
    RobStatTMSetupError,
    RobStatTMWarning,
)
from robstattm_py.utils.check_setup import check_setup
from robstattm_py.utils.seeds import set_seed
from robstattm_py._help import help, list_names
from robstattm_py._r import capture_r_warnings, last_r_warnings, r_started
from robstattm_py.bench import set_n_jobs, timer as _bench_timer  # noqa: F401

# Univariate
from robstattm_py.univariate.loc_scale_m import LocScaleMResult, loc_scale_m
from robstattm_py.univariate.m_scale import m_scale
from robstattm_py.regression.control import LmrobdetControl, lmrobdet_control
from robstattm_py.regression.control_m import LmrobMControl, lmrobm_control
from robstattm_py.regression.refine_sm import RefineSMResult, refine_sm
from robstattm_py.regression.lmrobdet_mm import (
    LmrobdetMMPrediction,
    LmrobdetMMResult,
    LmrobdetMMSummary,
    drop1_lmrobdet,
    lmrobdet_mm,
)
from robstattm_py.regression._s3_methods import Drop1Result
from robstattm_py.regression.lmrobdet_dcml import LmrobdetDCMLResult, lmrobdet_dcml
from robstattm_py.regression.lmrob_m import LmrobMResult, lmrob_m
from robstattm_py.regression.pyinit import PyinitResult, pyinit
from robstattm_py.regression.step import StepResult, step_lmrobdet
from robstattm_py.regression.linear_test import RobLinearTestResult, rob_linear_test
from robstattm_py.regression.inv_tr2 import invtr2
from robstattm_py.covariance.cov_classic import CovClassicResult, cov_classic
from robstattm_py.covariance.cov_rob_mm import CovRobMMResult, cov_rob_mm
from robstattm_py.covariance.cov_rob_rocke import CovRobRockeResult, cov_rob_rocke
from robstattm_py.covariance.cov_rob import CovRobResult, cov_rob
from robstattm_py.covariance.kurt_sd_new import KurtSDResult, kurt_sd_new
from robstattm_py.covariance.fastmve import FastMVEResult, fastmve
from robstattm_py.pca.pca_rob_s import PcaRobSResult, pca_rob_s
from robstattm_py.pca.prcomp_rob import PrcompRobResult, prcomp_rob
from robstattm_py.glm.logreg import LogregResult, by_logreg, wby_logreg, wml_logreg
from robstattm_py.external.pense import (
    PenseCVResult,
    PenseResult,
    pense,
    pense_cv,
)
from robstattm_py.external.gse import GSEResult, TSGSResult, gse, tsgs
from robstattm_py.external.arima_rob import ArimaRobResult, arima_rob
from robstattm_py.external.var_comprob import (
    VarComprobControl,
    VarComprobResult,
    var_comprob,
    var_comprob_control,
)
from robstattm_py.external.glmrob import GlmrobResult, glmrob
from robstattm_py.external.cubinf import CubinfResult, cubinf
from robstattm_py import datasets, plot, plotting, psi, bench, external

# Attach to_dict / to_r / _repr_html_ / coef_df to every result dataclass
# (see dev/design/user_interface.md §6 and src/robstattm_py/_result_mixins.py).
from robstattm_py._result_mixins import install_result_mixins as _install_mixins

_install_mixins()
del _install_mixins

__all__ = [
    "__version__",
    # errors
    "RobStatTMError",
    "RobStatTMRError",
    "RobStatTMSetupError",
    "RobStatTMWarning",
    # utilities
    "check_setup",
    "set_seed",
    "help",
    "list_names",
    "r_started",
    "capture_r_warnings",
    "last_r_warnings",
    "set_n_jobs",
    "bench",
    # univariate wrappers
    "loc_scale_m",
    "LocScaleMResult",
    "m_scale",
    # regression
    "LmrobdetControl",
    "lmrobdet_control",
    "LmrobMControl",
    "lmrobm_control",
    "RefineSMResult",
    "refine_sm",
    "LmrobdetMMResult",
    "LmrobdetMMSummary",
    "LmrobdetMMPrediction",
    "lmrobdet_mm",
    "Drop1Result",
    "drop1_lmrobdet",
    "LmrobdetDCMLResult",
    "lmrobdet_dcml",
    "LmrobMResult",
    "lmrob_m",
    "PyinitResult",
    "pyinit",
    "StepResult",
    "step_lmrobdet",
    "RobLinearTestResult",
    "rob_linear_test",
    "invtr2",
    # covariance
    "CovClassicResult",
    "cov_classic",
    "CovRobMMResult",
    "cov_rob_mm",
    "CovRobRockeResult",
    "cov_rob_rocke",
    "CovRobResult",
    "cov_rob",
    "KurtSDResult",
    "kurt_sd_new",
    "FastMVEResult",
    "fastmve",
    # pca
    "PcaRobSResult",
    "pca_rob_s",
    "PrcompRobResult",
    "prcomp_rob",
    # glm
    "LogregResult",
    "by_logreg",
    "wby_logreg",
    "wml_logreg",
    # external (stretch: pense / GSE / TSGS)
    "PenseResult",
    "PenseCVResult",
    "pense",
    "pense_cv",
    "GSEResult",
    "gse",
    "TSGSResult",
    "tsgs",
    "ArimaRobResult",
    "arima_rob",
    "VarComprobControl",
    "VarComprobResult",
    "var_comprob",
    "var_comprob_control",
    "GlmrobResult",
    "glmrob",
    "CubinfResult",
    "cubinf",
    # submodules
    "datasets",
    "plot",
    "plotting",
    "psi",
    "external",
]
