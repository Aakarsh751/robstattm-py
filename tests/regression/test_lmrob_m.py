"""Strict-tier tests for lmrob_m vs direct R."""
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
            rpm.lmrob_m(1, data=pd.DataFrame({"a": [1]}))  # type: ignore[arg-type]

    def test_non_df_data(self):
        with pytest.raises(TypeError):
            rpm.lmrob_m("y ~ x", data=[[1]])  # type: ignore[arg-type]


@needs_r
class TestMineralVsR:
    @pytest.fixture(autouse=True)
    def _r_setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral); "
             "set.seed(42L); m_check <- lmrobM(zinc ~ copper, data=mineral)")
        yield
        ro.r("rm(m_check)")

    @pytest.fixture
    def py(self):
        set_seed(42)
        return rpm.lmrob_m("zinc ~ copper", data=rpm.datasets.mineral())

    def test_coefficients(self, py, R):
        np.testing.assert_array_equal(
            py.coefficients, np.asarray(R("coef(m_check)"), dtype=float)
        )

    def test_scale(self, py, R):
        assert py.scale == float(R("m_check$scale")[0])

    def test_r_squared(self, py, R):
        assert py.r_squared == float(R("m_check$r.squared")[0])

    def test_residuals(self, py, R):
        np.testing.assert_array_equal(
            py.residuals, np.asarray(R("m_check$residuals"), dtype=float)
        )

    def test_fitted_values(self, py, R):
        np.testing.assert_array_equal(
            py.fitted_values, np.asarray(R("m_check$fitted.values"), dtype=float)
        )

    def test_rweights(self, py, R):
        np.testing.assert_array_equal(
            py.rweights, np.asarray(R("m_check$rweights"), dtype=float)
        )

    def test_cov(self, py, R):
        np.testing.assert_array_equal(
            py.cov, np.asarray(R("m_check$cov"), dtype=float)
        )

    def test_iter(self, py, R):
        assert py.iter == int(R("m_check$iter")[0])

    def test_converged(self, py, R):
        assert py.converged == bool(R("m_check$converged")[0])


@needs_r
def test_lmrob_m_repr():
    set_seed(42)
    fit = rpm.lmrob_m("zinc ~ copper", data=rpm.datasets.mineral())
    assert "LmrobMResult" in repr(fit)
