"""Strict-tier tests for ``PrcompRobResult.summary()`` — port of R's
``summary.prcompRob``."""
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


@needs_r
class TestPrcompRobSummaryWine:

    @pytest.fixture(scope="class")
    def py_summary(self):
        df = rpm.datasets.wine()
        rpm.set_seed(42)
        _r().r("set.seed(42)")
        fit = rpm.prcomp_rob(df)
        return fit.summary()

    @pytest.fixture(scope="class")
    def r_summary(self):
        ro = _r()
        ro.r(
            "library(RobStatTM); set.seed(42); data(wine); "
            "X_pr <- as.matrix(wine[, sapply(wine, is.numeric)]); "
            "rpm_test_pr_fit  <- prcompRob(X_pr); "
            "rpm_test_pr_summ <- summary(rpm_test_pr_fit)"
        )
        return ro.r

    def test_importance_matrix(self, py_summary, r_summary):
        r_imp = np.asarray(r_summary("rpm_test_pr_summ$importance"), dtype=float)
        np.testing.assert_array_equal(py_summary.importance.to_numpy(), r_imp)

    def test_sdev_row(self, py_summary, r_summary):
        r_sd = np.asarray(
            r_summary("rpm_test_pr_summ$importance['Standard deviation', ]"),
            dtype=float,
        ).ravel()
        np.testing.assert_array_equal(py_summary.sdev, r_sd)

    def test_proportion_row(self, py_summary, r_summary):
        r_prop = np.asarray(
            r_summary("rpm_test_pr_summ$importance['Proportion of Variance', ]"),
            dtype=float,
        ).ravel()
        np.testing.assert_array_equal(py_summary.proportion_of_variance, r_prop)

    def test_cumulative_row(self, py_summary, r_summary):
        r_cum = np.asarray(
            r_summary("rpm_test_pr_summ$importance['Cumulative Proportion', ]"),
            dtype=float,
        ).ravel()
        np.testing.assert_array_equal(py_summary.cumulative_proportion, r_cum)

    def test_component_names(self, py_summary, r_summary):
        r_cols = tuple(r_summary("colnames(rpm_test_pr_summ$importance)"))
        assert py_summary.component_names == r_cols

    def test_repr_html_contains_importance(self, py_summary):
        html = py_summary._repr_html_()
        assert "Importance of components" in html


@needs_r
def test_prcomp_rob_summary_works_without_r_fit():
    """summary() depends only on the extracted ``sdev``/component-names,
    so it remains usable even if the raw R fit isn't around (e.g. after
    pickling)."""
    from dataclasses import replace
    df = rpm.datasets.wine()
    rpm.set_seed(42)
    _r().r("set.seed(42)")
    fit = rpm.prcomp_rob(df)
    fit_no = replace(fit, _r_fit=None)
    s = fit_no.summary()
    np.testing.assert_array_equal(
        s.proportion_of_variance, fit.summary().proportion_of_variance
    )
