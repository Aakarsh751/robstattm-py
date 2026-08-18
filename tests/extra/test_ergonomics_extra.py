"""Result-object ergonomics across *every* result family.

``tests/test_ui_ergonomics.py`` exercises only ``LmrobdetMMResult``. Here we
check ``to_dict`` / ``_repr_html_`` / ``to_r`` / ``coef_df`` on the covariance,
PCA, GLM, univariate, and summary result types, plus pickle persistence, none
of which is covered there.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r

# --------------------------------------------------------------------------
# to_dict() contract holds for non-regression result types
# --------------------------------------------------------------------------


@needs_r
class TestToDictAcrossTypes:
    def test_cov_classic_to_dict(self):
        res = rpm.cov_classic(rpm.datasets.wine())
        d = res.to_dict()
        assert isinstance(d, dict)
        assert {"center", "cov"} <= set(d)
        assert not any(k.startswith("_") for k in d)
        assert isinstance(d["cov"], np.ndarray)

    def test_logreg_to_dict(self):
        rng = np.random.default_rng(0)
        X = rng.standard_normal((60, 2))
        y = (X[:, 0] + rng.standard_normal(60) > 0).astype(float)
        res = rpm.wml_logreg(X, y)
        d = res.to_dict()
        assert "coefficients" in d and "method" in d
        assert d["method"] == "WMLlogreg"

    def test_loc_scale_to_dict(self):
        x = np.concatenate([np.arange(20.0), [200.0]])
        d = rpm.loc_scale_m(x).to_dict()
        assert set(d) == {"mu", "std_mu", "disper"}

    def test_pca_to_dict(self):
        res = rpm.prcomp_rob(rpm.datasets.wine())
        d = res.to_dict()
        assert {"sdev", "rotation", "center", "scores"} <= set(d)


# --------------------------------------------------------------------------
# _repr_html_ returns a non-empty HTML string for every result + summary
# --------------------------------------------------------------------------


@needs_r
class TestReprHtmlAcrossTypes:
    @pytest.mark.parametrize(
        "factory",
        [
            lambda: rpm.cov_classic(rpm.datasets.wine()),
            lambda: rpm.cov_rob_mm(rpm.datasets.wine().iloc[:, :4]),
            lambda: rpm.prcomp_rob(rpm.datasets.wine()),
            lambda: rpm.loc_scale_m(np.arange(30.0)),
        ],
    )
    def test_result_repr_html(self, factory):
        rpm.set_seed(1)
        html = factory()._repr_html_()
        assert isinstance(html, str) and html.strip()

    def test_summary_repr_html(self):
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
        assert "<table" in fit.summary()._repr_html_()

    def test_cov_summary_repr_html(self):
        s = rpm.cov_classic(rpm.datasets.wine()).summary()
        html = s._repr_html_()
        assert "Eigenvalue" in html or "covariance" in html.lower()

    def test_prcomp_summary_repr_html(self):
        s = rpm.prcomp_rob(rpm.datasets.wine()).summary()
        assert "Importance" in s._repr_html_()

    def test_drop1_repr_html(self):
        fit = rpm.lmrobdet_mm(
            "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
            data=rpm.datasets.stackloss(),
        )
        assert "drop1" in fit.drop1()._repr_html_()


# --------------------------------------------------------------------------
# coef_df() works for every regression family that exposes it
# --------------------------------------------------------------------------


@needs_r
class TestCoefDf:
    def test_lmrob_m_coef_df(self):
        fit = rpm.lmrob_m("zinc ~ copper", data=rpm.datasets.mineral())
        s = fit.coef_df()
        assert isinstance(s, pd.Series)
        assert list(s.index) == list(fit.coef_names)

    def test_dcml_coef_df(self):
        fit = rpm.lmrobdet_dcml("zinc ~ copper", data=rpm.datasets.mineral())
        s = fit.coef_df()
        np.testing.assert_array_equal(s.to_numpy(), fit.coefficients)

    def test_logreg_coef_df_length(self):
        rng = np.random.default_rng(1)
        X = rng.standard_normal((50, 2))
        y = (X[:, 1] + rng.standard_normal(50) > 0).astype(float)
        s = rpm.wml_logreg(X, y).coef_df()
        assert len(s) == 3  # intercept + 2 slopes


# --------------------------------------------------------------------------
# to_r() now works for LocScaleMResult (regression guard for the fix)
# --------------------------------------------------------------------------


@needs_r
def test_loc_scale_to_r_roundtrips():
    res = rpm.loc_scale_m(np.arange(40.0))
    r_obj = res.to_r()
    assert r_obj is not None
    mod = type(r_obj).__module__
    assert "rpy2" in mod or "rlike" in mod


# --------------------------------------------------------------------------
# Pickle persistence: numeric fields survive a dumps/loads round-trip
# --------------------------------------------------------------------------


@needs_r
class TestPicklePersistence:
    def test_regression_fit_pickles(self):
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
        fit2 = pickle.loads(pickle.dumps(fit))
        np.testing.assert_array_equal(fit2.coefficients, fit.coefficients)
        assert fit2.scale == fit.scale
        assert fit2.coef_names == fit.coef_names

    def test_cov_result_pickles(self):
        res = rpm.cov_classic(rpm.datasets.wine())
        res2 = pickle.loads(pickle.dumps(res))
        np.testing.assert_array_equal(res2.cov, res.cov)
