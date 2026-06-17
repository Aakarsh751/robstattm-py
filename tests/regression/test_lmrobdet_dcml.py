"""Strict-tier tests for lmrobdet_dcml vs direct R."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_r


class TestValidation:
    def test_non_str_formula(self):
        with pytest.raises(TypeError):
            rpm.lmrobdet_dcml(1, data=pd.DataFrame({"a": [1]}))  # type: ignore[arg-type]

    def test_non_df_data(self):
        with pytest.raises(TypeError):
            rpm.lmrobdet_dcml("y ~ x", data=[[1]])  # type: ignore[arg-type]

    def test_empty_df(self):
        with pytest.raises(ValueError):
            rpm.lmrobdet_dcml("y ~ x", data=pd.DataFrame())


@needs_r
class TestMineralVsR:
    @pytest.fixture(autouse=True)
    def _r_setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral); "
             "set.seed(42L); d_check <- lmrobdetDCML(zinc ~ copper, data=mineral)")
        yield
        ro.r("rm(d_check)")

    @pytest.fixture
    def py(self):
        set_seed(42)
        return rpm.lmrobdet_dcml("zinc ~ copper", data=rpm.datasets.mineral())

    def test_coefficients(self, py, R):
        np.testing.assert_array_equal(
            py.coefficients, np.asarray(R("coef(d_check)"), dtype=float)
        )

    def test_scale(self, py, R):
        assert py.scale == float(R("d_check$scale")[0])

    def test_t0(self, py, R):
        assert py.t0 == float(R("d_check$t0")[0])

    def test_residuals(self, py, R):
        np.testing.assert_array_equal(
            py.residuals, np.asarray(R("d_check$residuals"), dtype=float)
        )

    def test_fitted_values(self, py, R):
        np.testing.assert_array_equal(
            py.fitted_values, np.asarray(R("d_check$fitted.values"), dtype=float)
        )

    def test_cov(self, py, R):
        np.testing.assert_array_equal(
            py.cov, np.asarray(R("d_check$cov"), dtype=float)
        )

    def test_rweights_mm(self, py, R):
        np.testing.assert_array_equal(
            py.rweights_mm, np.asarray(R("d_check$rweightsMM"), dtype=float)
        )

    def test_iter(self, py, R):
        assert py.iter == int(R("d_check$iter")[0])

    def test_converged(self, py, R):
        assert py.converged == bool(R("d_check$converged")[0])

    def test_rank(self, py, R):
        assert py.rank == int(R("d_check$rank")[0])

    def test_df_residual(self, py, R):
        assert py.df_residual == int(R("d_check$df.residual")[0])

    def test_coef_names(self, py):
        assert py.coef_names == ("(Intercept)", "copper")


@needs_r
def test_repr():
    set_seed(42)
    fit = rpm.lmrobdet_dcml("zinc ~ copper", data=rpm.datasets.mineral())
    s = repr(fit)
    assert "LmrobdetDCMLResult" in s
    assert "zinc ~ copper" in s
