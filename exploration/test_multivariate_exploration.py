"""Multivariate wrappers, dispatcher, Rocke, fastmve, PCA variants.

None of these parameter combinations appear in ``docs/examples/`` except
``cov_rob_mm`` and ``prcomp_rob`` at default settings.
"""
from __future__ import annotations

import numpy as np

import robstattm_py as rpm
from tests.conftest import assert_scalar_equal, needs_r


@needs_r
class TestCovRobDispatcher:
    """``cov_rob`` auto-selects MM vs Rocke by dimension."""

    def test_glass_uses_mm(self):
        rpm.set_seed(11)
        X = rpm.datasets.glass().to_numpy()
        fit = rpm.cov_rob(X)
        assert fit.estimator_type == "MM"
        assert fit.cov.shape == (7, 7)
        assert np.all(np.isfinite(fit.center))

    def test_vehicle_uses_rocke(self):
        rpm.set_seed(11)
        X = rpm.datasets.vehicle().to_numpy()
        fit = rpm.cov_rob(X)
        assert fit.estimator_type == "Rocke"
        assert fit.cov.shape == (18, 18)

    def test_force_type_vs_r(self, R):
        rpm.set_seed(7)
        wine = rpm.datasets.wine().to_numpy()
        py = rpm.cov_rob(wine, type="MM")
        R("library(RobStatTM); data(wine); set.seed(7); "
          "r_fit <- covRob(wine, type='MM')")
        np.testing.assert_allclose(
            py.center, np.asarray(R("r_fit$center"), dtype=float), rtol=0, atol=0
        )


@needs_r
class TestCovClassicBaseline:
    """Classical Pearson baseline, side-by-side with robust."""

    def test_wine_classical_vs_robust(self):
        rpm.set_seed(5)
        wine = rpm.datasets.wine().to_numpy()
        classic = rpm.cov_classic(wine)
        robust = rpm.cov_rob_mm(wine)
        # Classical and robust centers should differ (wine has structure)
        assert not np.allclose(classic.center, robust.center)
        summ_cl = classic.summary()
        summ_ro = robust.summary()
        assert summ_cl.center.shape[0] == summ_ro.center.shape[0] == wine.shape[1]


@needs_r
class TestFastmveAndKurtInit:
    """Auxiliary covariance tools not in public examples."""

    def test_fastmve_on_biochem(self, R):
        X = rpm.datasets.biochem().to_numpy()
        py = rpm.fastmve(X)
        R("library(RobStatTM); data(biochem); "
          "X <- as.matrix(biochem); r_fit <- fastmve(X)")
        assert_scalar_equal(np.linalg.det(py.cov), np.linalg.det(R("r_fit$cov")))
        assert py.cov.shape == (2, 2)

    def test_kurt_sd_new_on_wine(self, R):
        rpm.set_seed(99)
        wine = rpm.datasets.wine().to_numpy()
        py = rpm.kurt_sd_new(wine)
        R("library(RobStatTM); data(wine); set.seed(99); "
          "r_fit <- KurtSDNew(wine)")
        np.testing.assert_allclose(
            py.center, np.asarray(R("r_fit$center"), dtype=float), rtol=0, atol=0
        )


@needs_r
class TestPcaVariants:
    """Both PCA entry points with non-default parameters."""

    def test_pca_rob_s_ncomp(self, R):
        rpm.set_seed(42)
        bus = rpm.datasets.bus().to_numpy()
        py = rpm.pca_rob_s(bus, ncomp=4, deltasca=0.4)
        R("library(RobStatTM); data(bus); set.seed(42); "
          "r_fit <- pcaRobS(bus, ncomp=4, deltasca=0.4)")
        assert py.q == int(np.asarray(R("r_fit$q")).item())
        r_propex = float(np.asarray(R("r_fit$propex")).item())
        assert abs(py.propex - r_propex) < 1e-12

    def test_prcomp_rob_rank(self, R):
        rpm.set_seed(42)
        bus = rpm.datasets.bus().to_numpy()
        py = rpm.prcomp_rob(bus, rank=5, delta_scale=0.45)
        R("library(RobStatTM); data(bus); set.seed(42); "
          "r_fit <- prcompRob(bus, rank.=5, delta.scale=0.45)")
        np.testing.assert_allclose(
            py.sdev[:5],
            np.asarray(R("r_fit$sdev"), dtype=float)[:5],
            rtol=0,
            atol=0,
        )
        summ = py.summary()
        assert len(summ.proportion_of_variance) == len(py.sdev)

    def test_cov_rob_mm_with_corr(self):
        rpm.set_seed(1)
        wine = rpm.datasets.wine()
        fit = rpm.cov_rob_mm(wine, corr=True)
        assert fit.cor is not None
        diag = np.diag(fit.cor)
        np.testing.assert_allclose(diag, np.ones_like(diag), rtol=1e-10, atol=1e-10)


@needs_r
class TestRockeExplicit:
    """Force Rocke path on medium-dimensional data."""

    def test_glass_rocke_vs_r(self, R):
        rpm.set_seed(3)
        X = rpm.datasets.glass().to_numpy()
        py = rpm.cov_rob_rocke(X)
        R("library(RobStatTM); data(glass); set.seed(3); "
          "r_fit <- covRobRocke(glass)")
        assert_scalar_equal(np.trace(py.cov), np.trace(R("r_fit$cov")))
