"""R-name compatibility layer.

Users transcribing code from the textbook may want to keep the original
R names. Importing from this module gives them every wrapper under both
its Python (snake_case) name AND its R-original name where the R name is
a legal Python identifier.

Per ``docs/user_interface.md §2.3``::

    from robstattm_py.compat_r import *
    fit = lmrobdetMM("zinc ~ copper", data=data)  # works
    # ↑ identical to robstattm_py.lmrobdet_mm

R names with dots are not Python-legal, so each gets an
underscore-replacement alias instead (e.g. ``lmrobdet.control`` →
``lmrobdet_control``, which is also the canonical Python name).

The full R↔Python map lives in ``docs/user_interface.md §5``.
"""
from __future__ import annotations

import robstattm_py as _rpm

# Univariate
locScaleM = _rpm.loc_scale_m
MLocDis = _rpm.loc_scale_m
scaleM = _rpm.m_scale
mscale = _rpm.m_scale

# Regression
lmrobM = _rpm.lmrob_m
lmrobdetMM = _rpm.lmrobdet_mm
lmrobdetDCML = _rpm.lmrobdet_dcml
pyinit = _rpm.pyinit
INVTR2 = _rpm.invtr2
# `step.lmrobdetMM` and `rob.linear.test` are not Python-legal, so the
# canonical Python name is the alias the user gets here too.
step_lmrobdetMM = _rpm.step_lmrobdet
rob_linear_test = _rpm.rob_linear_test
lsRobTestMM = _rpm.rob_linear_test
lmrobdetLinTest = _rpm.rob_linear_test
# `drop1.lmrobdetMM` is an S3 method in R; the Python equivalent is a function
# (and the .drop1() method on a fit). Expose the R-style name here too.
drop1 = _rpm.drop1_lmrobdet
drop1_lmrobdetMM = _rpm.drop1_lmrobdet
# Control factories
lmrobM_control = _rpm.lmrobm_control
lmrobdet_control = _rpm.lmrobdet_control
# Refinement helper
refine_sm = _rpm.refine_sm

# Covariance
covRob = _rpm.cov_rob
Multirobu = _rpm.cov_rob
covRobMM = _rpm.cov_rob_mm
MMultiSHR = _rpm.cov_rob_mm
covRobRocke = _rpm.cov_rob_rocke
RockeMulti = _rpm.cov_rob_rocke
covClassic = _rpm.cov_classic
KurtSDNew = _rpm.kurt_sd_new
initPP = _rpm.kurt_sd_new
fastmve = _rpm.fastmve

# PCA
pcaRobS = _rpm.pca_rob_s
SMPCA = _rpm.pca_rob_s
prcompRob = _rpm.prcomp_rob

# GLM
BYlogreg = _rpm.by_logreg
logregBY = _rpm.by_logreg
WBYlogreg = _rpm.wby_logreg
logregWBY = _rpm.wby_logreg
WMLlogreg = _rpm.wml_logreg
logregWML = _rpm.wml_logreg

# External stretch packages (pense / GSE / TSGS)
pense = _rpm.pense
pense_cv = _rpm.pense_cv
GSE = _rpm.gse
TSGS = _rpm.tsgs

# External stretch packages (example-script reproduction, D-024).
# `arima.rob`, `varComprob.control`, `cubinf.control` have dots → the canonical
# Python snake_case name is the alias the user gets here too.
arima_rob = _rpm.arima_rob
varComprob = _rpm.var_comprob
varComprob_control = _rpm.var_comprob_control
glmrob = _rpm.glmrob
cubinf = _rpm.cubinf

# ψ-family helpers (live under rpm.psi.* but also useful at top level)
bisquare = _rpm.psi.bisquare
huber = _rpm.psi.huber
opt = _rpm.psi.opt
mopt = _rpm.psi.mopt
optv0 = _rpm.psi.optv0
moptv0 = _rpm.psi.moptv0
rho = _rpm.psi.rho
rhoprime = _rpm.psi.rhoprime
rhoprime2 = _rpm.psi.rhoprime2

# Datasets — exposed via `data("mineral")`-style helper:
def data(name: str):
    """R-style ``data('mineral')`` loader. Equivalent to
    ``robstattm_py.datasets.<name>()``.
    """
    fn = getattr(_rpm.datasets, name, None)
    if fn is None or not callable(fn):
        raise KeyError(
            f"dataset {name!r} not found. Available: "
            + ", ".join(sorted(d for d in dir(_rpm.datasets) if not d.startswith("_")))
        )
    return fn()


__all__ = [
    # univariate
    "locScaleM", "MLocDis", "scaleM", "mscale",
    # regression
    "lmrobM", "lmrobdetMM", "lmrobdetDCML",
    "pyinit", "INVTR2",
    "step_lmrobdetMM", "rob_linear_test", "lsRobTestMM", "lmrobdetLinTest",
    "drop1", "drop1_lmrobdetMM",
    "lmrobM_control", "lmrobdet_control",
    "refine_sm",
    # covariance
    "covRob", "Multirobu",
    "covRobMM", "MMultiSHR",
    "covRobRocke", "RockeMulti",
    "covClassic",
    "KurtSDNew", "initPP",
    "fastmve",
    # pca
    "pcaRobS", "SMPCA", "prcompRob",
    # glm
    "BYlogreg", "logregBY",
    "WBYlogreg", "logregWBY",
    "WMLlogreg", "logregWML",
    # external stretch packages
    "pense", "pense_cv", "GSE", "TSGS",
    "arima_rob", "varComprob", "varComprob_control", "glmrob", "cubinf",
    # psi
    "bisquare", "huber", "opt", "mopt", "optv0", "moptv0",
    "rho", "rhoprime", "rhoprime2",
    # data
    "data",
]
