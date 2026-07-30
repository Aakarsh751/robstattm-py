"""Strict-tier tests for cov_rob dispatcher (port of covRob / Multirobu).

Note on seeding: ``cov_rob`` (and the underlying ``covRob``) uses random
projections via ``KurtSDNew``. To compare Python and R outputs at strict
tier, each must be seeded *immediately* before its call.
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


class TestValidation:
    def test_bad_type_raises(self):
        with pytest.raises(ValueError, match="type"):
            rpm.cov_rob(np.eye(5), type="bogus")


def _push_X(R, X, name: str) -> None:
    """Push a numpy matrix into R's global env under ``name``."""
    from robstattm_py._r import r as _r

    _r().globalenv[name] = X


@needs_r
class TestWineDispatch:
    """wine dataset (p=13) → dispatcher should pick Rocke under type='auto'."""

    @pytest.fixture(scope="class")
    def X(self):
        return rpm.datasets.wine().to_numpy(dtype=float)

    @pytest.fixture(scope="class")
    def _push(self, X, R):
        _push_X(R, X, "rpm_test_X")

    def test_auto_picks_rocke_for_p_ge_10(self, X, R, _push):
        rpm.set_seed(42)
        py = rpm.cov_rob(X, type="auto")
        assert py.estimator_type == "Rocke"

    def test_center_matches_r(self, X, R, _push):
        rpm.set_seed(42)
        py = rpm.cov_rob(X, type="auto")
        R("set.seed(42)")
        r_center = np.asarray(R("covRob(rpm_test_X, type='auto')$center"), dtype=float).ravel()
        np.testing.assert_array_equal(py.center, r_center)

    def test_cov_matches_r(self, X, R, _push):
        rpm.set_seed(42)
        py = rpm.cov_rob(X, type="auto")
        R("set.seed(42)")
        r_cov = np.asarray(R("covRob(rpm_test_X, type='auto')$cov"), dtype=float)
        np.testing.assert_array_equal(py.cov, r_cov)

    def test_dist_matches_r(self, X, R, _push):
        rpm.set_seed(42)
        py = rpm.cov_rob(X, type="auto")
        R("set.seed(42)")
        r_dist = np.asarray(R("covRob(rpm_test_X, type='auto')$dist"), dtype=float).ravel()
        np.testing.assert_array_equal(py.dist, r_dist)

    def test_wts_matches_r(self, X, R, _push):
        rpm.set_seed(42)
        py = rpm.cov_rob(X, type="auto")
        R("set.seed(42)")
        r_wts = np.asarray(R("covRob(rpm_test_X, type='auto')$wts"), dtype=float).ravel()
        np.testing.assert_array_equal(py.wts, r_wts)


@needs_r
class TestSmallP:
    """First 5 wine columns (p=5) → dispatcher should pick MM."""

    @pytest.fixture(scope="class")
    def X(self):
        return rpm.datasets.wine().iloc[:, :5].to_numpy(dtype=float)

    @pytest.fixture(scope="class")
    def _push(self, X, R):
        _push_X(R, X, "rpm_test_X5")

    def test_auto_picks_mm_for_p_lt_10(self, X, R, _push):
        rpm.set_seed(7)
        py = rpm.cov_rob(X, type="auto")
        assert py.estimator_type == "MM"

    def test_small_p_center_matches_r(self, X, R, _push):
        rpm.set_seed(7)
        py = rpm.cov_rob(X, type="auto")
        R("set.seed(7)")
        r_center = np.asarray(R("covRob(rpm_test_X5, type='auto')$center"), dtype=float).ravel()
        np.testing.assert_array_equal(py.center, r_center)


@needs_r
class TestExplicitType:
    """Forcing type='MM' or type='Rocke' overrides the auto rule."""

    @pytest.fixture(scope="class")
    def X(self):
        return rpm.datasets.wine().iloc[:, :5].to_numpy(dtype=float)

    @pytest.fixture(scope="class")
    def _push(self, X, R):
        _push_X(R, X, "rpm_test_Xf")

    def test_forced_mm(self, X, R, _push):
        rpm.set_seed(11)
        py = rpm.cov_rob(X, type="MM")
        assert py.estimator_type == "MM"
        R("set.seed(11)")
        r_center = np.asarray(R("covRob(rpm_test_Xf, type='MM')$center"), dtype=float).ravel()
        np.testing.assert_array_equal(py.center, r_center)

    def test_forced_rocke(self, X, R, _push):
        rpm.set_seed(11)
        py = rpm.cov_rob(X, type="Rocke")
        assert py.estimator_type == "Rocke"
        R("set.seed(11)")
        r_center = np.asarray(R("covRob(rpm_test_Xf, type='Rocke')$center"), dtype=float).ravel()
        np.testing.assert_array_equal(py.center, r_center)


@needs_r
def test_repr():
    X = rpm.datasets.wine().to_numpy(dtype=float)
    rpm.set_seed(42)
    fit = rpm.cov_rob(X, type="auto")
    s = repr(fit)
    assert "CovRobResult" in s
    assert "Rocke" in s


@needs_r
def test_corr_flag_shape_consistent():
    """When corr=True, ``cor`` is either None (R returned NULL) or (p,p)."""
    X = rpm.datasets.wine().iloc[:, :5].to_numpy(dtype=float)
    rpm.set_seed(1)
    fit = rpm.cov_rob(X, type="auto", corr=True)
    if fit.cor is not None:
        assert fit.cor.shape == fit.cov.shape
