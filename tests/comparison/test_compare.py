"""Tests for compare() -- the fit.models side-by-side facade."""
from __future__ import annotations

import importlib.util

import pytest

import robstattm_py as rpm
from tests.conftest import needs_r

needs_fitmodels = pytest.mark.skipif(
    importlib.util.find_spec("fitmodels_py") is None,
    reason="sibling package fitmodels-py not installed",
)


class TestErrors:
    def test_empty(self):
        with pytest.raises(ValueError):
            rpm.compare()

    @needs_r
    def test_unsupported_type_message(self):
        # A univariate location/scale fit is neither regression nor covariance.
        loc = rpm.loc_scale_m([1.0, 2.0, 3.0, 4.0, 100.0])
        with pytest.raises(NotImplementedError):
            rpm.compare(a=loc)

    @needs_r
    @needs_fitmodels
    def test_cannot_mix_cov_and_regression(self):
        df = rpm.datasets.mineral()
        cc = rpm.cov_classic(df)
        ls = rpm.lm("zinc ~ copper", data=df)
        with pytest.raises(ValueError):
            rpm.compare(cov=cc, reg=ls)


@needs_r
@needs_fitmodels
class TestCompareLmVsRobust:
    @pytest.fixture(scope="class")
    def cmp(self):
        rpm.set_seed(1)
        df = rpm.datasets.mineral()
        ls = rpm.lm("zinc ~ copper", data=df)
        rob = rpm.lmrobdet_mm("zinc ~ copper", data=df)
        return rpm.compare(LeastSquares=ls, Robust=rob)

    def test_labels_present_in_summary(self, cmp):
        text = str(cmp.summary())
        assert "LeastSquares" in text and "Robust" in text

    def test_clean_calls_no_inline_data(self, cmp):
        # The estimator path records readable calls, not a deparsed data frame.
        text = str(cmp)
        assert "data = data" in text
        assert "c(102" not in text  # would appear if the frame were deparsed

    def test_indexing(self, cmp):
        assert list(cmp.models) == ["LeastSquares", "Robust"]

    def test_summary_has_both_coefficient_rows(self, cmp):
        table = str(cmp.summary())
        assert "copper" in table and "(Intercept)" in table

    def test_ls_coefficient_appears(self, cmp):
        # The LS intercept (7.96063 from the vignette) shows in the joined table.
        assert "7.96" in str(cmp.summary())

    def test_coef_and_residuals_surface(self, cmp):
        coefs = cmp.coef()
        assert list(coefs.index) == ["LeastSquares", "Robust"]
        assert set(cmp.residuals()) == {"LeastSquares", "Robust"}
        assert set(cmp.fitted()) == {"LeastSquares", "Robust"}


@needs_r
@needs_fitmodels
class TestCompareFitFromNames:
    """lm vs a model fitmodels-py has no estimator for (ltsReg -> class 'lts')."""

    def test_lm_vs_lts_builds_lmfm(self):
        rpm.set_seed(3)
        df = rpm.datasets.mineral()
        cmp = rpm.compare(
            LS=rpm.lm("zinc ~ copper", data=df),
            LTS=rpm.lts_reg("zinc ~ copper", data=df),
        )
        assert cmp.fm_class == "lmfm"
        assert list(cmp.models) == ["LS", "LTS"]


@needs_r
@needs_fitmodels
class TestCompareCovfm:
    @pytest.fixture(scope="class")
    def cmp(self):
        wine3 = rpm.datasets.wine().iloc[:, :3]
        return rpm.compare(
            Classical=rpm.cov_classic(wine3), Robust=rpm.cov_rob(wine3)
        )

    def test_is_covfm(self, cmp):
        assert cmp.fm_class == "covfm"
        assert list(cmp.models) == ["Classical", "Robust"]

    def test_center_and_cov_surface(self, cmp):
        center = cmp.center()
        assert list(center.index) == ["Classical", "Robust"]
        assert set(cmp.cov()) == {"Classical", "Robust"}

    def test_summary_lines_up_both(self, cmp):
        text = str(cmp.summary())
        assert "Classical" in text and "Robust" in text
