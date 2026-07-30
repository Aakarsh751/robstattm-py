"""Strict-tier tests for S3 methods on LmrobdetDCMLResult."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


@needs_r
class TestMineralDCMLS3:
    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_dcml("zinc ~ copper", data=df)

    @pytest.fixture(scope="class")
    def r_ctx(self):
        from robstattm_py._r import r
        ro = r()
        ro.r(
            "library(RobStatTM); data(mineral); "
            "rpm_test_dcml_fit <- lmrobdetDCML(zinc ~ copper, data=mineral); "
            "rpm_test_dcml_summ <- summary(rpm_test_dcml_fit); "
            "rpm_test_dcml_pred <- predict(rpm_test_dcml_fit); "
            "rpm_test_dcml_hat <- hatvalues(rpm_test_dcml_fit)"
        )
        return ro

    def test_summary_coefficients(self, fit, r_ctx, R):
        s = fit.summary()
        r_coefs = np.asarray(R("rpm_test_dcml_summ$coefficients"), dtype=float)
        np.testing.assert_array_equal(s.coefficients_table.to_numpy(), r_coefs)

    def test_summary_cov(self, fit, r_ctx, R):
        s = fit.summary()
        r_cov = np.asarray(R("rpm_test_dcml_summ$cov"), dtype=float)
        np.testing.assert_array_equal(s.cov, r_cov)

    def test_summary_scalars(self, fit, r_ctx, R):
        s = fit.summary()
        assert s.scale == float(R("rpm_test_dcml_summ$scale")[0])
        assert s.sigma == float(R("rpm_test_dcml_summ$sigma")[0])
        # DCML summary lacks r.squared / adj.r.squared (verified vs R).
        # The wrapper exposes them as None for DCML.
        assert s.r_squared is None
        assert s.adj_r_squared is None

    def test_predict_default(self, fit, r_ctx, R):
        py = fit.predict()
        r_pred = np.asarray(R("rpm_test_dcml_pred"), dtype=float).ravel()
        np.testing.assert_array_equal(py, r_pred)

    def test_predict_newdata(self, fit, r_ctx, R):
        new = pd.DataFrame({"copper": [10.0, 20.0, 30.0]})
        py = fit.predict(new)
        r_new = R(
            "predict(rpm_test_dcml_fit, newdata=data.frame(copper=c(10,20,30)))"
        )
        np.testing.assert_array_equal(py, np.asarray(r_new, dtype=float).ravel())

    def test_hatvalues(self, fit, r_ctx, R):
        py = fit.hatvalues()
        r_hat = np.asarray(R("rpm_test_dcml_hat"), dtype=float).ravel()
        np.testing.assert_array_equal(py, r_hat)


@needs_r
class TestDCMLRSquaredClassic:
    """`.r_squared_classic()` is the documented workaround for R not
    populating ``$r.squared`` on DCML fits."""

    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_dcml("zinc ~ copper", data=df)

    def test_r_squared_classic_matches_r(self, fit, R):
        """Strict-tier vs the R formula
        ``1 - sum(residuals^2) / sum((y - mean(y))^2)``."""
        from robstattm_py._r import r as _r
        ro = _r()
        ro.r(
            "library(RobStatTM); data(mineral); "
            "rpm_test_dcml_r2_fit <- lmrobdetDCML(zinc ~ copper, data=mineral); "
            "rpm_test_dcml_r2_y   <- mineral$zinc; "
            "rpm_test_dcml_r2     <- 1 - sum(rpm_test_dcml_r2_fit$residuals^2) "
            "                          / sum((rpm_test_dcml_r2_y - "
            "                                 mean(rpm_test_dcml_r2_y))^2)"
        )
        try:
            r_val = float(R("rpm_test_dcml_r2")[0])
            py_val = fit.r_squared_classic()
            assert py_val == r_val
        finally:
            ro.r(
                "for (v in c('rpm_test_dcml_r2_fit','rpm_test_dcml_r2_y',"
                "'rpm_test_dcml_r2')) if (exists(v)) rm(list=v)"
            )

    def test_summary_r_squared_still_none(self, fit):
        """Confirm R-parity: ``.summary().r_squared`` stays ``None`` for DCML.

        The classical R² is only available via the dedicated method.
        """
        assert fit.summary().r_squared is None
        assert fit.summary().adj_r_squared is None


@needs_r
def test_dcml_methods_require_data():
    df = rpm.datasets.mineral()
    fit = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
    from dataclasses import replace
    fit_nodata = replace(fit, _data=None)
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.summary()
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.hatvalues()
    with pytest.raises(ValueError, match="original data"):
        fit_nodata.predict()
