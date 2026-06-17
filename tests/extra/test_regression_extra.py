"""Regression: formula-shape variety + method parity not covered elsewhere.

``tests/regression/*`` covers the flagship ``zinc ~ copper`` path and S3 methods
on ``LmrobdetMMResult``. Here: no-intercept formulas, multi-predictor (X, y),
headline-kwarg control parity for ``lmrob_m``, and predict()/coef() on the DCML
and lmrobM families.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm
from tests.conftest import needs_r


@needs_r
class TestNoInterceptFormula:
    def test_coef_names_drop_intercept(self):
        fit = rpm.lmrobdet_mm("zinc ~ -1 + copper", data=rpm.datasets.mineral())
        assert fit.coef_names == ("copper",)
        assert fit.coefficients.shape == (1,)

    def test_iters_const_none_when_absent(self):
        """R omits ``iters.const`` for no-intercept fits; the wrapper must
        return ``None`` rather than crash with an opaque rpy2 error."""
        fit = rpm.lmrobdet_mm("zinc ~ -1 + copper", data=rpm.datasets.mineral())
        assert fit.iters_const is None

    def test_no_intercept_parity(self, R):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral)")
        py = rpm.lmrobdet_mm("zinc ~ -1 + copper", data=rpm.datasets.mineral())
        r_coef = np.asarray(
            ro.r("coef(lmrobdetMM(zinc ~ -1 + copper, data=mineral))"), dtype=float
        )
        np.testing.assert_array_equal(py.coefficients, r_coef)


@needs_r
class TestMultiPredictorArrayForm:
    def test_xy_multipredictor_matches_formula(self):
        df = rpm.datasets.stackloss()
        formula_fit = rpm.lmrobdet_mm(
            "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df
        )
        # Dataset columns are Python-safe (R dots -> underscores).
        X = df[["Air_Flow", "Water_Temp", "Acid_Conc_"]].to_numpy()
        y = df["stack_loss"].to_numpy()
        xy_fit = rpm.lmrobdet_mm(X=X, y=y)
        np.testing.assert_array_equal(xy_fit.coefficients, formula_fit.coefficients)
        # generated predictor names for a bare ndarray
        assert xy_fit.coef_names == ("(Intercept)", "x0", "x1", "x2")


@needs_r
class TestLmrobMHeadlineKwargs:
    @pytest.mark.parametrize("family", ["bisquare", "opt"])
    def test_family_kwarg_parity(self, family, R):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral)")
        py = rpm.lmrob_m("zinc ~ copper", data=rpm.datasets.mineral(), family=family)
        r_coef = np.asarray(
            ro.r(
                f"coef(lmrobM(zinc ~ copper, data=mineral, "
                f"control=lmrobM.control(family='{family}')))"
            ),
            dtype=float,
        )
        np.testing.assert_array_equal(py.coefficients, r_coef)

    def test_cannot_mix_control_and_kwargs(self):
        df = rpm.datasets.mineral()
        ctrl = rpm.lmrobm_control(efficiency=0.9)
        with pytest.raises(TypeError, match="Cannot mix"):
            rpm.lmrob_m("zinc ~ copper", data=df, control=ctrl, family="bisquare")


@needs_r
class TestPredictAndCoefDCML:
    @pytest.fixture(scope="class")
    def df(self):
        return rpm.datasets.mineral()

    def test_predict_default_equals_fitted(self, df):
        fit = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        np.testing.assert_allclose(fit.predict(), fit.fitted_values, rtol=1e-9)

    def test_predict_newdata_parity(self, df):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(mineral)")
        fit = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        new = pd.DataFrame({"copper": [5.0, 15.0, 25.0]})
        py_pred = fit.predict(new)
        r_pred = np.asarray(
            ro.r(
                "predict(lmrobdetDCML(zinc ~ copper, data=mineral), "
                "newdata=data.frame(copper=c(5,15,25)))"
            ),
            dtype=float,
        ).ravel()
        np.testing.assert_array_equal(py_pred, r_pred)

    def test_coef_and_coef_df_series(self, df):
        fit = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        for s in (fit.coef(), fit.coef_df()):
            assert isinstance(s, pd.Series)
            assert list(s.index) == ["(Intercept)", "copper"]


@needs_r
def test_coef_uniform_across_regression_families():
    """coef() is now available on all three regression result types (the
    result-methods guide documents it for the whole family)."""
    df = rpm.datasets.mineral()
    for fit in (
        rpm.lmrobdet_mm("zinc ~ copper", data=df),
        rpm.lmrobdet_dcml("zinc ~ copper", data=df),
        rpm.lmrob_m("zinc ~ copper", data=df),
    ):
        s = fit.coef()
        assert isinstance(s, pd.Series)
        assert list(s.index) == ["(Intercept)", "copper"]


@needs_r
class TestLmrobMPredictHatvalues:
    @pytest.fixture(scope="class")
    def fit(self):
        return rpm.lmrob_m("zinc ~ copper", data=rpm.datasets.mineral())

    def test_predict_in_sample_matches_fitted(self, fit):
        np.testing.assert_allclose(fit.predict(), fit.fitted_values, rtol=1e-9)

    def test_hatvalues_nonnegative_and_sized(self, fit):
        h = fit.hatvalues()
        assert h.shape == (53,)
        assert (h >= 0).all()
