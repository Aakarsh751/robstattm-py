"""Strict-tier tests for robstatm_py.m_scale vs direct R."""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from tests.conftest import assert_scalar_equal, needs_r


GOLDEN_U = np.array(
    [
        1.2, -0.4, 0.7, 2.1, -1.0, 0.3, 1.8, -2.5, 0.9, 0.0,
        10.0, -10.0, 0.5, -0.3, 1.5, 2.2, -1.7, 0.6, 0.1, -0.8,
    ]
)


class TestInputValidation:
    def test_non_numeric_raises(self):
        with pytest.raises(TypeError):
            rpm.m_scale("nope")  # type: ignore[arg-type]

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            rpm.m_scale(np.array([]))

    def test_bad_delta(self):
        with pytest.raises(ValueError, match="delta"):
            rpm.m_scale(GOLDEN_U, delta=0.0)
        with pytest.raises(ValueError, match="delta"):
            rpm.m_scale(GOLDEN_U, delta=1.5)


@needs_r
class TestStrictTierVsR:
    @pytest.mark.parametrize("family", ["bisquare", "huber"])
    @pytest.mark.parametrize("delta", [0.25, 0.5])
    def test_m_scale_matches_r(self, R, family, delta):
        from robstatm_py._r import r

        ro = r()
        ro.globalenv["u_test"] = GOLDEN_U
        ro.r("library(RobStatTM)")
        py = rpm.m_scale(GOLDEN_U, family=family, delta=delta)
        r_val = R(f'scaleM(u_test, family="{family}", delta={delta})')
        assert_scalar_equal(py, r_val, where=f"family={family} delta={delta}")


@needs_r
def test_returns_native_float():
    assert isinstance(rpm.m_scale(GOLDEN_U), float)


@needs_r
def test_determinism():
    assert rpm.m_scale(GOLDEN_U) == rpm.m_scale(GOLDEN_U)
