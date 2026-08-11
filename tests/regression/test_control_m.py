"""Tests for ``lmrobm_control`` + integration with ``lmrob_m(control=...)``."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import numpy as np
import pytest

import robstattm_py as rpm
from robstattm_py._r import r as _r
from robstattm_py.regression.control_m import _R_KEY_MAP, _control_m_to_r

try:
    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


def _public_fields_m():
    return [f for f in fields(rpm.LmrobMControl) if not f.name.startswith("_")]


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
        # FrozenInstanceError specifically — a blind `Exception` would also pass
        # if the assignment failed for some unrelated reason.
        with pytest.raises(FrozenInstanceError):
            c.bb = 0.7  # frozen dataclass


@needs_r
class TestLmrobMControlVsRFormals:
    """Guard the control *surface* against drift from R's ``lmrobM.control``.

    Parallels ``tests/regression/test_control.py`` for ``lmrobdet.control`` — it
    is the D-022-class safety net: it would flag a Python default or argument
    name that silently diverged from R (which ``_control_m_to_r``'s
    skip-when-equal-default logic relies on being correct).
    """

    def test_field_count_matches_r_formals(self):
        py_fields = _public_fields_m()
        ro = _r()
        r_formals = list(ro.r("names(formals(RobStatTM::lmrobM.control))"))
        assert len(py_fields) == len(r_formals), (
            f"field-count drift: python={len(py_fields)} "
            f"({[f.name for f in py_fields]}) r={len(r_formals)} ({r_formals})"
        )

    def test_defaults_match_r(self):
        default = rpm.lmrobm_control()
        ro = _r()
        r_names = set(ro.r("names(RobStatTM::lmrobM.control())"))
        for f in _public_fields_m():
            py_val = getattr(default, f.name)
            if py_val is None:
                continue  # tuning.psi/chi derived by R; efficiency is input-only
            r_name = _R_KEY_MAP.get(f.name, f.name)
            if r_name not in r_names:
                continue
            r_raw = ro.r(f'RobStatTM::lmrobM.control()[["{r_name}"]]')
            if isinstance(py_val, bool):
                assert bool(r_raw[0]) == py_val, f"{f.name}: py={py_val} r={bool(r_raw[0])}"
            elif isinstance(py_val, (int, float)):
                assert float(r_raw[0]) == float(py_val), (
                    f"{f.name} ({r_name}): py={py_val} r={float(r_raw[0])}"
                )
            else:
                assert str(r_raw[0]) == str(py_val), f"{f.name}: py={py_val} r={r_raw[0]}"

    def test_nondefault_keys_roundtrip_into_r(self):
        """Non-headline keys must reach R under the right argument names."""
        from robstattm_py._r import rx2

        ctrl = rpm.lmrobm_control(
            efficiency=0.85, max_it=42, rel_tol=1e-8,
            mscale_tol=1e-8, mscale_maxit=33,
        )
        r_list = _control_m_to_r(ctrl)  # must not raise
        assert int(rx2(r_list, "max.it")[0]) == 42
        assert float(rx2(r_list, "rel.tol")[0]) == 1e-8
        assert float(rx2(r_list, "mscale_tol")[0]) == 1e-8
        assert int(rx2(r_list, "mscale_maxit")[0]) == 33


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
