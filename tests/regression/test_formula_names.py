"""A formula may use the column names the caller can actually see.

Our dataset loaders rename R's dotted columns for Python (``n.shocks`` becomes
``n_shocks``), but the frame is pushed to R under its original names. Before
``formula_to_r_names`` the obvious call, read the frame, look at
``df.columns``, write a formula using what you saw, failed with R's
``object 'n_shocks' not found``, naming something the caller never typed.

Both spellings must work, and must give the same fit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from robstattm_py.regression._formula import formula_to_r_names, r_name_map

try:
    from robstattm_py._r import r as _r

    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


class TestRewriteIsPure:
    """No R needed: the rewrite is a pure string transformation."""

    def _frame(self) -> pd.DataFrame:
        df = pd.DataFrame({"n_shocks": [1.0, 2.0], "time": [3.0, 4.0]})
        df.attrs["r_columns"] = ("n.shocks", "time")
        return df

    def test_python_name_is_rewritten(self):
        assert formula_to_r_names("time ~ n_shocks", self._frame()) == "time ~ n.shocks"

    def test_r_name_is_left_alone(self):
        assert formula_to_r_names("time ~ n.shocks", self._frame()) == "time ~ n.shocks"

    def test_dot_formula_is_untouched(self):
        # `y ~ .` must not acquire an expanded column list.
        assert formula_to_r_names("time ~ .", self._frame()) == "time ~ ."

    def test_frame_without_r_columns_is_untouched(self):
        plain = pd.DataFrame({"n_shocks": [1.0], "time": [2.0]})
        assert formula_to_r_names("time ~ n_shocks", plain) == "time ~ n_shocks"
        assert r_name_map(plain) == {}

    def test_only_whole_identifiers_are_replaced(self):
        # A longer name that merely contains a mapped one must survive.
        df = pd.DataFrame({"n_shocks": [1.0], "n_shocks_lagged": [1.0], "time": [2.0]})
        df.attrs["r_columns"] = ("n.shocks", "n.shocks.lagged", "time")
        assert (
            formula_to_r_names("time ~ n_shocks + n_shocks_lagged", df)
            == "time ~ n.shocks + n.shocks.lagged"
        )

    def test_mismatched_attrs_are_ignored(self):
        # A stale r_columns of the wrong length must not corrupt the formula.
        df = pd.DataFrame({"n_shocks": [1.0], "time": [2.0]})
        df.attrs["r_columns"] = ("n.shocks",)
        assert formula_to_r_names("time ~ n_shocks", df) == "time ~ n_shocks"


@needs_r
class TestBothSpellingsFitIdentically:
    def test_lmrob_m_shock(self):
        shock = rpm.datasets.shock()
        assert "n_shocks" in shock.columns  # the name a caller would see

        py_spelling = rpm.lmrob_m("time ~ n_shocks", data=shock)
        r_spelling = rpm.lmrob_m("time ~ n.shocks", data=shock)

        np.testing.assert_array_equal(
            py_spelling.coefficients, r_spelling.coefficients
        )
        assert py_spelling.coef_names == r_spelling.coef_names

    def test_lmrobdet_mm_shock(self):
        shock = rpm.datasets.shock()
        fit = rpm.lmrobdet_mm("time ~ n_shocks", data=shock)
        assert fit.coef_names == ("(Intercept)", "n.shocks")

    def test_dot_formula_still_expands(self):
        # `.` must reach R intact. algae has factor columns, so the expanded
        # coefficient count exceeds the column count - the point is only that
        # the dot expanded at all rather than being mangled by the rewrite.
        algae = rpm.datasets.algae()
        fit = rpm.lmrobdet_mm("V12 ~ .", data=algae)
        assert fit.coef_names[0] == "(Intercept)"
        assert len(fit.coef_names) >= algae.shape[1]
        # (Don't assert the response is absent from the names: algae's factor
        # columns expand to level-suffixed labels - V1 level 2 is "V12", which
        # collides with the response name by coincidence.)
