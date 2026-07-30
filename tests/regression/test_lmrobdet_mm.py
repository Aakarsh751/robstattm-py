"""Strict-tier tests for robstattm_py.lmrobdet_mm vs direct R."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_non_str_formula(self):
        with pytest.raises(TypeError):
            rpm.lmrobdet_mm(123, data=pd.DataFrame({"a": [1, 2]}))  # type: ignore[arg-type]

    def test_non_df_data(self):
        with pytest.raises(TypeError):
            rpm.lmrobdet_mm("y ~ x", data=[[1, 2], [3, 4]])  # type: ignore[arg-type]

    def test_empty_df(self):
        with pytest.raises(ValueError):
            rpm.lmrobdet_mm("y ~ x", data=pd.DataFrame())


# ---------------------------------------------------------------------------
# lmrobdet_control validation
# ---------------------------------------------------------------------------

class TestControl:
    def test_default_construction(self):
        ctrl = rpm.lmrobdet_control()
        assert ctrl.family == "mopt"
        assert ctrl.efficiency == 0.95

    def test_unknown_kwarg_raises(self):
        with pytest.raises(TypeError, match="unknown"):
            rpm.lmrobdet_control(no_such_arg=1)

    def test_override(self):
        ctrl = rpm.lmrobdet_control(family="bisquare", efficiency=0.85)
        assert ctrl.family == "bisquare"
        assert ctrl.efficiency == 0.85


# ---------------------------------------------------------------------------
# Strict-tier comparison vs direct R — flagship test on `mineral`
# ---------------------------------------------------------------------------

@needs_r
class TestMineralVsR:
    """Field-by-field comparison of lmrobdet_mm vs direct R on mineral dataset."""

    @pytest.fixture(autouse=True)
    def _r_setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral); "
             "rpm_check_fit <- lmrobdetMM(zinc ~ copper, data=mineral)")
        yield
        ro.r("rm(rpm_check_fit)")

    @pytest.fixture
    def py(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_mm("zinc ~ copper", data=df)

    def test_coefficients(self, py, R):
        r_coef = np.asarray(R("coef(rpm_check_fit)"), dtype=float)
        np.testing.assert_array_equal(py.coefficients, r_coef)

    def test_scale(self, py, R):
        assert py.scale == float(R("rpm_check_fit$scale")[0])

    def test_loss(self, py, R):
        assert py.loss == float(R("rpm_check_fit$loss")[0])

    def test_iter(self, py, R):
        assert py.iter == int(R("rpm_check_fit$iter")[0])

    def test_converged(self, py, R):
        assert py.converged == bool(R("rpm_check_fit$converged")[0])

    def test_rank(self, py, R):
        assert py.rank == int(R("rpm_check_fit$rank")[0])

    def test_df_residual(self, py, R):
        assert py.df_residual == int(R("rpm_check_fit$df.residual")[0])

    def test_r_squared(self, py, R):
        assert py.r_squared == float(R("rpm_check_fit$r.squared")[0])

    def test_adj_r_squared(self, py, R):
        assert py.adj_r_squared == float(R("rpm_check_fit$adj.r.squared")[0])

    def test_residuals(self, py, R):
        np.testing.assert_array_equal(
            py.residuals, np.asarray(R("rpm_check_fit$residuals"), dtype=float)
        )

    def test_fitted_values(self, py, R):
        np.testing.assert_array_equal(
            py.fitted_values,
            np.asarray(R("rpm_check_fit$fitted.values"), dtype=float),
        )

    def test_rweights(self, py, R):
        np.testing.assert_array_equal(
            py.rweights, np.asarray(R("rpm_check_fit$rweights"), dtype=float)
        )

    def test_cov(self, py, R):
        np.testing.assert_array_equal(
            py.cov, np.asarray(R("rpm_check_fit$cov"), dtype=float)
        )

    def test_coef_names(self, py):
        assert py.coef_names == ("(Intercept)", "copper")


# ---------------------------------------------------------------------------
# Repr + helpers
# ---------------------------------------------------------------------------

@needs_r
def test_repr_is_informative():
    df = rpm.datasets.mineral()
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    s = repr(fit)
    assert "zinc ~ copper" in s
    assert "copper" in s
    assert "scale" in s


@needs_r
def test_coef_returns_named_series():
    df = rpm.datasets.mineral()
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    s = fit.coef()
    assert isinstance(s, pd.Series)
    assert list(s.index) == ["(Intercept)", "copper"]


# ---------------------------------------------------------------------------
# family / efficiency kwargs override control
# ---------------------------------------------------------------------------

@needs_r
@pytest.mark.parametrize("family", ["mopt", "bisquare"])
@pytest.mark.parametrize("efficiency", [0.85, 0.95])
def test_family_efficiency_kwargs(R, family, efficiency):
    from robstattm_py._r import r

    ro = r()
    ro.r("library(RobStatTM); data(mineral)")
    df = rpm.datasets.mineral()
    py = rpm.lmrobdet_mm(
        "zinc ~ copper", data=df, family=family, efficiency=efficiency
    )
    r_coef = np.asarray(
        ro.r(
            f"coef(lmrobdetMM(zinc ~ copper, data=mineral, "
            f"control=lmrobdet.control(family='{family}', efficiency={efficiency})))"
        ),
        dtype=float,
    )
    np.testing.assert_array_equal(py.coefficients, r_coef)


# ---------------------------------------------------------------------------
# Multi-variable formula
# ---------------------------------------------------------------------------

@needs_r
def test_multi_variable_formula(R):
    from robstattm_py._r import r

    ro = r()
    ro.r("library(RobStatTM); data(stackloss)")
    df = rpm.datasets.stackloss()
    py = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df)
    r_coef = np.asarray(
        ro.r("coef(lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., "
             "data=stackloss))"),
        dtype=float,
    )
    np.testing.assert_array_equal(py.coefficients, r_coef)
    assert py.coef_names == ("(Intercept)", "Air.Flow", "Water.Temp", "Acid.Conc.")
