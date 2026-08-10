"""Strict-tier tests for ``lmrobdet_control`` ⟷ R ``lmrobdet.control``.

These guard the *control surface* itself (not just the headline knobs):

* the dataclass field set must not drift from R's formals;
* every fixed default must equal R's default — this is the guard that catches a
  wrong dataclass default (it would have flagged ``refine_s_py = 0`` against
  R's ``refine.S.py = 1e-7``);
* the non-headline keys (``psc_keep``, ``mscale_tol``, ``py_maxit``,
  ``refine_s_py`` …) must round-trip into R under the correct argument names —
  previously these paths were never exercised by any test.
"""
from __future__ import annotations

from dataclasses import fields

import robstattm_py as rpm
from robstattm_py.regression.control import _R_KEY_MAP, _control_to_r
from tests.conftest import needs_r


def _public_fields():
    return [f for f in fields(rpm.LmrobdetControl) if not f.name.startswith("_")]


@needs_r
def test_field_count_matches_r_formals(R):
    """Dataclass field count must match ``formals(lmrobdet.control)`` — catches
    upstream API drift (a key added/removed in RobStatTM)."""
    py_fields = _public_fields()
    r_formals = list(R("names(formals(RobStatTM::lmrobdet.control))"))
    assert len(py_fields) == len(r_formals), (
        f"field-count drift: python={len(py_fields)} ({[f.name for f in py_fields]}) "
        f"r={len(r_formals)} ({r_formals})"
    )


@needs_r
def test_defaults_match_r(R):
    """Every fixed dataclass default must equal R's resolved default.

    ``lmrobdet.control()`` with no args returns every key filled with its R
    default; we compare field-by-field. ``None`` defaults (tuning.psi/chi) are
    skipped because R *computes* those from efficiency/bb.
    """
    default = rpm.LmrobdetControl()
    r_names = set(R("names(RobStatTM::lmrobdet.control())"))
    for f in _public_fields():
        py_val = getattr(default, f.name)
        if py_val is None:
            continue  # R derives tuning.psi / tuning.chi; not a fixed default
        r_name = _R_KEY_MAP.get(f.name, f.name)
        if r_name not in r_names:
            continue
        r_raw = R(f'RobStatTM::lmrobdet.control()[["{r_name}"]]')
        if isinstance(py_val, bool):
            assert bool(r_raw[0]) == py_val, f"{f.name}: py={py_val} r={bool(r_raw[0])}"
        elif isinstance(py_val, (int, float)):
            assert float(r_raw[0]) == float(py_val), (
                f"{f.name} ({r_name}): py={py_val} r={float(r_raw[0])}"
            )
        else:  # str
            assert str(r_raw[0]) == str(py_val), f"{f.name}: py={py_val} r={r_raw[0]}"


@needs_r
def test_refine_s_py_is_float_tolerance():
    """Regression guard for the int-vs-float default bug: ``refine_s_py`` is R's
    ``refine.S.py`` *tolerance* (1e-7), not an iteration count."""
    ctrl = rpm.LmrobdetControl()
    assert isinstance(ctrl.refine_s_py, float)
    assert ctrl.refine_s_py == 1e-7


@needs_r
def test_nondefault_keys_roundtrip_into_r():
    """Non-headline keys must reach R under the right argument names.

    If a key name were wrong (e.g. ``psc_keep`` vs a dotted spelling), R would
    raise "unused argument" and ``_control_to_r`` would blow up; if it were
    dropped, the returned list would still hold R's default. So: build it
    (must not raise) and read the changed values back.
    """
    from robstattm_py._r import rx2

    ctrl = rpm.lmrobdet_control(
        efficiency=0.85,
        mscale_tol=1e-8,
        py_maxit=15,
        refine_s_py=1e-6,
        psc_keep=0.4,
    )
    r_list = _control_to_r(ctrl)  # must not raise

    assert float(rx2(r_list, "mscale_tol")[0]) == 1e-8
    assert int(rx2(r_list, "py_maxit")[0]) == 15
    assert float(rx2(r_list, "refine.S.py")[0]) == 1e-6
    assert float(rx2(r_list, "psc_keep")[0]) == 0.4


@needs_r
def test_nondefault_control_changes_the_fit():
    """End-to-end: a control with a non-headline key set still matches R's own
    fit built with the same control (strict tier)."""
    import numpy as np

    from robstattm_py._r import r

    df = rpm.datasets.mineral()
    ctrl = rpm.lmrobdet_control(efficiency=0.85, py_maxit=15, mscale_tol=1e-8)
    py = rpm.lmrobdet_mm("zinc ~ copper", data=df, control=ctrl)

    ro = r()
    ro.r(
        "library(RobStatTM); data(mineral); "
        "rpm_ctrl_test <- lmrobdet.control(efficiency=0.85, py_maxit=15, mscale_tol=1e-8)"
    )
    try:
        r_coef = np.asarray(
            ro.r(
                "coef(lmrobdetMM(zinc ~ copper, data=mineral, control=rpm_ctrl_test))"
            ),
            dtype=float,
        )
    finally:
        ro.r("if (exists('rpm_ctrl_test')) rm(rpm_ctrl_test)")
    np.testing.assert_array_equal(py.coefficients, r_coef)
