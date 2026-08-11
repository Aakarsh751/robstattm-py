"""R's integer NA must not arrive as the number -2147483648.

R stores integer ``NA`` as ``INT_MIN``. rpy2's pandas conversion maps an R
integer column to numpy ``int32``, which has no missing value, so the sentinel
came through as an ordinary datum: no error, no warning, and every subsequent
number wrong. ``mean()`` was off, ``dropna()`` dropped nothing, ``min()``
returned -2147483648.

Found through ``WWGbook::autism``, where two missing ``vsae`` scores turned a
41-child complete-case subset into 42 and surfaced only as a length-mismatch
complaint from the estimator, several steps removed from the cause.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from robstattm_py.datasets import _R_INT_NA, _restore_integer_na

try:
    from robstattm_py._r import r as _r

    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


class TestRestoreIntegerNa:
    """No R required — the repair is a pure DataFrame transformation."""

    def test_sentinel_becomes_missing(self):
        df = pd.DataFrame({"x": np.array([1, _R_INT_NA, 3], dtype="int32")})
        out = _restore_integer_na(df.copy())
        assert out["x"].isna().tolist() == [False, True, False]
        assert out["x"].dropna().tolist() == [1, 3]

    def test_integrality_is_preserved(self):
        df = pd.DataFrame({"x": np.array([1, _R_INT_NA], dtype="int32")})
        # Int64, not float64 — a count column should stay a count column.
        assert str(_restore_integer_na(df.copy())["x"].dtype) == "Int64"

    def test_clean_integer_column_is_untouched(self):
        df = pd.DataFrame({"x": np.array([1, 2, 3], dtype="int32")})
        out = _restore_integer_na(df.copy())
        assert str(out["x"].dtype) == "int32"
        assert out["x"].tolist() == [1, 2, 3]

    def test_float_and_object_columns_are_untouched(self):
        df = pd.DataFrame(
            {"f": [1.0, np.nan], "s": ["a", "b"], "i": np.array([1, 2], dtype="int32")}
        )
        out = _restore_integer_na(df.copy())
        assert out["f"].isna().tolist() == [False, True]
        assert out["s"].tolist() == ["a", "b"]

    def test_a_legitimate_int_min_would_be_lost(self):
        """Document the one case this cannot distinguish.

        R gives us no way to tell a genuine ``-2147483648`` from ``NA`` after
        conversion, because they are the same bits. No real dataset stores that
        value, but the limitation is real and should be visible rather than
        discovered.
        """
        df = pd.DataFrame({"x": np.array([_R_INT_NA], dtype="int32")})
        assert _restore_integer_na(df.copy())["x"].isna().all()


@needs_r
class TestAgainstR:
    def test_autism_missing_count_matches_r(self):
        """The dataset that exposed this: two missing vsae scores."""
        import robstattm_py as rpm
        from robstattm_py._r import r

        pytest.importorskip("rpy2")
        ro = r()
        if not bool(ro.r("isTRUE(requireNamespace('WWGbook', quietly=TRUE))")[0]):
            pytest.skip("R package WWGbook not installed")

        df = rpm.datasets.load("WWGbook", "autism")
        ro.r('data(autism, package="WWGbook")')
        try:
            r_na = {
                str(name): int(count)
                for name, count in zip(
                    ro.r("names(autism)"),
                    ro.r("sapply(autism, function(c) sum(is.na(c)))"),
                    strict=True,
                )
            }
        finally:
            ro.r('if (exists("autism")) rm(list="autism")')

        py_na = {c: int(df[c].isna().sum()) for c in df.columns}
        assert py_na == r_na
        # And the corrupted value is gone.
        assert df["vsae"].min() > 0

    def test_complete_case_subset_size_matches_r(self):
        """41 children with five observations each, as autism.R states."""
        import robstattm_py as rpm
        from robstattm_py._r import r

        ro = r()
        if not bool(ro.r("isTRUE(requireNamespace('WWGbook', quietly=TRUE))")[0]):
            pytest.skip("R package WWGbook not installed")

        df = rpm.datasets.load("WWGbook", "autism").dropna()
        counts = df["childid"].value_counts()
        assert int((counts == 5).sum()) == 41
