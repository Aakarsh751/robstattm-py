"""Comparison models: non-RobStatTM fits you can line up against the robust ones.

Everything here wraps a model from another R package -- ``stats`` (``lm``,
``glm``), ``MASS`` (``rlm``), ``robustbase`` (``lmrob``, ``ltsReg``) -- so you can
see how a RobStatTM robust fit differs from a classical or alternative-robust
one. This is the set behind Doug Martin's ``methods("summary")`` list
(``summary.lm``, ``summary.lmrob``, ``summary.lts``) plus the classical ``glm``
baseline for the robust logistic regressions.

Each returns a native Python result (frozen dataclass, numpy/pandas fields,
``.summary()`` porting R's ``summary.*``), so you can read every number without
touching rpy2. For R's ``fit.models`` side-by-side view, use
:func:`~robstattm_py.compare`.

``cov_classic`` is a genuine RobStatTM function and lives in
``robstattm_py.covariance``; it is re-exported here so the comparison surface is
complete in one place (compare it against ``cov_rob``).
"""
from robstattm_py.comparison._common import (
    ComparisonPrediction,
    ComparisonSummary,
)
from robstattm_py.comparison.compare import Comparison, compare
from robstattm_py.comparison.glm import GlmResult, glm
from robstattm_py.comparison.lm import LmResult, lm
from robstattm_py.comparison.lmrob import LmrobResult, lmrob
from robstattm_py.comparison.lts import LtsResult, lts_reg
from robstattm_py.comparison.rlm import RlmResult, rlm
from robstattm_py.covariance.cov_classic import CovClassicResult, cov_classic

__all__ = [
    "ComparisonSummary",
    "ComparisonPrediction",
    "LmResult",
    "lm",
    "GlmResult",
    "glm",
    "RlmResult",
    "rlm",
    "LtsResult",
    "lts_reg",
    "LmrobResult",
    "lmrob",
    "Comparison",
    "compare",
    # re-exported RobStatTM classical covariance, for the cov comparison
    "CovClassicResult",
    "cov_classic",
]
