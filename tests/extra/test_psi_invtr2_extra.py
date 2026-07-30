"""ψ-family mathematical identities + INVTR2 coverage.

``tests/psi/test_psi.py`` checks pointwise parity vs R and bisquare auto-cc.
Here we assert the *structural* identities a ρ/ψ family must satisfy (even/odd,
ρ(0)=0, boundedness) and extend the auto-cc check to the vector families, plus
add INVTR2 happy-path parity (only its validation is tested elsewhere).
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r

U = np.array([-3.0, -1.5, -0.3, 0.0, 0.3, 1.5, 3.0])
SCALAR_FAMILIES = ["bisquare", "huber"]
VECTOR_FAMILIES = ["mopt", "opt"]


@needs_r
class TestRhoIdentities:
    @pytest.mark.parametrize("family", SCALAR_FAMILIES + VECTOR_FAMILIES)
    def test_rho_at_zero_is_zero(self, family):
        cc = getattr(rpm.psi, family)(0.95)
        assert rpm.psi.rho([0.0], family=family, cc=cc)[0] == 0.0

    @pytest.mark.parametrize("family", SCALAR_FAMILIES + VECTOR_FAMILIES)
    def test_psi_at_zero_is_zero(self, family):
        cc = getattr(rpm.psi, family)(0.95)
        # ψ(0) = ρ'(0) = 0 for every symmetric redescending family
        assert abs(rpm.psi.rhoprime([0.0], family=family, cc=cc)[0]) < 1e-12

    def test_rho_is_even(self):
        cc = rpm.psi.bisquare(0.95)
        left = rpm.psi.rho(-U, family="bisquare", cc=cc)
        right = rpm.psi.rho(U, family="bisquare", cc=cc)
        np.testing.assert_array_equal(left, right)

    def test_psi_is_odd(self):
        cc = rpm.psi.bisquare(0.95)
        left = rpm.psi.rhoprime(-U, family="bisquare", cc=cc)
        right = rpm.psi.rhoprime(U, family="bisquare", cc=cc)
        np.testing.assert_array_almost_equal(left, -right, decimal=12)

    def test_standardized_rho_in_unit_interval(self):
        cc = rpm.psi.bisquare(0.95)
        vals = rpm.psi.rho(np.linspace(-10, 10, 201), family="bisquare",
                           cc=cc, standardize=True)
        assert vals.min() >= 0.0
        assert vals.max() <= 1.0 + 1e-12

    def test_redescending_rho_saturates(self):
        """A redescending ρ flattens at 1 far from 0 (bisquare)."""
        cc = rpm.psi.bisquare(0.95)
        far = rpm.psi.rho([50.0, 100.0], family="bisquare", cc=cc, standardize=True)
        np.testing.assert_array_almost_equal(far, [1.0, 1.0], decimal=10)


@needs_r
class TestAutoCcVectorFamilies:
    """`rho(..., e=)` auto-derivation must equal `rho(..., cc=)` for the vector
    families too (the strict suite only verifies this for bisquare)."""

    @pytest.mark.parametrize("family", VECTOR_FAMILIES)
    @pytest.mark.parametrize("fn", ["rho", "rhoprime", "rhoprime2"])
    def test_auto_cc_matches_explicit(self, family, fn):
        cc = getattr(rpm.psi, family)(0.9)
        f = getattr(rpm.psi, fn)
        a = f(U, family=family, cc=cc)
        b = f(U, family=family, e=0.9)
        np.testing.assert_array_equal(a, b)


@needs_r
class TestInvtr2:
    def test_bisquare_matches_doc_value(self):
        assert abs(rpm.invtr2(0.5, "bisquare", 4.685) - 0.5106142) < 1e-6

    @pytest.mark.parametrize("rr2", [0.1, 0.4, 0.7])
    def test_bisquare_parity(self, rr2, R):
        cc = float(rpm.psi.bisquare(0.95))
        py = rpm.invtr2(rr2, "bisquare", cc)
        r_val = float(R(f'RobStatTM::INVTR2({rr2}, "bisquare", {cc})')[0])
        assert py == r_val

    def test_opt_vector_parity(self, R):
        from robstattm_py._r import r

        cc = np.asarray(rpm.psi.opt(0.95), dtype=float)
        ro = r()
        ro.globalenv["rpm_cc_opt"] = cc
        try:
            py = rpm.invtr2(0.4, "opt", cc)
            r_val = float(ro.r('RobStatTM::INVTR2(0.4, "opt", rpm_cc_opt)')[0])
        finally:
            ro.r("if (exists('rpm_cc_opt')) rm(rpm_cc_opt)")
        assert py == r_val

    def test_invtr2_is_increasing_in_rr2(self):
        cc = float(rpm.psi.bisquare(0.95))
        vals = [rpm.invtr2(r, "bisquare", cc) for r in (0.1, 0.3, 0.5, 0.7)]
        assert all(b > a for a, b in zip(vals, vals[1:]))
