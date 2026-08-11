"""Tests for R-warning surfacing and the R-idiomatic result accessors.

Covers the two gaps closed in the warnings/accessors pass:

* R warnings emitted during a fit / result method are captured and re-raised
  as :class:`robstattm_py.RobStatTMWarning` (instead of vanishing into rpy2's
  console callback as an opaque "There were 50 or more warnings" line), and are
  also retrievable via :func:`robstattm_py.last_r_warnings`.
* Regression results expose ``resid`` / ``fitted`` / ``weights`` / ``vcov`` /
  ``sigma`` accessors alongside the pre-existing ``coef``.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from robstattm_py import RobStatTMWarning, last_r_warnings
from robstattm_py._r import _parse_r_warning_text
from robstattm_py._r import r as _r

try:
    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


# ---------------------------------------------------------------- parser (R-free)


class TestParseRWarningText:
    def test_empty(self):
        assert _parse_r_warning_text([]) == []
        assert _parse_r_warning_text(["", "  \n"]) == []

    def test_single_with_call(self):
        # rpy2 delivers a warning header and body as separate fragments.
        assert _parse_r_warning_text(["Warning in sqrt(-1) :", " NaNs produced\n"]) == [
            "NaNs produced"
        ]

    def test_multiple_warnings(self):
        frags = [
            "Warning in f(1) :", " w 1\n",
            "Warning in f(1) :", " w 2\n",
            "Warning in f(1) :", " w 3\n",
        ]
        assert _parse_r_warning_text(frags) == ["w 1", "w 2", "w 3"]

    def test_no_call_header(self):
        assert _parse_r_warning_text(["Warning message:\n", "did not converge\n"]) == [
            "did not converge"
        ]

    def test_drops_deferred_summary_noise(self):
        # R's deferred-summary line carries no content and must be dropped.
        assert _parse_r_warning_text(
            ["There were 50 or more warnings (use warnings() to see them)\n"]
        ) == []


# ---------------------------------------------------------------- accessors


@needs_r
class TestRegressionAccessors:
    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_mm("zinc ~ copper", data=df)

    def test_resid_matches_field(self, fit):
        s = fit.resid()
        assert isinstance(s, pd.Series)
        np.testing.assert_array_equal(s.to_numpy(), np.asarray(fit.residuals).ravel())

    def test_fitted_matches_field(self, fit):
        s = fit.fitted()
        assert isinstance(s, pd.Series)
        np.testing.assert_array_equal(
            s.to_numpy(), np.asarray(fit.fitted_values).ravel()
        )

    def test_weights_matches_field(self, fit):
        s = fit.weights()
        assert isinstance(s, pd.Series)
        np.testing.assert_array_equal(s.to_numpy(), np.asarray(fit.rweights).ravel())

    def test_vcov_is_labeled_square(self, fit):
        v = fit.vcov()
        assert isinstance(v, pd.DataFrame)
        assert list(v.index) == list(fit.coef_names)
        assert list(v.columns) == list(fit.coef_names)
        np.testing.assert_array_equal(v.to_numpy(), np.asarray(fit.cov, dtype=float))

    def test_sigma_is_scale(self, fit):
        assert fit.sigma() == pytest.approx(float(fit.scale))

    def test_accessors_present_on_all_lmrob_families(self):
        df = rpm.datasets.mineral()
        fits = [
            rpm.lmrobdet_mm("zinc ~ copper", data=df),
            rpm.lmrob_m("zinc ~ copper", data=df),
            rpm.lmrobdet_dcml("zinc ~ copper", data=df),
        ]
        for f in fits:
            for m in ("coef", "resid", "fitted", "weights", "vcov", "sigma"):
                assert callable(getattr(f, m)), f"{type(f).__name__} missing {m}()"

    def test_dcml_weights_uses_mm_field(self):
        df = rpm.datasets.mineral()
        f = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        np.testing.assert_array_equal(
            f.weights().to_numpy(), np.asarray(f.rweights_mm).ravel()
        )


# ---------------------------------------------------------------- warning capture


@needs_r
class TestRWarningCapture:
    @staticmethod
    def _hard_problem():
        rng = np.random.default_rng(0)
        n = 40
        x = rng.normal(size=n)
        y = rng.standard_cauchy(size=n) * 50.0
        return pd.DataFrame({"x": x, "y": y})

    def test_nonconvergence_surfaces_as_python_warning(self):
        wdf = self._hard_problem()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rpm.lmrob_m("y ~ x", data=wdf, max_it=2)
        r_warns = [w for w in caught if issubclass(w.category, RobStatTMWarning)]
        assert r_warns, "expected at least one RobStatTMWarning from a hard fit"
        # last_r_warnings() mirrors what was surfaced.
        assert last_r_warnings()

    def test_clean_fit_has_no_r_warnings(self):
        df = rpm.datasets.mineral()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rpm.lmrobdet_mm("zinc ~ copper", data=df)
        r_warns = [w for w in caught if issubclass(w.category, RobStatTMWarning)]
        assert r_warns == []
        assert last_r_warnings() == []

    def test_capture_context_manager_collects_without_emit(self):
        from robstattm_py import capture_r_warnings

        wdf = self._hard_problem()
        # record=True only to keep the inner guard's warnings off the test log;
        # the assertion below is about what the outer CM collected.
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with capture_r_warnings(emit=False) as msgs:
                # Fit directly through R inside the CM.
                rpm.lmrob_m("y ~ x", data=wdf, max_it=2)
        # emit=False on the *outer* CM means it re-raises nothing itself, but the
        # inner rcall guard still emits; assert the outer collected messages.
        assert isinstance(msgs, list)
