"""Strict-tier tests for pca_rob_s and prcomp_rob."""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_r


class TestValidation:
    def test_1d_raises(self):
        with pytest.raises(ValueError):
            rpm.pca_rob_s(np.arange(10.0))

    def test_nan_raises(self):
        with pytest.raises(ValueError):
            rpm.pca_rob_s(np.array([[1.0, np.nan], [3.0, 4.0]]))


@needs_r
class TestPcaRobSVsR:
    """Strict-tier comparison on the bus dataset (R chapter 6 flagship)."""

    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(bus); X_bus <- as.matrix(bus[, sapply(bus, is.numeric)])")
        set_seed(42)
        df = rpm.datasets.bus()
        py = rpm.pca_rob_s(df, ncomp=3)
        ro.r("set.seed(42L); fit_pca <- pcaRobS(X_bus, ncomp=3)")
        return py

    def test_eigvec(self, setup, R):
        py = setup
        r_eigvec = np.asarray(R("fit_pca$eigvec"), dtype=float)
        np.testing.assert_array_equal(py.eigvec, r_eigvec)

    def test_repre(self, setup, R):
        py = setup
        r_repre = np.asarray(R("fit_pca$repre"), dtype=float)
        np.testing.assert_array_equal(py.repre, r_repre)

    def test_propex(self, setup, R):
        py = setup
        assert py.propex == float(R("fit_pca$propex")[0])

    def test_prop_spc(self, setup, R):
        py = setup
        r_pspc = np.asarray(R("fit_pca$propSPC"), dtype=float)
        np.testing.assert_array_equal(py.prop_spc, r_pspc)

    def test_mu(self, setup, R):
        py = setup
        r_mu = np.asarray(R("fit_pca$mu"), dtype=float)
        np.testing.assert_array_equal(py.mu, r_mu)

    def test_q(self, setup, R):
        py = setup
        assert py.q == int(R("fit_pca$q")[0])

    def test_fit_matrix(self, setup, R):
        py = setup
        r_fit = np.asarray(R("fit_pca$fit"), dtype=float)
        np.testing.assert_array_equal(py.fit, r_fit)


@needs_r
class TestPrcompRobVsR:
    """prcomp_rob shape and values vs direct R."""

    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(wine); X_wine <- as.matrix(wine[, sapply(wine, is.numeric)])")
        set_seed(7)
        df = rpm.datasets.wine()
        py = rpm.prcomp_rob(df)
        ro.r("set.seed(7L); fit_prc <- prcompRob(X_wine)")
        return py

    def test_sdev(self, setup, R):
        py = setup
        r_sdev = np.asarray(R("fit_prc$sdev"), dtype=float)
        np.testing.assert_array_equal(py.sdev, r_sdev)

    def test_rotation(self, setup, R):
        py = setup
        r_rot = np.asarray(R("fit_prc$rotation"), dtype=float)
        np.testing.assert_array_equal(py.rotation, r_rot)

    def test_center(self, setup, R):
        py = setup
        r_center = np.asarray(R("fit_prc$center"), dtype=float)
        np.testing.assert_array_equal(py.center, r_center)

    def test_scores(self, setup, R):
        py = setup
        r_x = np.asarray(R("fit_prc$x"), dtype=float)
        np.testing.assert_array_equal(py.scores, r_x)


@needs_r
def test_pca_repr():
    set_seed(42)
    df = rpm.datasets.bus()
    res = rpm.pca_rob_s(df, ncomp=2)
    s = repr(res)
    assert "PcaRobSResult" in s
    assert "q=2" in s
