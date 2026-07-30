"""Strict-tier tests for kurt_sd_new and fastmve."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from robstattm_py import set_seed
from tests.conftest import needs_r


class TestValidation:
    def test_1d_raises(self):
        with pytest.raises(ValueError):
            rpm.kurt_sd_new(np.arange(10.0))
        with pytest.raises(ValueError):
            rpm.fastmve(np.arange(10.0))


@needs_r
class TestKurtSDNewVsR:
    @pytest.fixture
    def setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(wine); X_wk <- as.matrix(wine[, sapply(wine, is.numeric)])")
        set_seed(7)
        py = rpm.kurt_sd_new(rpm.datasets.wine())
        ro.r("set.seed(7L); k_check <- KurtSDNew(X_wk)")
        return py

    def test_center(self, setup, R):
        py = setup
        r_c = np.asarray(R("k_check$center"), dtype=float)
        np.testing.assert_array_equal(py.center, r_c)

    def test_cova(self, setup, R):
        py = setup
        r_v = np.asarray(R("k_check$cova"), dtype=float)
        np.testing.assert_array_equal(py.cova, r_v)

    def test_disma(self, setup, R):
        py = setup
        r_d = np.asarray(R("k_check$disma"), dtype=float)
        np.testing.assert_array_equal(py.disma, r_d)

    def test_idx(self, setup, R):
        py = setup
        r_i = np.asarray(R("k_check$idx"), dtype=float)
        np.testing.assert_array_equal(py.idx, r_i)

    def test_t(self, setup, R):
        py = setup
        r_t = np.asarray(R("k_check$t"), dtype=float)
        np.testing.assert_array_equal(py.t, r_t)


@needs_r
class TestFastMVEVsR:
    @pytest.fixture
    def setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(wine); X_fmve <- as.matrix(wine[, sapply(wine, is.numeric)])")
        set_seed(11)
        py = rpm.fastmve(rpm.datasets.wine())
        ro.r("set.seed(11L); fmve <- fastmve(X_fmve)")
        return py

    def test_center(self, setup, R):
        py = setup
        np.testing.assert_array_equal(py.center, np.asarray(R("fmve$center"), dtype=float))

    def test_cov(self, setup, R):
        py = setup
        np.testing.assert_array_equal(py.cov, np.asarray(R("fmve$cov"), dtype=float))

    def test_scale(self, setup, R):
        py = setup
        assert py.scale == float(R("fmve$scale")[0])

    def test_best_zero_based(self, setup, R):
        """`best` indices are 0-based in Python; verify they're R-1."""
        py = setup
        r_best = np.asarray(R("fmve$best"), dtype=int)
        np.testing.assert_array_equal(py.best, r_best - 1)
        assert py.best.min() >= 0  # valid 0-based index


@needs_r
def test_kurt_sd_repr():
    set_seed(1)
    res = rpm.kurt_sd_new(rpm.datasets.wine())
    assert "KurtSDResult" in repr(res)


@needs_r
def test_fastmve_repr():
    set_seed(1)
    res = rpm.fastmve(rpm.datasets.wine())
    assert "FastMVEResult" in repr(res)
