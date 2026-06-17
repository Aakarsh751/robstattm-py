"""Wrappers for robust estimators that live in *external* CRAN packages.

These are the proposal's stretch goals (Maronna et al. 2019 reference them
alongside RobStatTM, but they ship in separate packages):

* ``pense``  → robust elastic-net S/MM estimator (package ``pense``)
* ``gse``    → Generalized S-Estimator for missing data (package ``GSE``)
* ``tsgs``   → Two-Step GSE for cell-wise outliers (package ``GSE``)

Same rpy2 pattern as the core wrappers: we wrap only the named entry-point
functions, not the whole packages. The R packages must be installed by the
user (``install.packages(c("pense", "GSE"))``); ``robstatm_py.check_setup()``
reports whether they are available.
"""
from robstatm_py.external.pense import (
    PenseCVResult,
    PenseResult,
    pense,
    pense_cv,
)
from robstatm_py.external.gse import (
    GSEResult,
    TSGSResult,
    gse,
    tsgs,
)

__all__ = [
    "PenseResult",
    "PenseCVResult",
    "pense",
    "pense_cv",
    "GSEResult",
    "gse",
    "TSGSResult",
    "tsgs",
]
