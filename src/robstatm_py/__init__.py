"""RobStatTM-Py — Python wrappers for the RobStatTM R package.

Public flat re-exports (see docs/user_interface.md §2.1). Submodule access is
also supported: ``from robstatm_py.univariate import loc_scale_m``.

Importing this module is cheap — R is not started until the first wrapper call
(see ``_r.py`` for the lazy ``importr`` pattern, and ``decisions.md`` D-009).
"""
from __future__ import annotations

__version__ = "0.0.1.dev0"

from robstatm_py._errors import (
    RobStatTMError,
    RobStatTMRError,
    RobStatTMSetupError,
)
from robstatm_py.utils.check_setup import check_setup
from robstatm_py.utils.seeds import set_seed
from robstatm_py._help import help, list_names
from robstatm_py._r import r_started
from robstatm_py.bench import set_n_jobs, timer as _bench_timer  # noqa: F401

# Univariate
from robstatm_py.univariate.loc_scale_m import LocScaleMResult, loc_scale_m
from robstatm_py.univariate.m_scale import m_scale
from robstatm_py.regression.control import LmrobdetControl, lmrobdet_control
from robstatm_py.regression.control_m import LmrobMControl, lmrobm_control
from robstatm_py.regression.refine_sm import RefineSMResult, refine_sm
from robstatm_py.regression.lmrobdet_mm import (
    LmrobdetMMPrediction,
    LmrobdetMMResult,
    LmrobdetMMSummary,
    drop1_lmrobdet,
    lmrobdet_mm,
)
from robstatm_py.regression._s3_methods import Drop1Result
from robstatm_py.regression.lmrobdet_dcml import LmrobdetDCMLResult, lmrobdet_dcml
from robstatm_py.regression.lmrob_m import LmrobMResult, lmrob_m
from robstatm_py.regression.pyinit import PyinitResult, pyinit
from robstatm_py.regression.step import StepResult, step_lmrobdet
from robstatm_py.regression.linear_test import RobLinearTestResult, rob_linear_test
from robstatm_py.regression.inv_tr2 import invtr2
from robstatm_py.covariance.cov_classic import CovClassicResult, cov_classic
from robstatm_py.covariance.cov_rob_mm import CovRobMMResult, cov_rob_mm
from robstatm_py.covariance.cov_rob_rocke import CovRobRockeResult, cov_rob_rocke
from robstatm_py.covariance.cov_rob import CovRobResult, cov_rob
from robstatm_py.covariance.kurt_sd_new import KurtSDResult, kurt_sd_new
from robstatm_py.covariance.fastmve import FastMVEResult, fastmve
from robstatm_py.pca.pca_rob_s import PcaRobSResult, pca_rob_s
from robstatm_py.pca.prcomp_rob import PrcompRobResult, prcomp_rob
from robstatm_py.glm.logreg import LogregResult, by_logreg, wby_logreg, wml_logreg
from robstatm_py.external.pense import (
    PenseCVResult,
    PenseResult,
    pense,
    pense_cv,
)
from robstatm_py.external.gse import GSEResult, TSGSResult, gse, tsgs
from robstatm_py import datasets, plotting, psi, bench, external

# Attach to_dict / to_r / _repr_html_ / coef_df to every result dataclass
# (see docs/user_interface.md §6 and src/robstatm_py/_result_mixins.py).
from robstatm_py._result_mixins import install_result_mixins as _install_mixins

_install_mixins()
del _install_mixins

__all__ = [
    "__version__",
    # errors
    "RobStatTMError",
    "RobStatTMRError",
    "RobStatTMSetupError",
    # utilities
    "check_setup",
    "set_seed",
    "help",
    "list_names",
    "r_started",
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
    # submodules
    "datasets",
    "plotting",
    "psi",
    "external",
]
