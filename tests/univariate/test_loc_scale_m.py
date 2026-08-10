"""Strict-tier tests for robstattm_py.loc_scale_m vs direct R."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import (
    assert_scalar_equal,
    needs_r,
)

# Deterministic golden input (no Python randomness — R and Py see identical bits)
GOLDEN_X = np.array(
    [
        1.2, -0.4, 0.7, 2.1, -1.0, 0.3, 1.8, -2.5, 0.9, 0.0,
        10.0, -10.0, 0.5, -0.3, 1.5, 2.2, -1.7, 0.6, 0.1, -0.8,
    ]
)


# ---------------------------------------------------------------------------
# Case 7 — argument validation (do not require R)
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_non_numeric_raises_type_error(self):
        with pytest.raises(TypeError):
            rpm.loc_scale_m("not numeric")  # type: ignore[arg-type]

    def test_empty_raises_value_error(self):
        with pytest.raises(ValueError):
            rpm.loc_scale_m(np.array([]))

    def test_2d_raises_value_error(self):
        with pytest.raises(ValueError):
            rpm.loc_scale_m(np.ones((3, 4)))

    def test_nan_without_narm_raises(self):
        with pytest.raises(ValueError, match="NaN"):
            rpm.loc_scale_m(np.array([1.0, 2.0, np.nan, 3.0]))

    # --- eff must be in the family-specific allowed set (R/MLocDis.R) ---
    # bisquare/huber only tabulate {0.85, 0.90, 0.95}; an out-of-set eff makes R
    # fail with an opaque "object 'resi' not found" (or a silent NA for the opt
    # family). Validate before the rpy2 boundary instead.
    @pytest.mark.parametrize("psi", ["bisquare", "huber"])
    def test_eff_099_rejected_for_bisquare_huber(self, psi):
        with pytest.raises(ValueError, match="not supported for psi"):
            rpm.loc_scale_m(GOLDEN_X, psi=psi, eff=0.99)

    @pytest.mark.parametrize("psi", ["mopt", "bisquare", "huber", "opt"])
    def test_off_grid_eff_rejected(self, psi):
        # 0.92 is in no family's allowed set
        with pytest.raises(ValueError, match="not supported for psi"):
            rpm.loc_scale_m(GOLDEN_X, psi=psi, eff=0.92)


# ---------------------------------------------------------------------------
# Strict-tier R comparison — all family × eff combos
# ---------------------------------------------------------------------------

@needs_r
class TestStrictTierVsR:
    """For each (family, eff), the Python output must equal R to atol=0."""

    @pytest.mark.parametrize("psi", ["mopt", "bisquare", "huber"])
    @pytest.mark.parametrize("eff", [0.85, 0.90, 0.95])
    def test_loc_scale_m_matches_r(self, R, psi, eff):
        py = rpm.loc_scale_m(GOLDEN_X, psi=psi, eff=eff)

        # Direct R call with the same input
        from robstattm_py._r import r

        ro = r()
        ro.globalenv["x_test"] = GOLDEN_X
        ro.r("library(RobStatTM)")
        r_mu = R(f'locScaleM(x_test, psi="{psi}", eff={eff})$mu')
        r_sd = R(f'locScaleM(x_test, psi="{psi}", eff={eff})$std.mu')
        r_di = R(f'locScaleM(x_test, psi="{psi}", eff={eff})$disper')

        assert_scalar_equal(py.mu, r_mu, where=f"mu psi={psi} eff={eff}")
        assert_scalar_equal(py.std_mu, r_sd, where=f"std_mu psi={psi} eff={eff}")
        assert_scalar_equal(py.disper, r_di, where=f"disper psi={psi} eff={eff}")

    @pytest.mark.parametrize("psi", ["mopt", "opt", "optv0", "moptv0"])
    def test_eff_099_opt_family_matches_r(self, R, psi):
        """The opt/mopt families additionally support eff=0.99 — verify the
        validation lets it through AND the result is strict-tier identical to R.
        """
        py = rpm.loc_scale_m(GOLDEN_X, psi=psi, eff=0.99)
        from robstattm_py._r import r

        ro = r()
        ro.globalenv["x_test"] = GOLDEN_X
        ro.r("library(RobStatTM)")
        assert_scalar_equal(
            py.mu, R(f'locScaleM(x_test, psi="{psi}", eff=0.99)$mu'),
            where=f"mu psi={psi} eff=0.99",
        )
        assert_scalar_equal(
            py.disper, R(f'locScaleM(x_test, psi="{psi}", eff=0.99)$disper'),
            where=f"disper psi={psi} eff=0.99",
        )


# ---------------------------------------------------------------------------
# Edge cases: clean data, contaminated data, all-equal
# ---------------------------------------------------------------------------

@needs_r
class TestEdgeCases:
    def test_clean_gaussian(self, R):
        from robstattm_py._r import r

        ro = r()
        x = np.linspace(-2, 2, 51)  # deterministic, no randomness
        ro.globalenv["x_clean"] = x
        ro.r("library(RobStatTM)")
        py = rpm.loc_scale_m(x)
        assert_scalar_equal(py.mu, R("locScaleM(x_clean)$mu"), where="clean mu")
        assert_scalar_equal(py.disper, R("locScaleM(x_clean)$disper"), where="clean disper")

    def test_heavy_contamination(self, R):
        from robstattm_py._r import r

        ro = r()
        # Sample with ~40% outliers; tests robustness regime
        x = np.concatenate([np.linspace(-1, 1, 30), np.full(20, 100.0)])
        ro.globalenv["x_contam"] = x
        ro.r("library(RobStatTM)")
        py = rpm.loc_scale_m(x)
        assert_scalar_equal(py.mu, R("locScaleM(x_contam)$mu"), where="contam mu")
        assert_scalar_equal(py.disper, R("locScaleM(x_contam)$disper"), where="contam disper")


# ---------------------------------------------------------------------------
# Determinism: same input -> same output
# ---------------------------------------------------------------------------

@needs_r
def test_determinism():
    """Repeated calls on the same input produce identical results."""
    a = rpm.loc_scale_m(GOLDEN_X)
    b = rpm.loc_scale_m(GOLDEN_X)
    assert a == b
