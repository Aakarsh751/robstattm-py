"""Strict-tier tests for ``CovRobResult.summary()`` and
``CovClassicResult.summary()``, ports of R's ``summary.covRob`` and
``summary.covClassic``."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from robstattm_py._r import r as _r

try:
    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


@pytest.fixture(scope="module")
def R():
    if not HAS_R:
        pytest.skip("R not available")
    return _r().r


# ----------------------------------------------------------------------
# covRob (MM auto-selected since p=13 actually triggers Rocke; verify)
# ----------------------------------------------------------------------
@needs_r
class TestCovRobSummaryWine:
    """Wine data: 13 features, R auto-selects Rocke."""

    @pytest.fixture(scope="class")
    def py_summary(self):
        df = rpm.datasets.wine()
        rpm.set_seed(42)
        _r().r("set.seed(42)")
        fit = rpm.cov_rob(df, type="MM")  # force MM to bypass singularity in Rocke
        return fit.summary()

    @pytest.fixture(scope="class")
    def r_summary(self):
        ro = _r()
        ro.r(
            "library(RobStatTM); set.seed(42); data(wine); "
            "X_test <- as.matrix(wine[, sapply(wine, is.numeric)]); "
            "rpm_test_cov_fit  <- covRob(X_test, type='MM'); "
            "rpm_test_cov_summ <- summary(rpm_test_cov_fit)"
        )
        return ro.r

    def test_cov_matrix(self, py_summary, r_summary):
        r_cov = np.asarray(r_summary("rpm_test_cov_summ$cov"), dtype=float)
        np.testing.assert_array_equal(py_summary.cov, r_cov)

    def test_center(self, py_summary, r_summary):
        r_c = np.asarray(r_summary("rpm_test_cov_summ$center"), dtype=float).ravel()
        np.testing.assert_array_equal(py_summary.center, r_c)

    def test_eigenvalues(self, py_summary, r_summary):
        r_e = np.asarray(r_summary("rpm_test_cov_summ$evals"), dtype=float).ravel()
        np.testing.assert_array_equal(py_summary.evals, r_e)

    def test_eigenvalue_names(self, py_summary, r_summary):
        r_n = tuple(r_summary("names(rpm_test_cov_summ$evals)"))
        assert py_summary.eval_names == r_n

    def test_distances(self, py_summary, r_summary):
        r_d = np.asarray(r_summary("rpm_test_cov_summ$dist"), dtype=float).ravel()
        np.testing.assert_array_equal(py_summary.dist, r_d)

    def test_classical_flag(self, py_summary):
        assert py_summary.classical is False
        assert "Robust" in repr(py_summary)

    def test_no_cor_when_corr_false(self, py_summary):
        assert py_summary.cor is None

    def test_proportion_of_variance_helper(self, py_summary):
        prop = py_summary.proportion_of_variance
        assert prop.shape == py_summary.evals.shape
        # sum equals 1 in the eigenvalue normalization
        assert abs(prop.sum() - 1.0) < 1e-12

    def test_repr_html_contains_eigenvalues(self, py_summary):
        html = py_summary._repr_html_()
        assert "Eigenvalue" in html and "Robust" in html


# ----------------------------------------------------------------------
# covClassic
# ----------------------------------------------------------------------
@needs_r
class TestCovClassicSummaryWine:

    @pytest.fixture(scope="class")
    def py_summary(self):
        df = rpm.datasets.wine()
        fit = rpm.cov_classic(df)
        return fit.summary()

    @pytest.fixture(scope="class")
    def r_summary(self):
        ro = _r()
        ro.r(
            "library(RobStatTM); data(wine); "
            "X_cls <- as.matrix(wine[, sapply(wine, is.numeric)]); "
            "rpm_test_cls_fit  <- covClassic(X_cls); "
            "rpm_test_cls_summ <- summary(rpm_test_cls_fit)"
        )
        return ro.r

    def test_cov_matrix(self, py_summary, r_summary):
        r_cov = np.asarray(r_summary("rpm_test_cls_summ$cov"), dtype=float)
        np.testing.assert_array_equal(py_summary.cov, r_cov)

    def test_center(self, py_summary, r_summary):
        r_c = np.asarray(r_summary("rpm_test_cls_summ$center"), dtype=float).ravel()
        np.testing.assert_array_equal(py_summary.center, r_c)

    def test_eigenvalues(self, py_summary, r_summary):
        r_e = np.asarray(r_summary("rpm_test_cls_summ$evals"), dtype=float).ravel()
        np.testing.assert_array_equal(py_summary.evals, r_e)

    def test_distances(self, py_summary, r_summary):
        r_d = np.asarray(r_summary("rpm_test_cls_summ$dist"), dtype=float).ravel()
        np.testing.assert_array_equal(py_summary.dist, r_d)

    def test_classical_flag(self, py_summary):
        assert py_summary.classical is True
        assert "Classical" in repr(py_summary)


# ----------------------------------------------------------------------
# CovRobMM and CovRobRocke separate result types also expose .summary()
# ----------------------------------------------------------------------
@needs_r
def test_cov_rob_mm_summary_smoke():
    df = rpm.datasets.wine()
    rpm.set_seed(7)
    _r().r("set.seed(7)")
    fit = rpm.cov_rob_mm(df)
    s = fit.summary()
    assert s.cov.shape == (df.shape[1], df.shape[1])
    assert s.evals.shape == (df.shape[1],)
    assert s.dist is not None and s.dist.shape == (df.shape[0],)


@needs_r
def test_cov_summary_works_without_r_fit():
    """summary() depends on the extracted cov/center/dist/cor arrays only,
    so it remains usable even if the raw R fit isn't around (e.g. after
    pickling)."""
    from dataclasses import replace
    df = rpm.datasets.wine()
    fit = rpm.cov_classic(df)
    fit_no = replace(fit, _r_fit=None)
    s = fit_no.summary()
    assert s.cov.shape == fit.cov.shape
    np.testing.assert_array_equal(s.evals, fit.summary().evals)
