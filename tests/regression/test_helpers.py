"""Strict-tier tests for the regression helpers: invtr2 + RFPE method."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


class TestInvtr2Validation:
    def test_bad_family(self):
        with pytest.raises(ValueError, match="family"):
            rpm.invtr2(0.5, "bogus", 4.685)

    def test_bad_rr2_type(self):
        with pytest.raises(TypeError, match="rr2"):
            rpm.invtr2("oops", "bisquare", 4.685)

    def test_bad_cc_type_for_scalar_family(self):
        with pytest.raises(TypeError, match="cc"):
            rpm.invtr2(0.5, "bisquare", "oops")

    def test_bad_cc_length_for_vector_family(self):
        with pytest.raises(ValueError, match="length-16"):
            rpm.invtr2(0.5, "opt", [1.0, 2.0])

    def test_bad_cc_length_for_huber(self):
        with pytest.raises(ValueError, match="length-3"):
            rpm.invtr2(0.5, "huber", [1.0, 2.0])


@needs_r
class TestInvtr2VsR_Scalar:
    """Strict-tier scalar-family parity with R's INVTR2."""

    @pytest.mark.parametrize("rr2", [0.0, 0.1, 0.5, 0.9, 0.99])
    @pytest.mark.parametrize("family,cc", [
        ("bisquare", 4.685),
        ("bisquare", 3.4437),  # 85% efficiency
    ])
    def test_invtr2_matches_r(self, R, rr2, family, cc):
        py = rpm.invtr2(rr2, family, cc)
        r_val = float(R(f"INVTR2({rr2}, '{family}', {cc})")[0])
        assert py == r_val


@needs_r
class TestInvtr2VsR_Vector:
    """Strict-tier vector-family parity (opt/mopt take a 16-elt cc vector)."""

    @pytest.mark.parametrize("rr2", [0.1, 0.5, 0.9])
    @pytest.mark.parametrize("family", ["mopt", "opt"])
    def test_invtr2_vector_family(self, R, rr2, family):
        # Get the canonical 16-element cc vector from the family helper
        cc_arr = getattr(rpm.psi, family)(0.95)  # 95% efficiency
        py = rpm.invtr2(rr2, family, cc_arr)
        # Push the same cc into R
        from robstattm_py._r import r as _r
        _r().globalenv["rpm_cc_test"] = np.asarray(cc_arr, dtype=float)
        r_val = float(R(f"INVTR2({rr2}, '{family}', rpm_cc_test)")[0])
        assert py == r_val


@needs_r
class TestRFPEMethod:
    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_mm("zinc ~ copper", data=df)

    @pytest.fixture(scope="class")
    def r_ctx(self):
        from robstattm_py._r import r
        ro = r()
        ro.r(
            "library(RobStatTM); data(mineral); "
            "rpm_test_rfpe_fit <- lmrobdetMM(zinc ~ copper, data=mineral); "
            "rpm_test_rfpe_val <- lmrobdetMM.RFPE(rpm_test_rfpe_fit); "
            "rpm_test_rfpe_both <- lmrobdetMM.RFPE(rpm_test_rfpe_fit, bothVals=TRUE)"
        )
        return ro

    def test_rfpe_scalar(self, fit, r_ctx, R):
        py = fit.rfpe()
        r_val = float(R("rpm_test_rfpe_val")[0])
        assert py == r_val
        assert isinstance(py, float)

    def test_rfpe_both_vals(self, fit, r_ctx, R):
        py = fit.rfpe(both_vals=True)
        assert isinstance(py, tuple) and len(py) == 2
        a, b = py
        r_a = float(R("rpm_test_rfpe_both$minRhoMM.C")[0])
        r_b = float(R("rpm_test_rfpe_both$penaltyRFPE")[0])
        assert a == r_a
        assert b == r_b

    def test_rfpe_sum_equals_scalar(self, fit, r_ctx):
        scalar = fit.rfpe()
        a, b = fit.rfpe(both_vals=True)
        # RFPE = minRhoMM.C + penaltyRFPE per R's lmrobdetMM.RFPE source
        assert scalar == a + b
