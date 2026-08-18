"""Strict-tier tests for pense + pense_cv vs direct R (pense package)."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from robstattm_py import set_seed
from tests.conftest import needs_pense


def _make_data(seed=0, n=50, p=8):
    rng = np.random.RandomState(seed)
    X = rng.randn(n, p)
    beta = np.array([3.0, -2.0, 1.5] + [0.0] * (p - 3))
    y = X @ beta + rng.randn(n)
    return X, y


# ---------------------------------------------------------------------------
# Validation (no R needed)
# ---------------------------------------------------------------------------

class TestValidation:
    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            rpm.pense(np.ones((5, 3)), np.ones(4))

    def test_1d_x(self):
        with pytest.raises(ValueError):
            rpm.pense(np.ones(10), np.ones(10))


# ---------------------------------------------------------------------------
# pense() path - strict tier
# ---------------------------------------------------------------------------

@needs_pense
class TestPensePath:
    @pytest.fixture
    def setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r("library(pense)")
        X, y = _make_data()
        ro.globalenv["Xp"] = X
        ro.globalenv["yp"] = y
        set_seed(1)
        py = rpm.pense(X, y, alpha=0.5, nlambda=10)
        ro.r("set.seed(1L); rfit <- pense(Xp, drop(yp), alpha=0.5, nlambda=10)")
        return py

    def test_lambda_path(self, setup, R):
        py = setup
        r_lam = np.asarray(R("rfit$lambda[[1]]"), dtype=float)
        np.testing.assert_array_equal(py.lambda_path, r_lam)

    def test_coefficients_matrix(self, setup, R):
        py = setup
        r_cm = np.asarray(
            R("sapply(rfit$lambda[[1]], function(L) as.numeric(coef(rfit, lambda=L)))"),
            dtype=float,
        )
        np.testing.assert_array_equal(py.coefficients, r_cm)

    def test_intercepts_view(self, setup):
        py = setup
        np.testing.assert_array_equal(py.intercepts, py.coefficients[0, :])

    def test_slopes_view(self, setup):
        py = setup
        np.testing.assert_array_equal(py.slopes, py.coefficients[1:, :])

    def test_alpha_bdp(self, setup, R):
        py = setup
        assert py.alpha == float(R("rfit$alpha")[0])
        assert py.bdp == float(R("rfit$bdp")[0])

    def test_coef_names(self, setup):
        py = setup
        assert py.coef_names[0] == "(Intercept)"
        assert len(py.coef_names) == py.coefficients.shape[0]

    def test_repr(self, setup):
        assert "PenseResult" in repr(setup)


# ---------------------------------------------------------------------------
# pense_cv() - strict tier
# ---------------------------------------------------------------------------

@needs_pense
class TestPenseCV:
    @pytest.fixture
    def setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r("library(pense)")
        X, y = _make_data()
        ro.globalenv["Xp"] = X
        ro.globalenv["yp"] = y
        set_seed(1)
        py = rpm.pense_cv(X, y, alpha=0.5, nlambda=10, cv_k=5, cv_repl=1)
        ro.r("set.seed(1L); rcv <- pense_cv(Xp, drop(yp), alpha=0.5, "
             "nlambda=10, cv_k=5, cv_repl=1)")
        return py

    def test_coef_min(self, setup, R):
        py = setup
        r_cmin = np.asarray(R("as.numeric(coef(rcv, lambda='min'))"), dtype=float)
        np.testing.assert_array_equal(py.coef_min, r_cmin)

    def test_cv_avg(self, setup, R):
        py = setup
        r_avg = np.asarray(R("rcv$cvres$cvavg"), dtype=float)
        np.testing.assert_array_equal(py.cv_avg, r_avg)

    def test_cv_se(self, setup, R):
        py = setup
        r_se = np.asarray(R("rcv$cvres$cvse"), dtype=float)
        np.testing.assert_array_equal(py.cv_se, r_se)

    def test_lambda_min(self, setup, R):
        py = setup
        r_lmin = float(R("rcv$cvres$lambda[which.min(rcv$cvres$cvavg)]")[0])
        assert py.lambda_min == r_lmin

    def test_cvres_dataframe(self, setup):
        py = setup
        assert {"cvavg", "cvse", "lambda"}.issubset(py.cvres.columns)
        assert len(py.cvres) == len(py.lambda_path)

    def test_repr(self, setup):
        assert "PenseCVResult" in repr(setup)


# ---------------------------------------------------------------------------
# Ergonomics installed on result classes
# ---------------------------------------------------------------------------

@needs_pense
def test_to_dict_works():
    X, y = _make_data()
    set_seed(1)
    pf = rpm.pense(X, y, nlambda=6)
    d = pf.to_dict()
    assert "coefficients" in d and "lambda_path" in d
