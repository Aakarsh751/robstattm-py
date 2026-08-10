"""Strict-tier tests for the ψ-family infrastructure."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r

U_GRID = np.array([-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0])
SCALAR_FAMILIES = ["bisquare", "huber"]
VECTOR_FAMILIES = ["mopt", "opt", "moptv0", "optv0"]
ALL_FAMILIES = SCALAR_FAMILIES + VECTOR_FAMILIES


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

def test_efficiency_out_of_range():
    with pytest.raises(ValueError):
        rpm.psi.bisquare(0.0)
    with pytest.raises(ValueError):
        rpm.psi.bisquare(1.0)


# ---------------------------------------------------------------------------
# Tuning constants match R bit-for-bit
# ---------------------------------------------------------------------------

@needs_r
@pytest.mark.parametrize("e", [0.85, 0.90, 0.95])
@pytest.mark.parametrize("family", SCALAR_FAMILIES)
def test_scalar_tuning_matches_r(R, family, e):
    py_cc = getattr(rpm.psi, family)(e)
    r_cc = float(R(f"RobStatTM::{family}({e})")[0])
    assert py_cc == r_cc, f"{family}({e}): py={py_cc!r} r={r_cc!r}"


@needs_r
@pytest.mark.parametrize("e", [0.85, 0.90, 0.95])
@pytest.mark.parametrize("family", VECTOR_FAMILIES)
def test_vector_tuning_matches_r(R, family, e):
    py_cc = np.asarray(getattr(rpm.psi, family)(e), dtype=float).ravel()
    r_cc = np.asarray(R(f"RobStatTM::{family}({e})"), dtype=float).ravel()
    np.testing.assert_array_equal(py_cc, r_cc, err_msg=f"{family}({e})")


# ---------------------------------------------------------------------------
# rho / rhoprime / rhoprime2 match R bit-for-bit
# ---------------------------------------------------------------------------

@needs_r
@pytest.mark.parametrize("family", ALL_FAMILIES)
def test_rho_matches_r(R, family):
    from robstattm_py._r import r

    ro = r()
    ro.globalenv["u_test"] = U_GRID
    ro.r("library(RobStatTM)")
    cc = getattr(rpm.psi, family)(0.95)
    ro.globalenv["cc_test"] = np.atleast_1d(cc).astype(float)
    py = rpm.psi.rho(U_GRID, family=family, cc=cc)
    r_val = np.asarray(
        R(f'RobStatTM::rho(u_test, family="{family}", cc=cc_test)'), dtype=float
    )
    np.testing.assert_array_equal(py, r_val, err_msg=f"rho/{family}")


@needs_r
@pytest.mark.parametrize("family", ALL_FAMILIES)
def test_rhoprime_matches_r(R, family):
    from robstattm_py._r import r

    ro = r()
    ro.globalenv["u_test"] = U_GRID
    ro.r("library(RobStatTM)")
    cc = getattr(rpm.psi, family)(0.95)
    ro.globalenv["cc_test"] = np.atleast_1d(cc).astype(float)
    py = rpm.psi.rhoprime(U_GRID, family=family, cc=cc)
    r_val = np.asarray(
        R(f'RobStatTM::rhoprime(u_test, family="{family}", cc=cc_test)'), dtype=float
    )
    np.testing.assert_array_equal(py, r_val, err_msg=f"rhoprime/{family}")


@needs_r
@pytest.mark.parametrize("family", ALL_FAMILIES)
def test_rhoprime2_matches_r(R, family):
    from robstattm_py._r import r

    ro = r()
    ro.globalenv["u_test"] = U_GRID
    ro.r("library(RobStatTM)")
    cc = getattr(rpm.psi, family)(0.95)
    ro.globalenv["cc_test"] = np.atleast_1d(cc).astype(float)
    py = rpm.psi.rhoprime2(U_GRID, family=family, cc=cc)
    r_val = np.asarray(
        R(f'RobStatTM::rhoprime2(u_test, family="{family}", cc=cc_test)'), dtype=float
    )
    np.testing.assert_array_equal(py, r_val, err_msg=f"rhoprime2/{family}")


# ---------------------------------------------------------------------------
# Auto-derivation of cc from e
# ---------------------------------------------------------------------------

@needs_r
def test_rho_auto_cc():
    """Calling rho with e= but no cc= should yield the same result as supplying cc."""
    cc = rpm.psi.bisquare(0.90)
    a = rpm.psi.rho(U_GRID, family="bisquare", cc=cc)
    b = rpm.psi.rho(U_GRID, family="bisquare", e=0.90)
    np.testing.assert_array_equal(a, b)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

@needs_r
def test_determinism():
    a = rpm.psi.rho(U_GRID, family="mopt", e=0.95)
    b = rpm.psi.rho(U_GRID, family="mopt", e=0.95)
    np.testing.assert_array_equal(a, b)
