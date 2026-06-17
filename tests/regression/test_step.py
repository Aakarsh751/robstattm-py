"""Strict-tier tests for step_lmrobdet."""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_r


class TestValidation:
    def test_non_fit_raises(self):
        with pytest.raises(TypeError):
            rpm.step_lmrobdet("not a fit")  # type: ignore[arg-type]


@needs_r
class TestMineralVsR:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral); "
             "set.seed(42L); f_r <- lmrobdetMM(zinc ~ copper, data=mineral); "
             "set.seed(42L); s_r <- step.lmrobdetMM(f_r, trace=FALSE)")
        set_seed(42)
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
        set_seed(42)
        return rpm.step_lmrobdet(fit)

    def test_anova_rfpe_matches_r(self, setup, R):
        py = setup
        r_rfpe = np.asarray(R("s_r$anova$RFPE"), dtype=float)
        np.testing.assert_array_equal(py.anova_rfpe, r_rfpe)

    def test_coefficients(self, setup, R):
        py = setup
        r_coef = np.asarray(R("coef(s_r)"), dtype=float)
        np.testing.assert_array_equal(py.coefficients, r_coef)

    def test_scale(self, setup, R):
        py = setup
        assert py.scale == float(R("s_r$scale")[0])


@needs_r
def test_repr():
    set_seed(42)
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
    set_seed(42)
    sfit = rpm.step_lmrobdet(fit)
    assert "StepResult" in repr(sfit)
