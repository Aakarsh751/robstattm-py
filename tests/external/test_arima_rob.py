"""Strict-tier tests for arima_rob vs direct R (robustarima package).

Covers the Chapter-8 example-script fits: resex (p=2 seasonal), ar3 (p=3),
MA1-AO (q=1), and the auto-AR identification path. ``arima.rob`` is
deterministic, so we reproduce each seeded ``arima.sim`` series in R, pull the
exact vector to Python, and assert bit-for-bit equality on both call paths.
"""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from tests.conftest import needs_robustarima


@needs_robustarima
class TestResex:
    """resex.R — robustarima::arima.rob(resex ~ 1, p=2, sd=1, sfreq=12)."""

    @pytest.fixture
    def setup(self, R):
        R("data(resex, package='RobStatTM')")
        R("rfit <- robustarima::arima.rob(resex ~ 1, p = 2, sd = 1, sfreq = 12)")
        y = np.asarray(R("as.numeric(resex)"), dtype=float)
        py = rpm.arima_rob(y=y, p=2, sd=1, sfreq=12)
        return py

    def test_ar(self, setup, R):
        np.testing.assert_array_equal(
            setup.ar, np.asarray(R("as.numeric(rfit$model$ar)"), dtype=float)
        )

    def test_regcoef(self, setup, R):
        np.testing.assert_array_equal(
            setup.regcoef, np.asarray(R("as.numeric(rfit$regcoef)"), dtype=float)
        )

    def test_sigma_innov(self, setup, R):
        assert setup.sigma_innov == float(R("rfit$sigma.innov")[0])

    def test_y_robust(self, setup, R):
        np.testing.assert_array_equal(
            setup.y_robust, np.asarray(R("as.numeric(rfit$y.robust)"), dtype=float)
        )

    def test_innov_tail(self, setup, R):
        # resex.R uses sort(abs(innov[15:89]))
        py_tail = np.sort(np.abs(setup.innov[14:89]))
        r_tail = np.asarray(R("sort(abs(rfit$innov[15:89]))"), dtype=float)
        np.testing.assert_array_equal(py_tail, r_tail)

    def test_regcoef_cov(self, setup, R):
        np.testing.assert_array_equal(
            setup.regcoef_cov.ravel(),
            np.asarray(R("as.numeric(rfit$regcoef.cov)"), dtype=float),
        )

    def test_seasonal_meta(self, setup):
        assert setup.sd == 1 and setup.sfreq == 12
        assert setup.ar.shape[0] == 2 and setup.ma.shape[0] == 0

    def test_repr(self, setup):
        assert "ArimaRobResult" in repr(setup)


@needs_robustarima
class TestAR3:
    """ar3.R — robustarima::arima.rob(ar3 ~ 1, p=3) on a seeded AR(3) simulation."""

    @pytest.fixture
    def setup(self, R):
        R(
            "set.seed(600); n.innov <- 300; n <- 200; phi <- c(4/3, -5/6, 1/6); "
            "innov <- rnorm(n.innov); "
            "ar3 <- arima.sim(model=list(ar=phi), n, innov=innov, n.start=n.innov-n)"
        )
        R("rfit <- robustarima::arima.rob(ar3 ~ 1, p = 3)")
        y = np.asarray(R("as.numeric(ar3)"), dtype=float)
        py = rpm.arima_rob(y=y, p=3)
        return py

    def test_ar(self, setup, R):
        np.testing.assert_array_equal(
            setup.ar, np.asarray(R("as.numeric(rfit$model$ar)"), dtype=float)
        )

    def test_regcoef(self, setup, R):
        np.testing.assert_array_equal(
            setup.regcoef, np.asarray(R("as.numeric(rfit$regcoef)"), dtype=float)
        )

    def test_order(self, setup):
        assert setup.ar.shape[0] == 3 and setup.ma.shape[0] == 0


@needs_robustarima
class TestMA1AO:
    """MA1-AO.R — robustarima::arima.rob(mac ~ 1, q=1) on a seeded MA(1)+AO simulation."""

    @pytest.fixture
    def setup(self, R):
        R(
            "set.seed(200); n.innov <- 300; n <- 200; theta <- -0.8; "
            "innov <- rnorm(n.innov); "
            "ma1 <- arima.sim(model=list(ma=theta), n=n, innov=innov, n.start=n.innov-n); "
            "mac <- ma1; mac[20*(1:10)] <- ma1[20*(1:10)] + 4"
        )
        R("rfit <- robustarima::arima.rob(mac ~ 1, q = 1)")
        y = np.asarray(R("as.numeric(mac)"), dtype=float)
        py = rpm.arima_rob(y=y, q=1)
        return py

    def test_ma(self, setup, R):
        np.testing.assert_array_equal(
            setup.ma, np.asarray(R("as.numeric(rfit$model$ma)"), dtype=float)
        )

    def test_y_robust(self, setup, R):
        np.testing.assert_array_equal(
            setup.y_robust, np.asarray(R("as.numeric(rfit$y.robust)"), dtype=float)
        )

    def test_order(self, setup):
        assert setup.ma.shape[0] == 1 and setup.ar.shape[0] == 0


@needs_robustarima
class TestAutoAR:
    """identAR2.R — robustarima::arima.rob(y ~ 1, auto.ar=TRUE) (may warn; numbers still match)."""

    @pytest.fixture
    def setup(self, R):
        R(
            "set.seed(700); n.innov <- 300; n <- 200; phi <- c(4/3, -5/6); "
            "innov <- rnorm(n.innov); "
            "x <- arima.sim(model=list(ar=phi), n, innov=innov, n.start=n.innov-n); "
            "ao <- ifelse(runif(n)>.1, 0, rnorm(n,4,1)); ao <- sign(runif(n,-1,1))*ao; "
            "y <- x + ao"
        )
        R("rfit <- suppressWarnings(robustarima::arima.rob(y ~ 1, auto.ar=TRUE))")
        y = np.asarray(R("as.numeric(y)"), dtype=float)
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            py = rpm.arima_rob(y=y, auto_ar=True)
        return py

    def test_selected_ar(self, setup, R):
        np.testing.assert_array_equal(
            setup.ar, np.asarray(R("as.numeric(rfit$model$ar)"), dtype=float)
        )

    def test_y_robust(self, setup, R):
        np.testing.assert_array_equal(
            setup.y_robust, np.asarray(R("as.numeric(rfit$y.robust)"), dtype=float)
        )


@needs_robustarima
class TestValidation:
    def test_requires_exactly_one_input(self):
        with pytest.raises(ValueError):
            rpm.arima_rob(p=2)
        with pytest.raises(ValueError):
            rpm.arima_rob(formula="y ~ 1", y=np.arange(10.0))
