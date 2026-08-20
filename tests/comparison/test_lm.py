"""Strict-tier tests for the classical ``lm`` comparison wrapper vs direct R."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from robstattm_py.regression._formula import df_with_r_names
from tests.conftest import needs_r


class TestValidation:
    def test_non_str_formula(self):
        with pytest.raises(TypeError):
            rpm.lm(1, data=pd.DataFrame({"a": [1]}))  # type: ignore[arg-type]

    def test_non_df_data(self):
        with pytest.raises(TypeError):
            rpm.lm("y ~ x", data=[[1]])  # type: ignore[arg-type]


@needs_r
class TestMineralVsR:
    @pytest.fixture(autouse=True)
    def _r_setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.globalenv["cmp_d"] = df_with_r_names(rpm.datasets.mineral())
        ro.r("cmp_lm <- lm(zinc ~ copper, data=cmp_d); cmp_s <- summary(cmp_lm)")
        yield
        ro.r("rm(cmp_d, cmp_lm, cmp_s)")

    @pytest.fixture
    def py(self):
        return rpm.lm("zinc ~ copper", data=rpm.datasets.mineral())

    def test_coefficients(self, py, R):
        np.testing.assert_allclose(
            py.coefficients, np.asarray(R("coef(cmp_lm)"), dtype=float)
        )

    def test_coef_names(self, py, R):
        assert list(py.coef_names) == [str(n) for n in R("names(coef(cmp_lm))")]

    def test_residuals(self, py, R):
        np.testing.assert_allclose(
            py.residuals, np.asarray(R("residuals(cmp_lm)"), dtype=float)
        )

    def test_fitted_values(self, py, R):
        np.testing.assert_allclose(
            py.fitted_values, np.asarray(R("fitted(cmp_lm)"), dtype=float)
        )

    def test_rank_and_df(self, py, R):
        assert py.rank == int(R("cmp_lm$rank")[0])
        assert py.df_residual == int(R("cmp_lm$df.residual")[0])

    def test_summary_table(self, py, R):
        s = py.summary()
        np.testing.assert_allclose(
            s.coefficients_table.to_numpy(),
            np.asarray(R("cmp_s$coefficients"), dtype=float),
        )
        assert list(s.coefficients_table.columns) == [
            "Estimate", "Std. Error", "t value", "Pr(>|t|)"
        ]

    def test_summary_scalars(self, py, R):
        s = py.summary()
        assert s.sigma == pytest.approx(float(R("cmp_s$sigma")[0]))
        assert s.r_squared == pytest.approx(float(R("cmp_s$r.squared")[0]))
        assert s.adj_r_squared == pytest.approx(float(R("cmp_s$adj.r.squared")[0]))
        assert s.fstatistic[0] == pytest.approx(float(R("cmp_s$fstatistic[1]")[0]))

    def test_predict_in_sample(self, py, R):
        np.testing.assert_allclose(py.predict(), py.fitted_values)

    def test_predict_se(self, py, R):
        p = py.predict(se_fit=True)
        R("cmp_p <- predict(cmp_lm, se.fit=TRUE)")
        np.testing.assert_allclose(p.fit, np.asarray(R("cmp_p$fit"), dtype=float))
        np.testing.assert_allclose(
            p.se_fit, np.asarray(R("cmp_p$se.fit"), dtype=float)
        )

    def test_vcov(self, py, R):
        np.testing.assert_allclose(
            py.vcov().to_numpy(),
            np.asarray(R("as.matrix(vcov(cmp_lm))"), dtype=float),
        )

    def test_confint(self, py, R):
        np.testing.assert_allclose(
            py.confint().to_numpy(),
            np.asarray(R("as.matrix(confint(cmp_lm))"), dtype=float),
        )

    def test_accessors(self, py):
        assert isinstance(py.coef(), pd.Series)
        assert isinstance(py.coef_df(), pd.Series)
        assert isinstance(py.resid(), pd.Series)
        assert isinstance(py.fitted(), pd.Series)
        assert "coefficients" in py.to_dict()
        assert py.to_r() is not None

    def test_published_vignette_numbers(self, py):
        # The mineral LS fit from the fit.models RobStatTM vignette.
        d = dict(py.coef().round(5))
        assert d["(Intercept)"] == pytest.approx(7.96063, abs=1e-4)
        assert d["copper"] == pytest.approx(0.13457, abs=1e-4)
        assert py.summary().r_squared == pytest.approx(0.4746, abs=1e-3)
