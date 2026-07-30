"""Univariate (loc/scale, M-scale) family sweep + robust-logistic happy paths.

``tests/univariate`` and ``tests/glm`` cover the default family / flagship call;
here we sweep ψ-families and assert the structural invariants of the GLM result
(probabilities in [0, 1], coefficient length, family-specific optional fields).
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r

FAMILIES = ["mopt", "bisquare", "opt"]


@needs_r
class TestLocScaleFamilies:
    @pytest.mark.parametrize("psi", FAMILIES)
    def test_location_recovers_symmetric_center(self, psi):
        # Symmetric clean sample centred at 10 → robust location ≈ 10.
        x = np.arange(0.0, 21.0)
        res = rpm.loc_scale_m(x, psi=psi)
        assert abs(res.mu - 10.0) < 0.5
        assert res.disper > 0

    @pytest.mark.parametrize("psi", FAMILIES)
    def test_matches_r(self, psi, R):
        from robstattm_py._r import r

        ro = r()
        x = np.concatenate([np.linspace(-1, 1, 30), [12.0, -15.0]])
        ro.globalenv["rpm_ls_x"] = x
        try:
            py = rpm.loc_scale_m(x, psi=psi)
            r_mu = float(ro.r(f'RobStatTM::locScaleM(rpm_ls_x, psi="{psi}")$mu')[0])
        finally:
            ro.r("if (exists('rpm_ls_x')) rm(rpm_ls_x)")
        assert py.mu == r_mu

    def test_na_rm_drops_missing(self):
        x = np.array([1.0, 2.0, 3.0, np.nan, 5.0, 4.0, 2.0, 3.0])
        # default rejects NaN
        with pytest.raises(ValueError, match="NaN"):
            rpm.loc_scale_m(x)
        # na_rm=True succeeds and gives a finite estimate
        res = rpm.loc_scale_m(x, na_rm=True)
        assert np.isfinite(res.mu)


@needs_r
class TestMScale:
    @pytest.mark.parametrize("family", ["bisquare", "mopt"])
    def test_positive_for_spread_data(self, family):
        rng = np.random.default_rng(0)
        u = rng.standard_normal(80)
        s = rpm.m_scale(u, family=family)
        assert s > 0

    def test_scales_with_data(self):
        rng = np.random.default_rng(1)
        u = rng.standard_normal(100)
        s1 = rpm.m_scale(u)
        s2 = rpm.m_scale(3.0 * u)
        # M-scale is scale-equivariant: scaling the data ~triples the scale.
        assert abs(s2 / s1 - 3.0) < 0.1

    def test_zero_residuals_give_zero_scale(self):
        # scaleM treats its input as (already-centred) residuals.
        assert rpm.m_scale(np.zeros(40)) == 0.0

    def test_not_centred_constant_is_scale_equivariant(self):
        # GOTCHA: scaleM does NOT centre — a constant c is treated as residual c,
        # so the scale is positive and proportional to |c| (not 0).
        s7 = rpm.m_scale(np.full(40, 7.0))
        s14 = rpm.m_scale(np.full(40, 14.0))
        assert s7 > 0
        assert abs(s14 / s7 - 2.0) < 1e-9

    def test_bad_delta_raises(self):
        with pytest.raises(ValueError, match="delta"):
            rpm.m_scale(np.arange(10.0), delta=1.5)


def _binary_data(n=80, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, 2))
    # noisy logistic response — non-separable so the robust fits converge
    p = 1.0 / (1.0 + np.exp(-(0.8 * X[:, 0] - 0.5 * X[:, 1])))
    y = (rng.random(n) < p).astype(float)
    return X, y


@needs_r
class TestLogregInvariants:
    @pytest.mark.parametrize("fn", ["by_logreg", "wby_logreg", "wml_logreg"])
    def test_probabilities_and_shape(self, fn):
        X, y = _binary_data(seed=2)
        res = getattr(rpm, fn)(X, y)
        assert res.coefficients.shape == (3,)  # intercept + 2 slopes
        assert (res.fitted_values >= 0).all() and (res.fitted_values <= 1).all()
        assert res.fitted_values.shape == (X.shape[0],)

    def test_by_wby_expose_objective_and_convergence(self):
        X, y = _binary_data(seed=3)
        for fn in ("by_logreg", "wby_logreg"):
            res = getattr(rpm, fn)(X, y)
            assert res.objective is not None
            assert res.converged is not None

    def test_wml_exposes_cov_and_xweights(self):
        X, y = _binary_data(seed=4)
        res = rpm.wml_logreg(X, y)
        assert res.cov is not None and res.cov.shape == (3, 3)
        assert res.xweights is not None

    def test_no_intercept_drops_a_coefficient(self):
        X, y = _binary_data(seed=5)
        with_int = rpm.wml_logreg(X, y, intercept=True)
        no_int = rpm.wml_logreg(X, y, intercept=False)
        assert with_int.coefficients.shape == (3,)
        assert no_int.coefficients.shape == (2,)

    def test_non_binary_y_rejected(self):
        X, _ = _binary_data()
        with pytest.raises(ValueError, match="binary"):
            rpm.by_logreg(X, np.array([0, 1, 2] * (X.shape[0] // 3 + 1))[: X.shape[0]])
