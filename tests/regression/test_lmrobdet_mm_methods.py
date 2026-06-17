"""Strict-tier tests for the S3-as-dataclass methods on LmrobdetMMResult.

Covers ``.summary()``, ``.predict()``, ``.hatvalues()`` — each against R's
own S3 dispatch (``summary.lmrobdetMM``, ``predict.lmrob``, ``hatvalues.lmrob``).
All assertions use exact equality.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm
from tests.conftest import needs_r


@needs_r
class TestMineralS3Methods:
    """Methods on a mineral-data lmrobdetMM fit, strict-tier vs R."""

    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_mm("zinc ~ copper", data=df)

    @pytest.fixture(scope="class")
    def r_fit(self):
        from robstatm_py._r import r

        ro = r()
        ro.r(
            "library(RobStatTM); data(mineral); "
            "rpm_test_fit <- lmrobdetMM(zinc ~ copper, data = mineral); "
            "rpm_test_summ <- summary(rpm_test_fit); "
            "rpm_test_hat  <- hatvalues(rpm_test_fit); "
            "rpm_test_pred <- predict(rpm_test_fit); "
            "rpm_test_pred_se <- predict(rpm_test_fit, se.fit=TRUE)"
        )
        return ro

    # --- summary() ---
    def test_summary_coefficients_table(self, fit, r_fit):
        s = fit.summary()
        r_coefs = np.asarray(r_fit.r("rpm_test_summ$coefficients"), dtype=float)
        np.testing.assert_array_equal(s.coefficients_table.to_numpy(), r_coefs)

    def test_summary_table_columns_and_index(self, fit):
        s = fit.summary()
        assert list(s.coefficients_table.columns) == [
            "Estimate", "Std. Error", "t value", "Pr(>|t|)",
        ]
        assert list(s.coefficients_table.index) == list(fit.coef_names)

    def test_summary_cov_matrix(self, fit, r_fit):
        s = fit.summary()
        r_cov = np.asarray(r_fit.r("rpm_test_summ$cov"), dtype=float)
        np.testing.assert_array_equal(s.cov, r_cov)

    def test_summary_residuals(self, fit, r_fit):
        s = fit.summary()
        r_res = np.asarray(r_fit.r("rpm_test_summ$residuals"), dtype=float).ravel()
        np.testing.assert_array_equal(s.residuals, r_res)

    def test_summary_scalar_fields(self, fit, r_fit):
        s = fit.summary()
        assert s.scale == float(r_fit.r("rpm_test_summ$scale")[0])
        assert s.sigma == float(r_fit.r("rpm_test_summ$sigma")[0])
        assert s.r_squared == float(r_fit.r("rpm_test_summ$r.squared")[0])
        assert s.adj_r_squared == float(r_fit.r("rpm_test_summ$adj.r.squared")[0])
        assert s.iter == int(r_fit.r("rpm_test_summ$iter")[0])
        assert s.converged == bool(r_fit.r("rpm_test_summ$converged")[0])

    def test_summary_df(self, fit, r_fit):
        s = fit.summary()
        r_df = tuple(int(x) for x in np.asarray(r_fit.r("rpm_test_summ$df"), dtype=int).ravel())
        assert s.df == r_df

    def test_summary_repr_smoke(self, fit):
        s = fit.summary()
        text = repr(s)
        assert "zinc ~ copper" in text
        assert "Coefficients" in text

    # --- predict() ---
    def test_predict_default(self, fit, r_fit):
        py_pred = fit.predict()
        r_pred = np.asarray(r_fit.r("rpm_test_pred"), dtype=float).ravel()
        np.testing.assert_array_equal(py_pred, r_pred)

    def test_predict_equals_fitted_values(self, fit):
        py_pred = fit.predict()
        np.testing.assert_array_equal(py_pred, fit.fitted_values)

    def test_predict_newdata(self, fit, r_fit):
        new = pd.DataFrame({"copper": [10.0, 20.0, 30.0]})
        py_pred = fit.predict(new)
        r_new = r_fit.r(
            "predict(rpm_test_fit, newdata=data.frame(copper=c(10,20,30)))"
        )
        r_pred = np.asarray(r_new, dtype=float).ravel()
        np.testing.assert_array_equal(py_pred, r_pred)

    def test_predict_se_fit(self, fit, r_fit):
        py = fit.predict(se_fit=True)
        assert isinstance(py, rpm.LmrobdetMMPrediction)
        r_fit_arr = np.asarray(r_fit.r("rpm_test_pred_se$fit"), dtype=float).ravel()
        r_se_arr = np.asarray(r_fit.r("rpm_test_pred_se$se.fit"), dtype=float).ravel()
        np.testing.assert_array_equal(py.fit, r_fit_arr)
        np.testing.assert_array_equal(py.se_fit, r_se_arr)
        assert py.df == int(r_fit.r("rpm_test_pred_se$df")[0])

    # --- hatvalues() ---
    def test_hatvalues(self, fit, r_fit):
        py_hat = fit.hatvalues()
        r_hat = np.asarray(r_fit.r("rpm_test_hat"), dtype=float).ravel()
        np.testing.assert_array_equal(py_hat, r_hat)

    def test_hatvalues_shape_and_range(self, fit):
        py_hat = fit.hatvalues()
        df = rpm.datasets.mineral()
        assert py_hat.shape == (len(df),)
        # Leverages live in [0, 1] (sum may exceed 1 for robust definitions
        # but each individual value should be non-negative).
        assert (py_hat >= 0).all()


@needs_r
class TestCustomControlS3Methods:
    """Regression test for the control-threading bug (2026-06-14).

    Before the fix, ``.summary()`` / ``.predict()`` / ``.hatvalues()`` refit the
    model with *default* control, so a fit built with a non-default control
    silently reported numbers for the wrong (default) model. These tests fit
    with ``family="opt", efficiency=0.80`` and assert the S3 methods match
    R's own dispatch on a fit built with the *same* control — strict tier.
    """

    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        ctrl = rpm.lmrobdet_control(family="opt", efficiency=0.80)
        return rpm.lmrobdet_mm("zinc ~ copper", data=df, control=ctrl)

    @pytest.fixture(scope="class")
    def r_fit(self):
        from robstatm_py._r import r

        ro = r()
        ro.r(
            "library(RobStatTM); data(mineral); "
            "rpm_cc_ctrl <- lmrobdet.control(family='opt', efficiency=0.80); "
            "rpm_cc_fit  <- lmrobdetMM(zinc ~ copper, data=mineral, control=rpm_cc_ctrl); "
            "rpm_cc_summ <- summary(rpm_cc_fit); "
            "rpm_cc_hat  <- hatvalues(rpm_cc_fit); "
            "rpm_cc_pred <- predict(rpm_cc_fit)"
        )
        return ro

    def test_fit_is_not_default(self):
        """Guard: the custom control must actually change the fit, else the
        test would pass vacuously even with the bug present."""
        df = rpm.datasets.mineral()
        default_fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
        ctrl = rpm.lmrobdet_control(family="opt", efficiency=0.80)
        custom_fit = rpm.lmrobdet_mm("zinc ~ copper", data=df, control=ctrl)
        assert not np.array_equal(default_fit.coefficients, custom_fit.coefficients)

    def test_summary_coefficients_match_r(self, fit, r_fit):
        s = fit.summary()
        r_coefs = np.asarray(r_fit.r("rpm_cc_summ$coefficients"), dtype=float)
        np.testing.assert_array_equal(s.coefficients_table.to_numpy(), r_coefs)

    def test_summary_cov_matches_r(self, fit, r_fit):
        s = fit.summary()
        r_cov = np.asarray(r_fit.r("rpm_cc_summ$cov"), dtype=float)
        np.testing.assert_array_equal(s.cov, r_cov)

    def test_summary_scale_matches_r_and_fit(self, fit, r_fit):
        s = fit.summary()
        r_scale = float(r_fit.r("rpm_cc_summ$scale")[0])
        assert s.scale == r_scale
        # Internal consistency: the summary's scale equals the fit's own scale.
        assert s.scale == fit.scale

    def test_predict_matches_r(self, fit, r_fit):
        py_pred = fit.predict()
        r_pred = np.asarray(r_fit.r("rpm_cc_pred"), dtype=float).ravel()
        np.testing.assert_array_equal(py_pred, r_pred)
        np.testing.assert_array_equal(py_pred, fit.fitted_values)

    def test_hatvalues_match_r(self, fit, r_fit):
        py_hat = fit.hatvalues()
        r_hat = np.asarray(r_fit.r("rpm_cc_hat"), dtype=float).ravel()
        np.testing.assert_array_equal(py_hat, r_hat)


@needs_r
def test_methods_require_data():
    """A fit without _data should raise on summary/predict/hatvalues."""
    df = rpm.datasets.mineral()
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    # Simulate loss of data by constructing a copy without it
    from dataclasses import replace

    fit_nodata = replace(fit, _data=None)
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.summary()
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.hatvalues()
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.predict()
