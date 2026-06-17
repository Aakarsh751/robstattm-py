"""Edge cases — degenerate inputs must fail cleanly or match R exactly.

A robust wrapper layer should never segfault, hang, or return silent garbage on
pathological data. These tests pin down the behavior on:

* NaN / Inf inputs            → clean Python ``ValueError`` (caught before R)
* constant / single column    → clean ``RobStatTMRError`` (R raises; we surface it)
* p > n covariance            → clean ``RobStatTMRError``
* rank-deficient regression   → identical to R (R returns an ``NaN`` coefficient)
* perfect GLM separation      → BYlogreg matches R; WBYlogreg's rough edge (B-009)
* malformed arguments         → ``ValueError`` / ``TypeError`` with a clear message

Where R itself succeeds (rank-deficient regression), we assert **bit-parity**
with R (NaN-aware). Where R errors, we assert the Python side raises the wrapped
error rather than crashing.

Run::

    pytest exploration/test_edge_cases.py -v
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm

sys.path.insert(0, os.path.dirname(__file__))
from _synth import make_binary_xy, make_cov_data, push_to_r, reval, rm_r  # noqa: E402

from tests.conftest import assert_array_equal, assert_scalar_equal, needs_r  # noqa: E402


# ===========================================================================
# 1. NaN / Inf inputs are rejected in Python, before the rpy2 boundary
# ===========================================================================


def _nan_1d():
    return np.array([1.0, 2.0, np.nan, 4.0])


def _nan_2d():
    X = np.random.default_rng(0).normal(size=(20, 3))
    X[2, 1] = np.nan
    return X


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda: rpm.loc_scale_m(_nan_1d()), id="loc_scale_m"),
        pytest.param(lambda: rpm.cov_rob_mm(_nan_2d()), id="cov_rob_mm"),
        pytest.param(lambda: rpm.cov_classic(_nan_2d()), id="cov_classic"),
        pytest.param(lambda: rpm.cov_rob(_nan_2d()), id="cov_rob"),
        pytest.param(lambda: rpm.prcomp_rob(_nan_2d()), id="prcomp_rob"),
        pytest.param(
            lambda: rpm.by_logreg(_nan_2d(), np.zeros(20)), id="by_logreg"
        ),
    ],
)
def test_nan_inputs_raise_value_error(call):
    with pytest.raises(ValueError):
        call()


def test_inf_input_rejected():
    X = np.random.default_rng(0).normal(size=(15, 3))
    X[0, 0] = np.inf
    with pytest.raises(ValueError):
        rpm.cov_rob_mm(X)


# ===========================================================================
# 2. Degenerate covariance / PCA: R errors, Python surfaces RobStatTMRError
# ===========================================================================


@needs_r
def test_constant_column_covariance_raises_clean():
    X = make_cov_data(n=50, p=4, seed=10)
    X[:, 2] = 7.0  # constant (zero-variance) column → singular
    rpm.set_seed(1)
    with pytest.raises(rpm.RobStatTMRError):
        rpm.cov_rob_mm(X)
    with pytest.raises(rpm.RobStatTMRError):
        rpm.cov_classic(X)


@needs_r
def test_single_column_covariance_and_pca_raise_clean():
    X = np.random.default_rng(2).normal(size=(40, 1))
    rpm.set_seed(1)
    with pytest.raises(rpm.RobStatTMRError):
        rpm.cov_rob_mm(X)
    with pytest.raises(rpm.RobStatTMRError):
        rpm.prcomp_rob(X)


@needs_r
def test_highdim_p_greater_than_n_covariance_raises_clean():
    X = make_cov_data(n=6, p=12, seed=3)  # p > n → not positive definite
    rpm.set_seed(1)
    with pytest.raises(rpm.RobStatTMRError):
        rpm.cov_rob_mm(X)


# ===========================================================================
# 3. Rank-deficient regression: R returns NaN coef — assert bit-parity
# ===========================================================================


@needs_r
def test_rank_deficient_regression_matches_r():
    rng = np.random.default_rng(2)
    x1 = rng.normal(size=50)
    df = pd.DataFrame({"y": 1.0 + 2.0 * x1 + rng.normal(scale=0.3, size=50), "x1": x1})
    df["x2"] = df["x1"]  # exact collinearity → R drops one term (NaN coef)
    df = df.astype("float64")
    push_to_r("ec_df", df)
    try:
        rpm.set_seed(3)
        py = rpm.lmrobdet_mm("y ~ x1 + x2", data=df)
        reval("set.seed(3L); ec_fit <- RobStatTM::lmrobdetMM(y ~ x1 + x2, data=ec_df)")
        # NaN-aware comparison (np.testing treats NaN == NaN as equal).
        assert_array_equal(py.coefficients, reval("as.numeric(coef(ec_fit))"), where="coef")
        assert np.isnan(py.coefficients[-1]), "expected dropped duplicate term to be NaN"
        assert_scalar_equal(py.scale, reval("ec_fit$scale"), where="scale")
    finally:
        rm_r("ec_df", "ec_fit")


# ===========================================================================
# 4. Perfect GLM separation
# ===========================================================================


@needs_r
def test_glm_separation_by_logreg_matches_r():
    """BYlogreg returns a (possibly non-converged) fit on separable data — and
    it must match R field-for-field."""
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 1))
    y = (X[:, 0] > 0).astype(float)  # perfectly separable
    push_to_r("ec_X", X)
    push_to_r("ec_y", y)
    try:
        rpm.set_seed(2)
        py = rpm.by_logreg(X, y)
        reval(
            "set.seed(2L); ec_glm <- RobStatTM::BYlogreg(ec_X, "
            "matrix(ec_y, ncol=1), intercept=1)"
        )
        assert_array_equal(
            py.coefficients, reval("as.numeric(ec_glm$coefficients)"), where="coef"
        )
    finally:
        rm_r("ec_X", "ec_y", "ec_glm")


@needs_r
def test_glm_separation_wby_logreg_raises_clean():
    """WBYlogreg on perfectly separable data: R returns a *truncated* object
    (only ``convergence/objective/coef``). The wrapper detects the missing
    ``coefficients`` field and raises a clear ``RobStatTMRError`` (B-009 fixed).
    """
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 1))
    y = (X[:, 0] > 0).astype(float)
    rpm.set_seed(2)
    with pytest.raises(rpm.RobStatTMRError, match="usable fit"):
        rpm.wby_logreg(X, y)


# ===========================================================================
# 5. Malformed arguments → clear, early Python errors
# ===========================================================================


def test_invalid_dispatch_type_raises():
    X = make_cov_data(n=30, p=3, seed=1)
    with pytest.raises(ValueError):
        rpm.cov_rob(X, type="banana")


def test_m_scale_delta_out_of_range_raises():
    with pytest.raises(ValueError):
        rpm.m_scale(np.arange(10.0), delta=1.5)


def test_empty_input_raises():
    with pytest.raises(ValueError):
        rpm.loc_scale_m(np.array([]))


def test_glm_length_mismatch_raises():
    X = np.random.default_rng(0).normal(size=(20, 2))
    y = np.zeros(19)  # wrong length
    with pytest.raises(ValueError):
        rpm.by_logreg(X, y)


def test_glm_non_binary_y_raises():
    X = np.random.default_rng(0).normal(size=(20, 2))
    y = np.full(20, 2.0)  # not 0/1
    with pytest.raises(ValueError):
        rpm.by_logreg(X, y)


def test_regression_mixed_invocation_raises():
    df = pd.DataFrame({"y": [1.0, 2.0, 3.0], "x": [0.1, 0.2, 0.3]})
    X = df[["x"]].to_numpy()
    y = df["y"].to_numpy()
    # passing both (formula, data) and (X, y) is contradictory
    with pytest.raises(TypeError):
        rpm.lmrobdet_mm("y ~ x", data=df, X=X, y=y)
