"""Strict-tier tests for gse + tsgs vs direct R (GSE package)."""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_gse


def _make_data(n=60, p=5, seed=0):
    rng = np.random.RandomState(seed)
    return rng.randn(n, p)


def _with_missing(X, frac=0.10, seed=123):
    Xm = X.copy()
    rng = np.random.default_rng(seed)
    flat = rng.choice(X.size, size=round(frac * X.size), replace=False)
    Xm.ravel()[flat] = np.nan
    return Xm


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_1d_raises(self):
        with pytest.raises(ValueError):
            rpm.gse(np.arange(10.0))

    def test_inf_raises(self):
        X = np.ones((10, 3))
        X[0, 0] = np.inf
        with pytest.raises(ValueError):
            rpm.gse(X)


# ---------------------------------------------------------------------------
# GSE — missing data, strict tier
# ---------------------------------------------------------------------------

@needs_gse
class TestGSE:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(GSE)")
        Xm = _with_missing(_make_data())
        ro.globalenv["Xm"] = Xm
        set_seed(42)
        py = rpm.gse(Xm)
        ro.r("set.seed(42L); rg <- GSE(Xm)")
        return py

    def test_mu(self, setup, R):
        np.testing.assert_array_equal(setup.mu, np.asarray(R("rg@mu"), dtype=float).ravel())

    def test_cov(self, setup, R):
        np.testing.assert_array_equal(setup.cov, np.asarray(R("rg@S"), dtype=float))

    def test_pmd(self, setup, R):
        np.testing.assert_array_equal(setup.pmd, np.asarray(R("rg@pmd"), dtype=float).ravel())

    def test_pmd_adj(self, setup, R):
        np.testing.assert_array_equal(
            setup.pmd_adj, np.asarray(R("rg@pmd.adj"), dtype=float).ravel()
        )

    def test_weights(self, setup, R):
        np.testing.assert_array_equal(
            setup.weights, np.asarray(R("rg@weights"), dtype=float).ravel()
        )

    def test_ximp(self, setup, R):
        np.testing.assert_array_equal(setup.ximp, np.asarray(R("rg@ximp"), dtype=float))

    def test_sc(self, setup, R):
        assert setup.sc == float(R("rg@sc")[0])

    def test_iter(self, setup, R):
        assert setup.iter == int(R("rg@iter")[0])

    def test_cov_symmetric(self, setup):
        np.testing.assert_allclose(setup.cov, setup.cov.T, atol=1e-12, rtol=0)

    def test_repr(self, setup):
        assert "GSEResult" in repr(setup)

    def test_accessors_match_slots(self, setup, R):
        """The S4 accessors getLocation/getScatter equal the slots we read."""
        np.testing.assert_array_equal(
            setup.mu, np.asarray(R("as.numeric(getLocation(rg))"), dtype=float)
        )
        np.testing.assert_array_equal(
            setup.cov, np.asarray(R("as.matrix(getScatter(rg))"), dtype=float)
        )


# ---------------------------------------------------------------------------
# TSGS — cell-wise, strict tier
# ---------------------------------------------------------------------------

@needs_gse
class TestTSGS:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(GSE)")
        X = _make_data()
        ro.globalenv["Xfull"] = X
        set_seed(42)
        py = rpm.tsgs(X)
        ro.r("set.seed(42L); rt <- TSGS(Xfull)")
        return py

    def test_mu(self, setup, R):
        np.testing.assert_array_equal(setup.mu, np.asarray(R("rt@mu"), dtype=float).ravel())

    def test_cov(self, setup, R):
        np.testing.assert_array_equal(setup.cov, np.asarray(R("rt@S"), dtype=float))

    def test_pmd(self, setup, R):
        np.testing.assert_array_equal(setup.pmd, np.asarray(R("rt@pmd"), dtype=float).ravel())

    def test_xf_filtered(self, setup, R):
        # xf carries NaN for flagged cells; compare with nan-equal semantics
        py_xf = setup.xf
        r_xf = np.asarray(R("rt@xf"), dtype=float)
        assert py_xf.shape == r_xf.shape
        both_nan = np.isnan(py_xf) & np.isnan(r_xf)
        np.testing.assert_array_equal(py_xf[~both_nan], r_xf[~both_nan])
        np.testing.assert_array_equal(np.isnan(py_xf), np.isnan(r_xf))

    def test_sc(self, setup, R):
        assert setup.sc == float(R("rt@sc")[0])

    def test_repr(self, setup):
        assert "TSGSResult" in repr(setup)
