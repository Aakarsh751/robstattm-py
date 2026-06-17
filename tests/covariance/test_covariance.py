"""Strict-tier tests for cov_classic, cov_rob_mm, cov_rob_rocke."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_r


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_non_numeric_raises(self):
        with pytest.raises((TypeError, ValueError)):
            rpm.cov_classic([["a", "b"], ["c", "d"]])

    def test_1d_raises(self):
        with pytest.raises(ValueError):
            rpm.cov_classic(np.array([1.0, 2.0, 3.0]))

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            rpm.cov_classic(np.empty((0, 3)))

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            rpm.cov_classic(np.array([[1.0, np.nan], [3.0, 4.0]]))


# ---------------------------------------------------------------------------
# cov_classic — fully deterministic, strict tier vs R
# ---------------------------------------------------------------------------

@needs_r
class TestCovClassic:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(wine); X_test <- as.matrix(wine[, sapply(wine, is.numeric)]); "
             "fit_c <- covClassic(X_test)")
        df = rpm.datasets.wine()
        py = rpm.cov_classic(df)
        return py

    def test_center(self, setup, R):
        py = setup
        r_center = np.asarray(R("fit_c$center"), dtype=float)
        np.testing.assert_array_equal(py.center, r_center)

    def test_cov(self, setup, R):
        py = setup
        r_cov = np.asarray(R("fit_c$cov"), dtype=float)
        np.testing.assert_array_equal(py.cov, r_cov)

    def test_dist(self, setup, R):
        py = setup
        r_dist = np.asarray(R("fit_c$dist"), dtype=float)
        np.testing.assert_array_equal(py.dist, r_dist)

    def test_repr(self, setup):
        s = repr(setup)
        assert "CovClassicResult" in s


@needs_r
class TestCovClassicNaActionAndArgs:
    """Non-default args: na_action (NaN handling) + corr/unbiased, vs R."""

    @pytest.fixture
    def data_with_nan(self):
        rng = np.random.RandomState(7)
        M = rng.randn(30, 3)
        M[2, 1] = np.nan
        M[10, 0] = np.nan
        return M

    def test_default_rejects_nan(self, data_with_nan):
        with pytest.raises(ValueError, match="NaN"):
            rpm.cov_classic(data_with_nan)

    def test_invalid_na_action_raises(self):
        with pytest.raises(ValueError, match="na_action"):
            rpm.cov_classic(np.zeros((5, 2)) + np.arange(10).reshape(5, 2),
                            na_action="bogus")

    def test_na_action_omit_matches_r(self, data_with_nan, R):
        from robstatm_py._r import r
        ro = r()
        ro.globalenv["A_na"] = data_with_nan
        py = rpm.cov_classic(data_with_nan, na_action="omit")
        r_cov = np.asarray(R("covClassic(A_na, na.action=na.omit)$cov"), float)
        r_ctr = np.asarray(R("covClassic(A_na, na.action=na.omit)$center"), float)
        r_dist = np.asarray(R("covClassic(A_na, na.action=na.omit)$dist"), float).ravel()
        np.testing.assert_array_equal(py.cov, r_cov)
        np.testing.assert_array_equal(py.center, r_ctr)
        np.testing.assert_array_equal(np.asarray(py.dist, float).ravel(), r_dist)
        assert py.dist.size == 28  # 30 rows minus 2 with NaN

    def test_corr_and_unbiased_match_r(self, R):
        from robstatm_py._r import r
        rng = np.random.RandomState(3)
        M = rng.randn(25, 4)
        ro = r()
        ro.globalenv["A_cc"] = M
        py = rpm.cov_classic(M, corr=True, unbiased=False)
        r_cov = np.asarray(R("covClassic(A_cc, corr=TRUE, unbiased=FALSE)$cov"), float)
        r_cor = np.asarray(R("covClassic(A_cc, corr=TRUE, unbiased=FALSE)$cor"), float)
        np.testing.assert_array_equal(py.cov, r_cov)
        np.testing.assert_array_equal(py.cor, r_cor)


# ---------------------------------------------------------------------------
# cov_rob_mm — stochastic; needs set_seed for parity
# ---------------------------------------------------------------------------

@needs_r
class TestCovRobMM:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(wine); X_test <- as.matrix(wine[, sapply(wine, is.numeric)])")
        # Seed R BEFORE Python wrapper runs; set_seed seeds both
        set_seed(42)
        df = rpm.datasets.wine()
        py = rpm.cov_rob_mm(df)
        # Re-seed R, then run R's own covRobMM for comparison
        ro.r("set.seed(42L); fit_mm <- covRobMM(X_test)")
        return py

    def test_center(self, setup, R):
        py = setup
        r_center = np.asarray(R("fit_mm$center"), dtype=float)
        np.testing.assert_array_equal(py.center, r_center)

    def test_cov(self, setup, R):
        py = setup
        r_cov = np.asarray(R("fit_mm$cov"), dtype=float)
        np.testing.assert_array_equal(py.cov, r_cov)

    def test_dist(self, setup, R):
        py = setup
        r_dist = np.asarray(R("fit_mm$dist"), dtype=float)
        np.testing.assert_array_equal(py.dist, r_dist)

    def test_wts(self, setup, R):
        py = setup
        r_wts = np.asarray(R("fit_mm$wts"), dtype=float)
        np.testing.assert_array_equal(py.wts, r_wts)

    def test_mu_initial(self, setup, R):
        py = setup
        r_mu = np.asarray(R("fit_mm$mu"), dtype=float)
        np.testing.assert_array_equal(py.mu, r_mu)

    def test_v_initial(self, setup, R):
        py = setup
        r_v = np.asarray(R("fit_mm$V"), dtype=float)
        np.testing.assert_array_equal(py.v, r_v)

    def test_cov_symmetric(self, setup):
        # R's covRobMM/covRobRocke output is symmetric only to machine precision
        # (not exactly), so this property check uses a loose tolerance — strict
        # R↔Python parity is still enforced by the test_cov tests above.
        py = setup
        np.testing.assert_allclose(py.cov, py.cov.T, atol=1e-12, rtol=0)

    def test_cov_psd(self, setup):
        py = setup
        eigvals = np.linalg.eigvalsh(py.cov)
        assert eigvals.min() > -1e-12


# ---------------------------------------------------------------------------
# cov_rob_rocke — stochastic
# ---------------------------------------------------------------------------

@needs_r
class TestCovRobRocke:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(wine); X_test <- as.matrix(wine[, sapply(wine, is.numeric)])")
        set_seed(123)
        df = rpm.datasets.wine()
        py = rpm.cov_rob_rocke(df)
        ro.r("set.seed(123L); fit_r <- covRobRocke(X_test)")
        return py

    def test_center(self, setup, R):
        py = setup
        r_center = np.asarray(R("fit_r$center"), dtype=float)
        np.testing.assert_array_equal(py.center, r_center)

    def test_cov(self, setup, R):
        py = setup
        r_cov = np.asarray(R("fit_r$cov"), dtype=float)
        np.testing.assert_array_equal(py.cov, r_cov)

    def test_dist(self, setup, R):
        py = setup
        r_dist = np.asarray(R("fit_r$dist"), dtype=float)
        np.testing.assert_array_equal(py.dist, r_dist)

    def test_sig(self, setup, R):
        py = setup
        assert py.sig == float(R("fit_r$sig")[0])

    def test_gamma(self, setup, R):
        py = setup
        assert py.gamma == float(R("fit_r$gamma")[0])

    def test_cov_symmetric(self, setup):
        # R's covRobMM/covRobRocke output is symmetric only to machine precision
        # (not exactly), so this property check uses a loose tolerance — strict
        # R↔Python parity is still enforced by the test_cov tests above.
        py = setup
        np.testing.assert_allclose(py.cov, py.cov.T, atol=1e-12, rtol=0)


# ---------------------------------------------------------------------------
# Smaller synthetic dataset — pure deterministic input, low p
# ---------------------------------------------------------------------------

@needs_r
def test_cov_classic_small_synthetic(R):
    from robstatm_py._r import r

    ro = r()
    # Pure deterministic Hilbert-like matrix (no randomness)
    X = np.fromfunction(lambda i, j: 1.0 / (1 + i + j), (10, 4), dtype=float)
    ro.globalenv["X_small"] = X
    ro.r("fit_cs <- covClassic(X_small)")
    py = rpm.cov_classic(X)
    np.testing.assert_array_equal(py.center, np.asarray(R("fit_cs$center"), dtype=float))
    np.testing.assert_array_equal(py.cov, np.asarray(R("fit_cs$cov"), dtype=float))
