"""Regression test for the ``Y ~ .`` (dot-formula) bug.

Originally, ``_extract_coef_names`` called R's ``terms(formula)`` without
a ``data=`` argument and crashed on dot formulas with::

    Error in terms.formula(Y ~ .) : '.' in formula and no 'data' argument

The fix moved coefficient-name extraction to
``coef_names_for(formula)`` which uses
``colnames(model.matrix(formula, data=rpm_data))``, works for every
formula form because the data is in R globalenv at extraction time.

These tests guard against any future regression to the formula-only
approach.
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm


@pytest.fixture(scope="module")
def coleman():
    return rpm.datasets.load("robustbase", "coleman")


def test_dot_formula_lmrobdet_mm(coleman):
    """``Y ~ .`` must expand to all predictors and not crash."""
    fit = rpm.lmrobdet_mm("Y ~ .", data=coleman)
    expected = ("(Intercept)", "salaryP", "fatherWc", "sstatus",
                "teacherSc", "motherLev")
    assert fit.coef_names == expected
    assert fit.coefficients.shape == (6,)
    assert fit.converged is True


def test_dot_formula_matches_explicit_formula(coleman):
    """``Y ~ .`` and the spelled-out formula must produce identical results."""
    dot = rpm.lmrobdet_mm("Y ~ .", data=coleman)
    spelled = rpm.lmrobdet_mm(
        "Y ~ salaryP + fatherWc + sstatus + teacherSc + motherLev",
        data=coleman,
    )
    np.testing.assert_array_equal(dot.coefficients, spelled.coefficients)
    assert dot.coef_names == spelled.coef_names
    assert dot.r_squared == spelled.r_squared
    assert dot.scale == spelled.scale


def test_interaction_formula(coleman):
    """``Y ~ a*b`` should expand to main effects + interaction."""
    fit = rpm.lmrobdet_mm("Y ~ salaryP * fatherWc", data=coleman)
    assert fit.coef_names == (
        "(Intercept)", "salaryP", "fatherWc", "salaryP:fatherWc",
    )
