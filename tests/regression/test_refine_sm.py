"""Tests for ``refine_sm``, strict-tier vs R."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from robstattm_py._r import r as _r

try:
    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


@needs_r
class TestRefineSMBisquare:
    """Generate the data inside R, lift it into Python for the wrapper call,
    and assert bit-equality against R's own refine.sm output."""

    @pytest.fixture(scope="class")
    def r_setup(self):
        ro = _r()
        ro.r("""
            library(RobStatTM)
            set.seed(0)
            rpm_test_X   <- matrix(rnorm(50*2), 50, 2)
            rpm_test_y   <- as.numeric(rpm_test_X %*% c(1,2)) + rnorm(50)*0.5
            rpm_test_b   <- bisquare(0.5)
            rpm_test_cc  <- bisquare(0.85)
            rpm_test_b0  <- c(0.9, 1.9)
        """)
        # Sanity: confirm dimensions on the R side before calling refine.sm.
        dim_X = list(ro.r("dim(rpm_test_X)"))
        assert dim_X == [50, 2], f"R sees rpm_test_X as dim={dim_X}"
        ro.r("""
            rpm_test_res <- refine.sm(x=rpm_test_X, y=rpm_test_y,
                                      initial.beta=rpm_test_b0,
                                      initial.scale=0.5,
                                      b=rpm_test_b, cc=rpm_test_cc,
                                      family='bisquare', tol=1e-7)
        """)
        yield ro
        ro.r(
            "for (v in c('rpm_test_X','rpm_test_y','rpm_test_b','rpm_test_cc',"
            "'rpm_test_b0','rpm_test_res')) if (exists(v)) rm(list=v)"
        )

    @pytest.fixture(scope="class")
    def py_call(self, r_setup):
        X = np.asarray(r_setup.r("rpm_test_X"), dtype=float)
        y = np.asarray(r_setup.r("rpm_test_y"), dtype=float).ravel()
        b = float(r_setup.r("rpm_test_b")[0])
        cc = float(r_setup.r("rpm_test_cc")[0])
        res = rpm.refine_sm(
            X, y, initial_beta=[0.9, 1.9], initial_scale=0.5,
            b=b, cc=cc, family="bisquare", tol=1e-7,
        )
        return res

    def test_beta_strict(self, py_call, r_setup):
        r_beta = np.asarray(r_setup.r("rpm_test_res$beta.rw"), dtype=float).ravel()
        np.testing.assert_array_equal(py_call.beta, r_beta)

    def test_scale_strict(self, py_call, r_setup):
        r_scale = float(r_setup.r("rpm_test_res$scale.rw")[0])
        assert py_call.scale == r_scale

    def test_converged_and_iterations(self, py_call, r_setup):
        r_conv = bool(r_setup.r("rpm_test_res$converged")[0])
        r_iter = int(r_setup.r("rpm_test_res$iterations")[0])
        assert py_call.converged == r_conv
        assert py_call.iterations == r_iter

    def test_repr_contains_size(self, py_call):
        assert "p=2" in repr(py_call)
        assert "converged" in repr(py_call)


@needs_r
def test_refine_sm_validates_inputs():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((10, 2))
    y = rng.standard_normal(10)
    # wrong beta length
    with pytest.raises(ValueError, match="initial_beta has length"):
        rpm.refine_sm(
            X, y, initial_beta=[1.0], initial_scale=1.0,
            b=0.5, cc=1.5, family="bisquare", tol=1e-7,
        )
    # mismatched X / y
    with pytest.raises(ValueError, match="rows but y has length"):
        rpm.refine_sm(
            X, y[:-1], initial_beta=[1.0, 2.0], initial_scale=1.0,
            b=0.5, cc=1.5, family="bisquare", tol=1e-7,
        )
    # X must be 2D
    with pytest.raises(ValueError, match="X must be 2-D"):
        rpm.refine_sm(
            X.ravel(), y, initial_beta=[1.0], initial_scale=1.0,
            b=0.5, cc=1.5, family="bisquare", tol=1e-7,
        )
