"""Strict-tier tests for the three robust logistic-regression wrappers."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


class TestValidation:
    def test_non_binary_y_raises(self):
        with pytest.raises(ValueError, match="binary"):
            rpm.by_logreg(np.ones((5, 2)), np.array([0, 1, 2, 0, 1]))

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            rpm.by_logreg(np.ones((5, 2)), np.array([0, 1, 0]))


@needs_r
def test_wby_logreg_separable_raises_clean():
    """B-009 regression guard: on perfectly separable data R's WBYlogreg returns
    a truncated object (no 'coefficients'); the wrapper must raise a clear
    RobStatTMRError, not an opaque rpy2 ``ValueError: x not in list``.
    """
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 1))
    y = (X[:, 0] > 0).astype(float)  # perfect separation
    rpm.set_seed(2)
    with pytest.raises(rpm.RobStatTMRError) as excinfo:
        rpm.wby_logreg(X, y)
    msg = str(excinfo.value)
    assert "usable fit" in msg
    assert "separable" in msg.lower()


@needs_r
class TestSkinDatasetVsR:
    """All three estimators on the skin dataset, strict-tier."""

    @pytest.fixture(scope="class")
    def r_setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r(
            "library(RobStatTM); data(skin); "
            "X_skin <- as.matrix(skin[, c('logVOL','logRATE')]); "
            "y_skin <- skin$vasoconst; "
            "by_r  <- BYlogreg(X_skin, y_skin); "
            "wby_r <- WBYlogreg(X_skin, y_skin); "
            "wml_r <- WMLlogreg(X_skin, y_skin)"
        )

    @pytest.fixture
    def inputs(self):
        df = rpm.datasets.skin()
        X = df[["logVOL", "logRATE"]].to_numpy(dtype=float)
        y = df["vasoconst"].to_numpy(dtype=float)
        return X, y

    @pytest.mark.parametrize(
        "py_fn, r_var",
        [
            ("by_logreg", "by_r"),
            ("wby_logreg", "wby_r"),
            ("wml_logreg", "wml_r"),
        ],
    )
    def test_coefficients(self, r_setup, inputs, R, py_fn, r_var):
        X, y = inputs
        py = getattr(rpm, py_fn)(X, y)
        r_coef = np.asarray(R(f"{r_var}$coefficients"), dtype=float)
        np.testing.assert_array_equal(py.coefficients, r_coef)

    @pytest.mark.parametrize(
        "py_fn, r_var",
        [
            ("by_logreg", "by_r"),
            ("wby_logreg", "wby_r"),
            ("wml_logreg", "wml_r"),
        ],
    )
    def test_fitted_values(self, r_setup, inputs, R, py_fn, r_var):
        X, y = inputs
        py = getattr(rpm, py_fn)(X, y)
        # BY/WBY return (1,n) row matrix in R; WML same. Python ravels to (n,)
        # per the user-facing API contract — values still bit-identical.
        r_fv = np.asarray(R(f"{r_var}$fitted.values"), dtype=float).ravel()
        np.testing.assert_array_equal(py.fitted_values, r_fv)
        # probabilities check
        assert (py.fitted_values >= 0).all() and (py.fitted_values <= 1).all()

    @pytest.mark.parametrize(
        "py_fn, r_var",
        [
            ("by_logreg", "by_r"),
            ("wby_logreg", "wby_r"),
            ("wml_logreg", "wml_r"),
        ],
    )
    def test_standard_deviation(self, r_setup, inputs, R, py_fn, r_var):
        X, y = inputs
        py = getattr(rpm, py_fn)(X, y)
        r_sd = np.asarray(R(f"{r_var}$standard.deviation"), dtype=float)
        np.testing.assert_array_equal(py.standard_deviation, r_sd)

    @pytest.mark.parametrize(
        "py_fn, r_var",
        [
            ("by_logreg", "by_r"),
            ("wby_logreg", "wby_r"),
            # WMLlogreg does not return an objective; skipped.
        ],
    )
    def test_objective(self, r_setup, inputs, R, py_fn, r_var):
        X, y = inputs
        py = getattr(rpm, py_fn)(X, y)
        assert py.objective == float(R(f"{r_var}$objective")[0])

    def test_wml_extra_fields(self, r_setup, inputs, R):
        """WMLlogreg returns xweights and cov (BY/WBY do not)."""
        X, y = inputs
        py = rpm.wml_logreg(X, y)
        # objective/converged not present in WML's R return list
        assert py.objective is None
        assert py.converged is None
        # xweights matches R's logical vector
        r_xw = np.asarray(R("wml_r$xweights"), dtype=bool).ravel()
        assert py.xweights is not None
        np.testing.assert_array_equal(py.xweights, r_xw)
        # cov matches R's matrix exactly
        r_cov = np.asarray(R("wml_r$cov"), dtype=float)
        assert py.cov is not None
        np.testing.assert_array_equal(py.cov, r_cov)

    def test_by_wby_have_objective_and_converged(self, r_setup, inputs, R):
        X, y = inputs
        for py_fn in ("by_logreg", "wby_logreg"):
            py = getattr(rpm, py_fn)(X, y)
            assert py.objective is not None
            assert py.converged is not None
            # xweights/cov are not in BY/WBY return list
            assert py.xweights is None
            assert py.cov is None


@needs_r
def test_repr():
    df = rpm.datasets.skin()
    X = df[["logVOL", "logRATE"]].to_numpy(dtype=float)
    y = df["vasoconst"].to_numpy(dtype=float)
    res = rpm.by_logreg(X, y)
    s = repr(res)
    assert "LogregResult" in s
    assert "BYlogreg" in s
