"""Strict-tier tests for drop1.lmrobdetMM (port of R's drop1.lmrobdetMM).

Each test seeds Python and R identically before fitting, because the MM fit
that ``drop1`` recomputes for every dropped term is stochastic. With matched
seeds the Python ``fit.drop1()`` output is bit-identical to a direct
``set.seed(N); drop1(lmrobdetMM(...))`` in R.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from robstattm_py import drop1_lmrobdet
from robstattm_py.regression._s3_methods import Drop1Result
from tests.conftest import needs_r


def _r_drop1(setup_code: str, drop_call: str):
    """Run an R drop1 and return (rownames, Df, RFPE)."""
    from robstattm_py._r import r

    ro = r()
    ro.r("suppressMessages(library(RobStatTM))")
    ro.r(setup_code)
    ro.r(f"rpm_aod <- {drop_call}")
    terms = tuple(str(t) for t in ro.r("rownames(rpm_aod)"))
    df = np.asarray(ro.r("as.numeric(rpm_aod$Df)"), dtype=float).ravel()
    rfpe = np.asarray(ro.r("as.numeric(rpm_aod$RFPE)"), dtype=float).ravel()
    ro.r("rm(list=intersect(c('rpm_aod','rfit'), ls()))")
    return terms, df, rfpe


# ---------------------------------------------------------------------------
# Validation (no R needed beyond import)
# ---------------------------------------------------------------------------

class TestValidation:
    def test_non_fit_raises(self):
        with pytest.raises(TypeError):
            drop1_lmrobdet("not a fit")  # type: ignore[arg-type]

    @needs_r
    def test_bad_scope_type_raises(self):
        rpm.set_seed(1)
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
        with pytest.raises(TypeError):
            fit.drop1(scope=[123])  # not a string term label


# ---------------------------------------------------------------------------
# Case 1 — mineral, single term, full model
# ---------------------------------------------------------------------------

@needs_r
class TestMineralSingleTerm:
    @pytest.fixture
    def py(self):
        rpm.set_seed(1)
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
        rpm.set_seed(1)
        return fit.drop1()

    @pytest.fixture
    def r_ref(self):
        return _r_drop1(
            "data(mineral); set.seed(1L); "
            "rfit <- lmrobdetMM(zinc ~ copper, data=mineral)",
            "drop1(rfit)",
        )

    def test_terms(self, py, r_ref):
        assert py.terms == r_ref[0]

    def test_df(self, py, r_ref):
        np.testing.assert_array_equal(py.df, r_ref[1])

    def test_rfpe(self, py, r_ref):
        np.testing.assert_array_equal(py.rfpe, r_ref[2])

    def test_table_shape(self, py):
        assert list(py.table.columns) == ["Df", "RFPE"]
        assert py.terms[0] == "<none>"
        assert isinstance(py, Drop1Result)

    def test_recommended(self, py, r_ref):
        # lowest-RFPE row label, matching argmin of R's RFPE column
        expected = r_ref[0][int(np.argmin(r_ref[2]))]
        assert py.recommended == expected


# ---------------------------------------------------------------------------
# Case 2 — stackloss, multiple terms, full model
# ---------------------------------------------------------------------------

@needs_r
class TestStacklossAllTerms:
    @pytest.fixture
    def py(self):
        rpm.set_seed(7)
        fit = rpm.lmrobdet_mm("stack.loss ~ .", data=rpm.datasets.stackloss())
        rpm.set_seed(7)
        return fit.drop1()

    @pytest.fixture
    def r_ref(self):
        return _r_drop1(
            "data(stackloss); set.seed(7L); "
            "rfit <- lmrobdetMM(stack.loss ~ ., data=stackloss)",
            "drop1(rfit)",
        )

    def test_terms(self, py, r_ref):
        assert py.terms == r_ref[0]

    def test_df(self, py, r_ref):
        np.testing.assert_array_equal(py.df, r_ref[1])

    def test_rfpe(self, py, r_ref):
        np.testing.assert_array_equal(py.rfpe, r_ref[2])

    def test_module_level_function_matches_method(self):
        rpm.set_seed(7)
        fit = rpm.lmrobdet_mm("stack.loss ~ .", data=rpm.datasets.stackloss())
        rpm.set_seed(7)
        via_method = fit.drop1()
        rpm.set_seed(7)
        via_func = drop1_lmrobdet(fit)
        np.testing.assert_array_equal(via_func.rfpe, via_method.rfpe)
        assert via_func.terms == via_method.terms


# ---------------------------------------------------------------------------
# Case 3 — stackloss, scoped (subset of terms)
# ---------------------------------------------------------------------------

@needs_r
class TestStacklossScoped:
    @pytest.fixture
    def py(self):
        rpm.set_seed(7)
        fit = rpm.lmrobdet_mm("stack.loss ~ .", data=rpm.datasets.stackloss())
        rpm.set_seed(7)
        return fit.drop1(scope=["Air.Flow", "Water.Temp"])

    @pytest.fixture
    def r_ref(self):
        return _r_drop1(
            "data(stackloss); set.seed(7L); "
            "rfit <- lmrobdetMM(stack.loss ~ ., data=stackloss)",
            'drop1(rfit, c("Air.Flow", "Water.Temp"))',
        )

    def test_terms(self, py, r_ref):
        assert py.terms == r_ref[0]
        # <none> + the two scoped terms only
        assert set(py.terms) == {"<none>", "Air.Flow", "Water.Temp"}

    def test_rfpe(self, py, r_ref):
        np.testing.assert_array_equal(py.rfpe, r_ref[2])

    def test_single_term_string_scope(self):
        rpm.set_seed(7)
        fit = rpm.lmrobdet_mm("stack.loss ~ .", data=rpm.datasets.stackloss())
        rpm.set_seed(7)
        res = fit.drop1(scope="Air.Flow")
        assert set(res.terms) == {"<none>", "Air.Flow"}


# ---------------------------------------------------------------------------
# Case 4 — explicit scale argument
# ---------------------------------------------------------------------------

@needs_r
class TestExplicitScale:
    def test_scale_matches_r(self):
        rpm.set_seed(1)
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
        rpm.set_seed(1)
        res = fit.drop1(scale=10.0)
        terms, df, rfpe = _r_drop1(
            "data(mineral); set.seed(1L); "
            "rfit <- lmrobdetMM(zinc ~ copper, data=mineral)",
            "drop1(rfit, scale=10.0)",
        )
        assert res.terms == terms
        np.testing.assert_array_equal(res.rfpe, rfpe)
        assert res.scale == 10.0
