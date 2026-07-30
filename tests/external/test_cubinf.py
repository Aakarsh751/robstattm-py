"""Strict-tier tests for cubinf vs direct R (robcbi package).

Reproduces the epilepsy.R CUBIF estimator (Example 7.3, Breslow data): a Poisson
GLM fit on the 5-column design matrix (explicit intercept), ``ufact=1.1``,
``null.dev=FALSE``. ``cubinf`` is deterministic.

Requires ``robcbi`` (+ its Fortran dependency ``robeth``); auto-skips otherwise.
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_breslow, needs_robcbi

_R_PREP = """
data(breslow.dat, package='robust')
yy <- breslow.dat[, 10]
xx1 <- breslow.dat[, 11]
xx2 <- breslow.dat[, 12]
xx3 <- breslow.dat[, 8]=="progabide"
xx4 <- xx2*xx3
XX <- cbind(rep(1,59), xx1, xx2, xx3, xx4)
colnames(XX) <- c("intercept","Age10","Base4","Progabide","interac.Base4-Progabide")
ctrl <- robcbi::cubinf.control(ufact=1.1)
rfit <- robcbi::cubinf(XX, yy, family=poisson(), null.dev=FALSE, control=ctrl)
"""


@needs_robcbi
@needs_breslow
class TestEpilepsyCUBIF:
    @pytest.fixture
    def setup(self, R):
        R(_R_PREP)
        XX = np.asarray(R("XX"), dtype=float)
        yy = np.asarray(R("as.numeric(yy)"), dtype=float)
        col_names = [str(c) for c in R("colnames(XX)")]
        import pandas as pd

        Xdf = pd.DataFrame(XX, columns=col_names)
        py = rpm.cubinf(Xdf, yy, family="poisson", intercept=False, null_dev=False, ufact=1.1)
        return py

    def test_coefficients(self, setup, R):
        np.testing.assert_array_equal(
            setup.coefficients, np.asarray(R("as.numeric(rfit$coefficients)"), dtype=float)
        )

    def test_std_errors(self, setup, R):
        np.testing.assert_array_equal(
            setup.std_errors, np.asarray(R("sqrt(diag(rfit$cov))"), dtype=float)
        )

    def test_fitted(self, setup, R):
        np.testing.assert_array_equal(
            setup.fitted_values, np.asarray(R("as.numeric(rfit$fitted.values)"), dtype=float)
        )

    def test_deviance_residuals(self, setup, R):
        # The wrapper's rsdev must equal R's rsdev bit-for-bit.
        np.testing.assert_array_equal(
            setup.deviance_residuals, np.asarray(R("as.numeric(rfit$rsdev)"), dtype=float)
        )

    def test_deviances_from_fitted_match_R(self, setup, R):
        # epilepsy.R recomputes deviance residuals from yy & fitted. Compute the
        # formula *in R* using the wrapper's fitted values pushed back, so the
        # comparison stays within one math library (strict tier).
        from robstattm_py._r import r as _r

        _r().globalenv["rpm_py_fitted"] = setup.fitted_values
        try:
            r_from_py = np.asarray(
                R("sign(yy-rpm_py_fitted)*sqrt(2*(yy*log(pmax(yy,1))-yy"
                  "-yy*log(rpm_py_fitted)+rpm_py_fitted))"),
                dtype=float,
            )
            r_from_r = np.asarray(
                R("sign(yy-rfit$fitted)*sqrt(2*(yy*log(pmax(yy,1))-yy"
                  "-yy*log(rfit$fitted)+rfit$fitted))"),
                dtype=float,
            )
        finally:
            _r().r("if (exists('rpm_py_fitted')) rm(rpm_py_fitted)")
        np.testing.assert_array_equal(r_from_py, r_from_r)

    def test_coef_count(self, setup):
        assert setup.coefficients.shape[0] == 5

    def test_repr(self, setup):
        assert "CubinfResult" in repr(setup)
