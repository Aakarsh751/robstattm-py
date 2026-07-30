"""Wrappers for robust estimators that live in *external* CRAN packages.

These are the proposal's stretch goals (Maronna et al. 2019 reference them
alongside RobStatTM, but they ship in separate packages):

* ``pense``       → robust elastic-net S/MM estimator (package ``pense``)
* ``gse``         → Generalized S-Estimator for missing data (package ``GSE``)
* ``tsgs``        → Two-Step GSE for cell-wise outliers (package ``GSE``)
* ``arima_rob``   → robust ARIMA / filtered-tau (package ``robustarima``)
* ``var_comprob`` → robust variance-component models (package ``robustvarComp``)
* ``glmrob``      → robust GLM (package ``robustbase``)
* ``cubinf``      → CUBIF bounded-influence GLM (package ``robcbi``)

Same rpy2 pattern as the core wrappers: we wrap only the named entry-point
functions, not the whole packages. The R packages must be installed by the
user (``install.packages(c("pense", "GSE", "robustarima", "robustvarComp",
"robcbi"))``); ``robstattm_py.check_setup()`` reports whether they are available.
"""
from robstattm_py.external.pense import (
    PenseCVResult,
    PenseResult,
    pense,
    pense_cv,
)
from robstattm_py.external.gse import (
    GSEResult,
    TSGSResult,
    gse,
    tsgs,
)
from robstattm_py.external.arima_rob import ArimaRobResult, arima_rob
from robstattm_py.external.var_comprob import (
    VarComprobControl,
    VarComprobResult,
    var_comprob,
    var_comprob_control,
)
from robstattm_py.external.glmrob import GlmrobResult, glmrob
from robstattm_py.external.cubinf import CubinfResult, cubinf

__all__ = [
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
]
