"""Synthetic-data pipelines — Python-synthesized data, strict parity vs R.

Every test here **builds data in NumPy/pandas**, pushes the *same* array to R's
globalenv, runs the Python wrapper and the equivalent direct R call, and asserts
**bit-identical** outputs (``atol=0, rtol=0``) on the substantive numeric fields
— not just shapes. Stochastic estimators are seeded on both sides
(``rpm.set_seed`` / ``set.seed``) so the R RNG streams coincide.

Test matrix
-----------
| Wrapper                       | Data source (synthetic)                  | Parameters swept            | R fields compared                              |
|-------------------------------|------------------------------------------|-----------------------------|------------------------------------------------|
| loc_scale_m                   | 1-D Gaussian + gross outliers            | psi ∈ {mopt,bisquare,huber} | mu, std.mu, disper                             |
| m_scale                       | 1-D Gaussian + gross outliers            | family ∈ {bisquare,mopt,opt}| scalar M-scale                                 |
| psi.rho / rhoprime / rhoprime2| 1-D grid                                 | family ∈ {bisquare,opt,mopt}| elementwise rho / psi / psi'                   |
| invtr2                        | scalar RR2                               | bisquare cc                 | scalar INVTR2                                  |
| lmrobdet_mm / dcml / lmrob_m  | n×p linear model + 10% vertical outliers | estimator, family/eff       | coef, scale, residuals, fitted.values, cov     |
| cov_rob_mm / rocke / cov_rob  | n×p correlated Gaussian + row contam.    | corr on/off, dispatcher     | center, cov, dist                              |
| cov_classic                   | n×p correlated Gaussian                  | corr on/off                 | center, cov                                    |
| fastmve                       | n×p correlated Gaussian                  | —                           | center, cov, scale                             |
| kurt_sd_new                   | n×p correlated Gaussian                  | —                           | center, cova                                   |
| prcomp_rob                    | n×p correlated Gaussian                  | rank                        | sdev, rotation, center                         |
| pca_rob_s                     | n×p correlated Gaussian                  | ncomp                       | eigvec, mu, propex, propSPC                    |
| by/wby/wml_logreg             | binary GLM, mislabelled outliers         | method                      | coef, standard.deviation, fitted.values, dev.  |
| refine_sm                     | n×p linear model                         | family bisquare             | beta.rw, scale.rw                              |
| pense / pense_cv              | sparse-beta linear model                 | alpha                       | lambda path, coef path / coef(min)            |
| gse / tsgs                    | n×p Gaussian with MCAR missingness       | —                           | mu, cov (slots)                                |

Run::

    pytest exploration/test_synthetic_pipelines.py -v
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

import robstattm_py as rpm

sys.path.insert(0, os.path.dirname(__file__))
from _synth import (  # noqa: E402
    make_binary_xy,
    make_cov_data,
    make_regression_df,
    make_univariate,
    push_to_r,
    reval,
    rm_r,
)

from tests.conftest import (  # noqa: E402
    assert_array_equal,
    assert_scalar_equal,
    needs_gse,
    needs_pense,
    needs_r,
)

# ===========================================================================
# 1. Univariate location / scale M-estimators
# ===========================================================================


@needs_r
@pytest.mark.parametrize("psi", ["mopt", "bisquare", "huber"])
@pytest.mark.parametrize("eff", [0.90, 0.95])
def test_loc_scale_m_synth_vs_r(psi, eff):
    u = make_univariate(n=45, seed=101, outlier_frac=0.12)
    push_to_r("syn_u", u)
    try:
        py = rpm.loc_scale_m(u, psi=psi, eff=eff)
        reval(
            f"syn_ls <- RobStatTM::locScaleM(syn_u, psi='{psi}', eff={eff})"
        )
        assert_scalar_equal(py.mu, reval("syn_ls$mu"), where=f"mu[{psi}/{eff}]")
        assert_scalar_equal(py.std_mu, reval("syn_ls$std.mu"), where="std_mu")
        assert_scalar_equal(py.disper, reval("syn_ls$disper"), where="disper")
    finally:
        rm_r("syn_u", "syn_ls")


@needs_r
@pytest.mark.parametrize("family", ["bisquare", "mopt", "opt"])
@pytest.mark.parametrize("delta", [0.5, 0.25])
def test_m_scale_synth_vs_r(family, delta):
    u = make_univariate(n=50, seed=202, outlier_frac=0.10)
    push_to_r("syn_u", u)
    try:
        py = rpm.m_scale(u, family=family, delta=delta)
        reval(
            f"syn_ms <- RobStatTM::scaleM(syn_u, delta={delta}, family='{family}')"
        )
        assert_scalar_equal(py, reval("syn_ms"), where=f"m_scale[{family}/{delta}]")
    finally:
        rm_r("syn_u", "syn_ms")


# ===========================================================================
# 2. psi-family rho / psi / psi' and the INVTR2 helper (deterministic)
# ===========================================================================


@needs_r
@pytest.mark.parametrize("family", ["bisquare", "opt", "mopt"])
def test_psi_rho_family_synth_vs_r(family):
    rng = np.random.default_rng(303)
    u = np.sort(rng.uniform(-4.0, 4.0, size=37)).astype(np.float64)
    cc = getattr(rpm.psi, family)(0.95)  # tuning constant(s) at 95% efficiency
    push_to_r("syn_u", u)
    # atleast_1d: numpy2ri cannot convert a 0-d array (scalar bisquare cc) —
    # it raises "'dims' cannot be of length 0". A length-1 R vector is an
    # identical `cc` argument to a scalar in R.
    push_to_r("syn_cc", np.atleast_1d(np.asarray(cc, dtype=float)))
    try:
        py_rho = rpm.psi.rho(u, family=family, cc=cc, standardize=True)
        py_psi = rpm.psi.rhoprime(u, family=family, cc=cc, standardize=False)
        py_psi2 = rpm.psi.rhoprime2(u, family=family, cc=cc, standardize=False)
        r_rho = reval(f"RobStatTM::rho(syn_u, family='{family}', cc=syn_cc, standardize=TRUE)")
        r_psi = reval(f"RobStatTM::rhoprime(syn_u, family='{family}', cc=syn_cc, standardize=FALSE)")
        r_psi2 = reval(f"RobStatTM::rhoprime2(syn_u, family='{family}', cc=syn_cc, standardize=FALSE)")
        assert_array_equal(py_rho, r_rho, where=f"rho[{family}]")
        assert_array_equal(py_psi, r_psi, where=f"rhoprime[{family}]")
        assert_array_equal(py_psi2, r_psi2, where=f"rhoprime2[{family}]")
    finally:
        rm_r("syn_u", "syn_cc")


@needs_r
@pytest.mark.parametrize("rr2", [0.3, 0.5, 0.75])
def test_invtr2_bisquare_synth_vs_r(rr2):
    cc = float(rpm.psi.bisquare(0.85))
    py = rpm.invtr2(rr2, "bisquare", cc)
    r_val = reval(f"RobStatTM::INVTR2({rr2}, 'bisquare', {cc!r})")
    assert_scalar_equal(py, r_val, where=f"invtr2[{rr2}]")


# ===========================================================================
# 3. Regression — MM / DCML / M, full-field strict parity on contaminated data
# ===========================================================================

# (python_fn, r_fn, builds_control)
_REG_ESTIMATORS = [
    ("lmrobdet_mm", "lmrobdetMM"),
    ("lmrobdet_dcml", "lmrobdetDCML"),
    ("lmrob_m", "lmrobM"),
]


@needs_r
@pytest.mark.parametrize("py_fn,r_fn", _REG_ESTIMATORS, ids=[e[0] for e in _REG_ESTIMATORS])
def test_regression_synth_default_vs_r(py_fn, r_fn):
    """Default control: Python wrapper vs direct R, identical synthetic frame."""
    df = make_regression_df(n=70, p=3, seed=11, outlier_frac=0.10, outlier_mag=14.0)
    formula = "y ~ x1 + x2 + x3"
    push_to_r("syn_reg", df)
    try:
        rpm.set_seed(7)
        py = getattr(rpm, py_fn)(formula, data=df)
        reval(f"set.seed(7L); syn_fit <- RobStatTM::{r_fn}({formula}, data=syn_reg)")
        assert_array_equal(py.coefficients, reval("as.numeric(coef(syn_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("syn_fit$scale"), where="scale")
        assert_array_equal(
            py.fitted_values, reval("as.numeric(syn_fit$fitted.values)"), where="fitted"
        )
        assert_array_equal(
            py.residuals, reval("as.numeric(syn_fit$residuals)"), where="residuals"
        )
        assert_array_equal(py.cov, reval("syn_fit$cov"), where="cov")
    finally:
        rm_r("syn_reg", "syn_fit")


@needs_r
@pytest.mark.parametrize("family,eff", [("bisquare", 0.85), ("mopt", 0.95)])
def test_lmrobdet_mm_synth_custom_control_vs_r(family, eff):
    """Non-default control reproduced bit-for-bit (mirrors the D-021 fix path)."""
    df = make_regression_df(n=80, p=2, seed=23, outlier_frac=0.15, leverage=True)
    formula = "y ~ x1 + x2"
    push_to_r("syn_reg", df)
    try:
        ctrl = rpm.lmrobdet_control(family=family, efficiency=eff, bb=0.5)
        rpm.set_seed(99)
        py = rpm.lmrobdet_mm(formula, data=df, control=ctrl)
        reval(
            f"set.seed(99L); "
            f"sc <- RobStatTM::lmrobdet.control(family='{family}', efficiency={eff}, bb=0.5); "
            f"syn_fit <- RobStatTM::lmrobdetMM({formula}, data=syn_reg, control=sc)"
        )
        assert_array_equal(py.coefficients, reval("as.numeric(coef(syn_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("syn_fit$scale"), where="scale")
        assert_array_equal(
            py.fitted_values, reval("as.numeric(syn_fit$fitted.values)"), where="fitted"
        )
    finally:
        rm_r("syn_reg", "syn_fit", "sc")


@needs_r
def test_regression_xy_path_matches_formula_and_r():
    """X/y matrix entry point == formula entry point == direct R on the frame."""
    df = make_regression_df(n=60, p=3, seed=31, outlier_frac=0.08)
    X = df[["x1", "x2", "x3"]].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=float)
    push_to_r("syn_reg", df)
    try:
        rpm.set_seed(5)
        fit_xy = rpm.lmrobdet_mm(X=X, y=y)
        rpm.set_seed(5)
        fit_formula = rpm.lmrobdet_mm("y ~ x1 + x2 + x3", data=df)
        reval("set.seed(5L); syn_fit <- RobStatTM::lmrobdetMM(y ~ x1 + x2 + x3, data=syn_reg)")
        r_coef = reval("as.numeric(coef(syn_fit))")
        assert_array_equal(fit_xy.coefficients, fit_formula.coefficients, where="xy-vs-formula")
        assert_array_equal(fit_xy.coefficients, r_coef, where="xy-vs-R")
    finally:
        rm_r("syn_reg", "syn_fit")


# ===========================================================================
# 4. Covariance — MM / Rocke / dispatcher / classic / fastmve / kurt_sd_new
# ===========================================================================


@needs_r
@pytest.mark.parametrize("corr", [False, True])
def test_cov_rob_mm_synth_vs_r(corr):
    X = make_cov_data(n=90, p=5, seed=41, contam_frac=0.10)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(13)
        py = rpm.cov_rob_mm(X, corr=corr)
        reval(
            f"set.seed(13L); syn_cov <- RobStatTM::covRobMM(syn_X"
            f"{', corr=TRUE' if corr else ''})"
        )
        assert_array_equal(py.center, reval("syn_cov$center"), where="center")
        assert_array_equal(py.cov, reval("syn_cov$cov"), where="cov")
        assert_array_equal(py.dist, reval("as.numeric(syn_cov$dist)"), where="dist")
        if corr:
            assert_array_equal(py.cor, reval("syn_cov$cor"), where="cor")
    finally:
        rm_r("syn_X", "syn_cov")


@needs_r
def test_cov_rob_rocke_synth_highdim_vs_r():
    X = make_cov_data(n=120, p=12, seed=42, contam_frac=0.08)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(17)
        py = rpm.cov_rob_rocke(X)
        reval("set.seed(17L); syn_cov <- RobStatTM::covRobRocke(syn_X)")
        assert_array_equal(py.center, reval("syn_cov$center"), where="center")
        assert_array_equal(py.cov, reval("syn_cov$cov"), where="cov")
        assert_array_equal(py.dist, reval("as.numeric(syn_cov$dist)"), where="dist")
    finally:
        rm_r("syn_X", "syn_cov")


@needs_r
@pytest.mark.parametrize(
    "n,p,expected",
    [(90, 6, "MM"), (120, 12, "Rocke")],
    ids=["auto-MM-p6", "auto-Rocke-p12"],
)
def test_cov_rob_dispatch_synth_vs_r(n, p, expected):
    X = make_cov_data(n=n, p=p, seed=43, contam_frac=0.06)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(21)
        py = rpm.cov_rob(X, type="auto")
        assert py.estimator_type == expected
        reval("set.seed(21L); syn_cov <- RobStatTM::covRob(syn_X, type='auto')")
        assert_array_equal(py.center, reval("syn_cov$center"), where="center")
        assert_array_equal(py.cov, reval("syn_cov$cov"), where="cov")
    finally:
        rm_r("syn_X", "syn_cov")


@needs_r
@pytest.mark.parametrize("corr", [False, True])
def test_cov_classic_synth_vs_r(corr):
    X = make_cov_data(n=70, p=4, seed=44)
    push_to_r("syn_X", X)
    try:
        py = rpm.cov_classic(X, corr=corr)
        reval(
            f"syn_cov <- RobStatTM::covClassic(syn_X{', corr=TRUE' if corr else ''})"
        )
        assert_array_equal(py.center, reval("syn_cov$center"), where="center")
        assert_array_equal(py.cov, reval("syn_cov$cov"), where="cov")
        if corr:
            assert_array_equal(py.cor, reval("syn_cov$cor"), where="cor")
    finally:
        rm_r("syn_X", "syn_cov")


@needs_r
def test_fastmve_synth_vs_r():
    X = make_cov_data(n=80, p=4, seed=45, contam_frac=0.05)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(8)
        py = rpm.fastmve(X)
        reval("set.seed(8L); syn_mve <- RobStatTM::fastmve(syn_X)")
        assert_array_equal(py.center, reval("as.numeric(syn_mve$center)"), where="center")
        assert_array_equal(py.cov, reval("syn_mve$cov"), where="cov")
        assert_scalar_equal(py.scale, reval("syn_mve$scale"), where="scale")
    finally:
        rm_r("syn_X", "syn_mve")


@needs_r
def test_kurt_sd_new_synth_vs_r():
    X = make_cov_data(n=85, p=5, seed=46, contam_frac=0.06)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(3)
        py = rpm.kurt_sd_new(X)
        reval("set.seed(3L); syn_k <- RobStatTM::KurtSDNew(syn_X)")
        assert_array_equal(py.center, reval("as.numeric(syn_k$center)"), where="center")
        assert_array_equal(py.cova, reval("syn_k$cova"), where="cova")
    finally:
        rm_r("syn_X", "syn_k")


# ===========================================================================
# 5. PCA — prcomp_rob (prcomp shape) and pca_rob_s (M-scale)
# ===========================================================================


@needs_r
def test_prcomp_rob_synth_vs_r():
    X = make_cov_data(n=100, p=6, seed=51, contam_frac=0.07)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(19)
        py = rpm.prcomp_rob(X, rank=4)
        reval("set.seed(19L); syn_pca <- RobStatTM::prcompRob(syn_X, rank.=4L)")
        assert_array_equal(py.sdev, reval("as.numeric(syn_pca$sdev)"), where="sdev")
        assert_array_equal(py.rotation, reval("syn_pca$rotation"), where="rotation")
        assert_array_equal(py.center, reval("as.numeric(syn_pca$center)"), where="center")
    finally:
        rm_r("syn_X", "syn_pca")


@needs_r
def test_pca_rob_s_synth_vs_r():
    X = make_cov_data(n=110, p=6, seed=52, contam_frac=0.05)
    push_to_r("syn_X", X)
    try:
        rpm.set_seed(27)
        py = rpm.pca_rob_s(X, ncomp=3)
        reval("set.seed(27L); syn_pca <- RobStatTM::pcaRobS(syn_X, ncomp=3)")
        assert_array_equal(py.eigvec, reval("syn_pca$eigvec"), where="eigvec")
        assert_array_equal(py.mu, reval("as.numeric(syn_pca$mu)"), where="mu")
        assert_scalar_equal(py.propex, reval("syn_pca$propex"), where="propex")
        assert_array_equal(py.prop_spc, reval("as.numeric(syn_pca$propSPC)"), where="propSPC")
    finally:
        rm_r("syn_X", "syn_pca")


# ===========================================================================
# 6. GLM — robust logistic regression on a synthetic binary design
# ===========================================================================

_GLM_METHODS = [
    ("by_logreg", "BYlogreg"),
    ("wby_logreg", "WBYlogreg"),
    ("wml_logreg", "WMLlogreg"),
]


@needs_r
@pytest.mark.parametrize("py_fn,r_fn", _GLM_METHODS, ids=[m[0] for m in _GLM_METHODS])
def test_glm_synth_vs_r(py_fn, r_fn):
    X, y = make_binary_xy(n=140, p=3, seed=61, contam_frac=0.05)
    push_to_r("syn_X", X)
    push_to_r("syn_y", y)
    try:
        rpm.set_seed(2)
        py = getattr(rpm, py_fn)(X, y)
        # R: y as a 1-column matrix; intercept=1 (numeric) like the wrapper.
        reval(
            f"set.seed(2L); syn_glm <- RobStatTM::{r_fn}(syn_X, "
            f"matrix(syn_y, ncol=1), intercept=1)"
        )
        assert_array_equal(
            py.coefficients, reval("as.numeric(syn_glm$coefficients)"), where="coef"
        )
        assert_array_equal(
            py.standard_deviation,
            reval("as.numeric(syn_glm$standard.deviation)"),
            where="sd",
        )
        assert_array_equal(
            py.fitted_values, reval("as.numeric(syn_glm$fitted.values)"), where="fitted"
        )
        assert_array_equal(
            py.residual_deviances,
            reval("as.numeric(syn_glm$residual.deviances)"),
            where="deviances",
        )
    finally:
        rm_r("syn_X", "syn_y", "syn_glm")


# ===========================================================================
# 7. refine_sm — deterministic low-level refinement, parity on identical inputs
# ===========================================================================


@needs_r
def test_refine_sm_synth_vs_r():
    df = make_regression_df(n=60, p=2, seed=71, outlier_frac=0.0)
    # design with intercept column; beta length p = 3
    X = np.column_stack([np.ones(len(df)), df[["x1", "x2"]].to_numpy(dtype=float)])
    y = df["y"].to_numpy(dtype=float)
    beta0, *_ = np.linalg.lstsq(X, y, rcond=None)
    scale0 = float(np.std(y - X @ beta0))
    b_const = float(rpm.psi.bisquare(0.5))
    cc_const = float(rpm.psi.bisquare(0.85))

    py = rpm.refine_sm(
        X, y, initial_beta=beta0, initial_scale=scale0,
        b=b_const, cc=cc_const, family="bisquare", step="M",
    )
    push_to_r("syn_X", X)
    push_to_r("syn_y", y)
    push_to_r("syn_b0", np.asarray(beta0, dtype=float))
    try:
        # as.numeric() strips the `dim` attribute numpy2ri puts on 1-D arrays;
        # without it refine.sm's internal `y - x %*% beta` raises
        # "non-conformable arrays" (a c(60) array vs a c(60,1) matrix).
        reval(
            f"syn_ref <- RobStatTM::refine.sm(x=as.matrix(syn_X), "
            f"y=as.numeric(syn_y), "
            f"initial.beta=as.numeric(syn_b0), initial.scale={scale0!r}, "
            f"k=50, conv=1, b={b_const!r}, cc={cc_const!r}, "
            f"family='bisquare', step='M', tol=1e-7)"
        )
        assert_array_equal(py.beta, reval("as.numeric(syn_ref$beta.rw)"), where="beta.rw")
        assert_scalar_equal(py.scale, reval("syn_ref$scale.rw"), where="scale.rw")
    finally:
        rm_r("syn_X", "syn_y", "syn_b0", "syn_ref")


# ===========================================================================
# 8. Stretch externals (skip when CRAN package absent)
# ===========================================================================


@needs_r
@needs_pense
@pytest.mark.parametrize("alpha", [0.5, 1.0])
def test_pense_synth_path_vs_r(alpha):
    df = make_regression_df(n=60, p=6, seed=81, outlier_frac=0.10)
    X = df[[f"x{i}" for i in range(1, 7)]].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=float)
    push_to_r("syn_X", X)
    push_to_r("syn_y", y)
    try:
        rpm.set_seed(1)
        py = rpm.pense(X, y, alpha=alpha, nlambda=10)
        reval(
            f"set.seed(1L); syn_pf <- pense::pense(syn_X, drop(syn_y), "
            f"alpha={alpha}, nlambda=10)"
        )
        assert_array_equal(
            py.lambda_path, reval("syn_pf$lambda[[1]]"), where="lambda_path"
        )
        # Coefficient path via R's own coef(), exactly as the wrapper does.
        r_coef = reval(
            "sapply(syn_pf$lambda[[1]], "
            "function(L) as.numeric(coef(syn_pf, lambda=L)))"
        )
        assert_array_equal(py.coefficients, r_coef, where="coef_path")
    finally:
        rm_r("syn_X", "syn_y", "syn_pf")


@needs_r
@needs_gse
def test_gse_synth_missing_vs_r():
    X = make_cov_data(n=90, p=5, seed=91)
    rng = np.random.default_rng(91)
    Xm = X.copy()
    Xm[rng.random(X.shape) < 0.05] = np.nan
    push_to_r("syn_X", Xm)
    try:
        rpm.set_seed(4)
        py = rpm.gse(Xm)
        reval("set.seed(4L); syn_gse <- GSE::GSE(syn_X)")
        assert_array_equal(
            py.mu, reval("as.numeric(GSE::getLocation(syn_gse))"), where="mu"
        )
        assert_array_equal(py.cov, reval("GSE::getScatter(syn_gse)"), where="cov")
    finally:
        rm_r("syn_X", "syn_gse")
