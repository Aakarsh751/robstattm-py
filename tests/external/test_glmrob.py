"""Strict-tier tests for glmrob vs direct R (robustbase package).

Reproduces the epilepsy.R robust GLM estimators (Example 7.3, Breslow data):
the RQL/Mqle fit (default method) and the MT fit, both Poisson. ``glmrob`` is
deterministic for these methods, so no seeding is needed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_glmrob

_FORMULA = "yy ~ xx1 + xx2 + xx3 + xx4"

_R_PREP = """
data(breslow.dat, package='robust')
yy <- breslow.dat[, 10]
xx1 <- breslow.dat[, 11]
xx2 <- breslow.dat[, 12]
xx3 <- breslow.dat[, 8]=="progabide"
xx4 <- xx2*xx3
"""


def _pull_df(R) -> pd.DataFrame:
    """Pull the epilepsy design columns from R into a DataFrame (xx3 logical)."""
    return pd.DataFrame(
        {
            "yy": np.asarray(R("as.numeric(yy)"), dtype=float),
            "xx1": np.asarray(R("as.numeric(xx1)"), dtype=float),
            "xx2": np.asarray(R("as.numeric(xx2)"), dtype=float),
            "xx3": np.asarray(R("as.logical(xx3)"), dtype=bool),
            "xx4": np.asarray(R("as.numeric(xx4)"), dtype=float),
        }
    )


@needs_glmrob
class TestEpilepsyRQL:
    """RQL / Mqle fit (default method)."""

    @pytest.fixture
    def setup(self, R):
        R(_R_PREP)
        R(f"rfit <- robustbase::glmrob({_FORMULA}, family=poisson)")
        df = _pull_df(R)
        py = rpm.glmrob(_FORMULA, df, family="poisson")
        return py

    def test_coefficients(self, setup, R):
        np.testing.assert_array_equal(
            setup.coefficients, np.asarray(R("as.numeric(rfit$coefficients)"), dtype=float)
        )

    def test_std_errors(self, setup, R):
        np.testing.assert_array_equal(
            setup.std_errors, np.asarray(R("sqrt(diag(rfit$cov))"), dtype=float)
        )

    def test_residuals(self, setup, R):
        np.testing.assert_array_equal(
            setup.residuals, np.asarray(R("as.numeric(residuals(rfit))"), dtype=float)
        )

    def test_fitted(self, setup, R):
        np.testing.assert_array_equal(
            setup.fitted_values, np.asarray(R("as.numeric(rfit$fitted.values)"), dtype=float)
        )

    def test_method(self, setup):
        assert setup.method == "Mqle"
        assert setup.coefficients.shape[0] == 5

    def test_coef_names(self, setup, R):
        assert setup.coef_names == tuple(str(n) for n in R("names(rfit$coefficients)"))

    def test_repr(self, setup):
        assert "GlmrobResult" in repr(setup)


@needs_glmrob
class TestEpilepsyMT:
    """MT fit (method='MT')."""

    @pytest.fixture
    def setup(self, R):
        # method="MT" is stochastic (random subsamples) but seed-reproducible,
        # so seed both sides identically immediately before the fit.
        R(_R_PREP)
        R(f"set.seed(11L); rfitMT <- robustbase::glmrob({_FORMULA}, family=poisson, method='MT')")
        df = _pull_df(R)
        set_seed(11)
        py = rpm.glmrob(_FORMULA, df, family="poisson", method="MT")
        return py

    def test_coefficients(self, setup, R):
        np.testing.assert_array_equal(
            setup.coefficients, np.asarray(R("as.numeric(rfitMT$coefficients)"), dtype=float)
        )

    def test_std_errors(self, setup, R):
        np.testing.assert_array_equal(
            setup.std_errors, np.asarray(R("sqrt(diag(rfitMT$cov))"), dtype=float)
        )

    def test_method(self, setup):
        assert setup.method == "MT"


@needs_glmrob
class TestValidation:
    def test_bad_family_raises(self):
        with pytest.raises(ValueError):
            rpm.glmrob("y ~ x", pd.DataFrame({"y": [1.0], "x": [1.0]}), family="gaussian")
