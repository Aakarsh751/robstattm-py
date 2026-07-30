"""Strict-tier tests for S3 methods on LmrobMResult (summary/predict/hatvalues).

lmrobM dispatches to summary.lmrobdetMM / predict.lmrob / hatvalues.lmrob,
so the schema and parity story is identical to LmrobdetMMResult — but the
underlying fit is different, so we verify here too.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


@needs_r
class TestMineralLmrobMS3:
    """Summary + (manual) predict + hatvalues for LmrobMResult.

    R does not dispatch ``predict.lmrob`` / ``hatvalues.lmrob`` to lmrobM
    (class is ``c('lmrobM','lmrobdetMM')``, no ``lmrob`` in hierarchy),
    so the wrapper computes them from R primitives:
      predict   = model.matrix(formula, data) %*% coef(fit)
      hatvalues = diag(Q Q') where Q = qr.Q(qr(sqrt(rweights) * X))
    Both verified ``identical()`` to the S3 path on MM fits.
    """

    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrob_m("zinc ~ copper", data=df)

    @pytest.fixture(scope="class")
    def r_ctx(self):
        from robstattm_py._r import r
        ro = r()
        ro.r(
            "library(RobStatTM); data(mineral); "
            "rpm_test_lmm_fit <- lmrobM(zinc ~ copper, data=mineral); "
            "rpm_test_lmm_summ <- summary(rpm_test_lmm_fit); "
            # Manual predict + hatvalues per R primitives
            "rpm_test_lmm_mm <- model.matrix(formula(rpm_test_lmm_fit), "
            "                                 data=mineral); "
            "rpm_test_lmm_pred <- as.numeric(rpm_test_lmm_mm %*% "
            "                                coef(rpm_test_lmm_fit)); "
            "rpm_test_lmm_Q <- qr.Q(qr(sqrt(rpm_test_lmm_fit$rweights) * "
            "                          rpm_test_lmm_mm)); "
            "rpm_test_lmm_hat <- diag(rpm_test_lmm_Q %*% t(rpm_test_lmm_Q))"
        )
        return ro

    def test_summary_coefficients(self, fit, r_ctx, R):
        s = fit.summary()
        r_coefs = np.asarray(R("rpm_test_lmm_summ$coefficients"), dtype=float)
        np.testing.assert_array_equal(s.coefficients_table.to_numpy(), r_coefs)

    def test_summary_cov(self, fit, r_ctx, R):
        s = fit.summary()
        r_cov = np.asarray(R("rpm_test_lmm_summ$cov"), dtype=float)
        np.testing.assert_array_equal(s.cov, r_cov)

    def test_summary_scalars(self, fit, r_ctx, R):
        s = fit.summary()
        assert s.scale == float(R("rpm_test_lmm_summ$scale")[0])
        assert s.sigma == float(R("rpm_test_lmm_summ$sigma")[0])
        assert s.r_squared == float(R("rpm_test_lmm_summ$r.squared")[0])
        assert s.adj_r_squared == float(R("rpm_test_lmm_summ$adj.r.squared")[0])

    def test_predict_in_sample(self, fit, r_ctx, R):
        py = fit.predict()
        r_pred = np.asarray(R("rpm_test_lmm_pred"), dtype=float).ravel()
        np.testing.assert_array_equal(py, r_pred)

    def test_predict_equals_fitted_values(self, fit):
        """Manual predict on the training data should equal the stored fitted values."""
        np.testing.assert_array_equal(fit.predict(), fit.fitted_values)

    def test_predict_newdata(self, fit, r_ctx, R):
        new = pd.DataFrame({"copper": [10.0, 20.0, 30.0]})
        py = fit.predict(new)
        r_new = R(
            "as.numeric(model.matrix("
            "                 delete.response(terms(formula(rpm_test_lmm_fit))), "
            "                 data=data.frame(copper=c(10,20,30))) %*% "
            "           coef(rpm_test_lmm_fit))"
        )
        np.testing.assert_array_equal(py, np.asarray(r_new, dtype=float).ravel())

    def test_hatvalues(self, fit, r_ctx, R):
        py = fit.hatvalues()
        r_hat = np.asarray(R("rpm_test_lmm_hat"), dtype=float).ravel()
        np.testing.assert_array_equal(py, r_hat)

    def test_hatvalues_shape_and_range(self, fit):
        h = fit.hatvalues()
        assert h.shape == (len(rpm.datasets.mineral()),)
        assert (h >= 0).all()


@needs_r
def test_lmrobm_methods_require_data():
    df = rpm.datasets.mineral()
    fit = rpm.lmrob_m("zinc ~ copper", data=df)
    from dataclasses import replace
    fit_nodata = replace(fit, _data=None)
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.summary()
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.predict()
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.hatvalues()
