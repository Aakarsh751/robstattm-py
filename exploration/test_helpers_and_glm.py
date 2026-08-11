"""ψ helpers, invtr2, refine_sm, and GLM parameter exploration."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import assert_array_equal, assert_scalar_equal, needs_r


@needs_r
class TestPsiFamilies:
    """Tuning constants and ρ/ψ evaluation — not in docs/examples."""

    @pytest.mark.parametrize("family", ["bisquare", "huber"])
    def test_tuning_constants_scalar_families(self, R, family):
        py_c = getattr(rpm.psi, family)(0.95)
        r_c = R(f'RobStatTM::{family}(0.95)')
        assert_scalar_equal(py_c, r_c, where=family)

    @pytest.mark.parametrize("family", ["mopt", "opt"])
    def test_tuning_constants_vector_families(self, R, family):
        py_c = getattr(rpm.psi, family)(0.95)
        r_c = np.asarray(R(f'RobStatTM::{family}(0.95)'), dtype=float)
        assert_array_equal(np.asarray(py_c, dtype=float), r_c, where=family)

    def test_rho_pipeline(self, R):
        u = np.linspace(-3, 3, 7)
        cc = rpm.psi.bisquare(0.95)
        py_rho = rpm.psi.rho(u, family="bisquare", cc=cc)
        R("c <- bisquare(0.95); u <- seq(-3,3,length=7); r_rho <- rho(u, family='bisquare', cc=c)")
        np.testing.assert_allclose(py_rho, np.asarray(R("r_rho"), dtype=float), rtol=0, atol=0)


@needs_r
class TestInvtr2:
    """Robust R² helper — exported separately in R."""

    def test_matches_r(self, R):
        py = rpm.invtr2(0.82, family="mopt", cc=rpm.psi.mopt(0.95))
        R("library(RobStatTM); r_v <- INVTR2(0.82, family='mopt', cc=mopt(0.95))")
        assert_scalar_equal(py, R("r_v"))


@needs_r
class TestGlmCustomizations:
    """GLM wrappers with non-default tuning — beyond by_logreg.py example."""

    @pytest.fixture(scope="class")
    def skin_xy(self):
        df = rpm.datasets.skin()
        X = df[["logVOL", "logRATE"]].to_numpy(dtype=float)
        y = df["vasoconst"].to_numpy(dtype=float)
        return X, y

    def test_wby_vs_r(self, skin_xy, R):
        X, y = skin_xy
        py = rpm.wby_logreg(X, y, const=0.5, kmax=500)
        R(
            "library(RobStatTM); data(skin); "
            "X <- as.matrix(skin[, c('logVOL','logRATE')]); y <- skin$vasoconst; "
            "r_fit <- WBYlogreg(X, y, const=0.5, kmax=500)"
        )
        np.testing.assert_allclose(
            py.coefficients,
            np.asarray(R("r_fit$coefficients"), dtype=float),
            rtol=0,
            atol=0,
        )

    def test_wml_returns_cov(self, skin_xy):
        X, y = skin_xy
        fit = rpm.wml_logreg(X, y)
        assert fit.cov is not None
        assert fit.cov.shape == (3, 3)  # intercept + 2 predictors
        assert fit.xweights is not None

    def test_by_intercept_false(self, skin_xy, R):
        X, y = skin_xy
        py = rpm.by_logreg(X, y, intercept=False)
        R(
            "library(RobStatTM); data(skin); "
            "X <- as.matrix(skin[, c('logVOL','logRATE')]); y <- skin$vasoconst; "
            "r_fit <- BYlogreg(X, y, intercept=FALSE)"
        )
        assert py.coefficients.shape[0] == 2
        np.testing.assert_allclose(
            py.coefficients, np.asarray(R("r_fit$coefficients"), dtype=float),
            rtol=0, atol=0,
        )


@needs_r
class TestLocScaleMGrid:
    """Univariate sweeps beyond loc_scale_m.py default."""

    @pytest.mark.parametrize("psi,eff", [("bisquare", 0.85), ("huber", 0.90), ("opt", 0.95)])
    def test_flour_vs_r(self, R, psi, eff):
        x = rpm.datasets.flour().iloc[:, 0].to_numpy()
        py = rpm.loc_scale_m(x, psi=psi, eff=eff)
        R(
            f"library(RobStatTM); data(flour); x <- as.vector(flour[,1]); "
            f"r_fit <- locScaleM(x, psi='{psi}', eff={eff})"
        )
        assert_scalar_equal(py.mu, R("r_fit$mu"))
        assert_scalar_equal(py.disper, R("r_fit$disper"))

    def test_m_scale_bisquare(self, R):
        x = rpm.datasets.resex()["resex"].to_numpy()
        py = rpm.m_scale(x, family="bisquare", delta=0.5)
        R(
            "library(RobStatTM); data(resex); "
            "r_s <- scaleM(resex, family='bisquare', delta=0.5)"
        )
        assert_scalar_equal(py, R("r_s"))


@needs_r
class TestCrossPackageDataset:
    """``datasets.load()`` for non-RobStatTM data — not in examples."""

    def test_coleman_regression(self, R):
        coleman = rpm.datasets.load("robustbase", "coleman")
        py = rpm.lmrobdet_mm("Y ~ .", data=coleman)
        R("coleman <- robustbase::coleman; "
          "r_fit <- RobStatTM::lmrobdetMM(Y ~ ., data=coleman)")
        assert_scalar_equal(py.r_squared, R("r_fit$r.squared"))
