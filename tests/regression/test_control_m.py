"""Tests for ``lmrobm_control`` + integration with ``lmrob_m(control=...)``."""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from robstatm_py._r import r as _r

try:
    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


class TestLmrobMControl:
    """Pure-Python dataclass construction (no R required)."""

    def test_defaults(self):
        c = rpm.lmrobm_control()
        assert c.bb == 0.5
        assert c.efficiency == 0.99
        assert c.family == "opt"
        assert c.max_it == 100

    def test_kwargs_override(self):
        c = rpm.lmrobm_control(efficiency=0.85, family="bisquare", bb=0.55)
        assert c.efficiency == 0.85
        assert c.family == "bisquare"
        assert c.bb == 0.55

    def test_unknown_kwarg_raises(self):
        with pytest.raises(TypeError, match="unknown lmrobm_control kwargs"):
            rpm.lmrobm_control(not_a_field=42)

    def test_frozen(self):
        c = rpm.lmrobm_control()
        with pytest.raises(Exception):
            c.bb = 0.7  # frozen dataclass


@needs_r
class TestLmrobMWithControl:
    """``lmrob_m(control=ctrl)`` produces the same coefficients as the
    equivalent direct R call."""

    @pytest.fixture(scope="class")
    def df(self):
        return rpm.datasets.mineral()

    def test_control_object_round_trip(self, df):
        ctrl = rpm.lmrobm_control(efficiency=0.95, family="bisquare")
        fit = rpm.lmrob_m("zinc ~ copper", data=df, control=ctrl)
        # Compare to direct R call
        ro = _r()
        ro.r("""
            library(RobStatTM); data(mineral)
            rpm_test_ctrl <- lmrobM.control(efficiency=0.95, family='bisquare')
            rpm_test_fit  <- lmrobM(zinc ~ copper, data=mineral,
                                    control=rpm_test_ctrl)
        """)
        r_coef = np.asarray(ro.r("coef(rpm_test_fit)"), dtype=float)
        np.testing.assert_array_equal(fit.coefficients, r_coef)
        ro.r("rm(rpm_test_ctrl, rpm_test_fit)")

    def test_control_cannot_mix_with_kwargs(self, df):
        ctrl = rpm.lmrobm_control(efficiency=0.95)
        with pytest.raises(TypeError, match="Cannot mix"):
            rpm.lmrob_m("zinc ~ copper", data=df, control=ctrl, family="bisquare")

    def test_control_wrong_type_raises(self, df):
        with pytest.raises(TypeError, match="LmrobMControl"):
            rpm.lmrob_m(
                "zinc ~ copper", data=df,
                control=rpm.lmrobdet_control(),  # wrong control type
            )
