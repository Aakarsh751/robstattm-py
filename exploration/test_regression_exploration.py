"""Regression wrappers — parameter sweeps and less-documented workflows.

Covers combinations NOT shown in ``docs/examples/``:
  - full ``lmrobdet_control`` customisation (book defaults: bisquare @ 0.85)
  - ``lmrob_m`` vs ``lmrobdet_mm`` vs ``lmrobdet_dcml``
  - stepwise RFPE and robust linear tests
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import assert_scalar_equal, needs_r

# Book-style control used across many R example scripts (shock.R, algae.R, …)
BOOK_CTRL = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")


@needs_r
class TestControlCustomizations:
    """Sweep ψ-family and efficiency; verify Python == R on mineral."""

    @pytest.fixture(scope="class")
    def mineral(self):
        return rpm.datasets.mineral()

    @pytest.mark.parametrize(
        "family,efficiency",
        [
            ("mopt", 0.95),
            ("bisquare", 0.85),
            ("opt", 0.95),
        ],
    )
    def test_family_efficiency_vs_r(self, mineral, R, family, efficiency):
        from robstattm_py._r import r

        ro = r()
        ro.globalenv["rpm_mineral"] = mineral.copy()
        ro.globalenv["rpm_mineral"].columns = list(mineral.attrs["r_columns"])
        ro.r(
            f'ctrl <- lmrobdet.control(family="{family}", efficiency={efficiency}); '
            f'r_fit <- lmrobdetMM(zinc ~ copper, data=rpm_mineral, control=ctrl)'
        )
        py_fit = rpm.lmrobdet_mm(
            "zinc ~ copper", data=mineral, family=family, efficiency=efficiency
        )
        assert_scalar_equal(py_fit.scale, R("r_fit$scale"), where="scale")
        assert_scalar_equal(py_fit.r_squared, R("r_fit$r.squared"), where="r_squared")
        assert py_fit.converged

    def test_full_control_object_vs_r(self, mineral, R):
        from robstattm_py._r import r

        ro = r()
        ro.globalenv["rpm_mineral"] = mineral.copy()
        ro.globalenv["rpm_mineral"].columns = list(mineral.attrs["r_columns"])
        ro.r(
            "ctrl <- lmrobdet.control("
            "bb=0.5, efficiency=0.85, family='bisquare', "
            "max.it=150, trace.lev=0); "
            "r_fit <- lmrobdetMM(zinc ~ copper, data=rpm_mineral, control=ctrl)"
        )
        ctrl = rpm.lmrobdet_control(
            bb=0.5,
            efficiency=0.85,
            family="bisquare",
            max_it=150,
            trace_lev=0,
        )
        py_fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=ctrl)
        assert_scalar_equal(py_fit.iter, R("r_fit$iter"), where="iter")
        np.testing.assert_allclose(
            py_fit.coefficients,
            np.asarray(R("r_fit$coefficients"), dtype=float),
            rtol=0,
            atol=0,
        )


@needs_r
class TestLmrobM:
    """M-regression on shock data (Example 4.1) — not in docs/examples."""

    def test_shock_vs_r(self, R):
        shock = rpm.datasets.shock()
        ctrl = rpm.lmrobm_control(bb=0.5, efficiency=0.85, family="bisquare")
        py = rpm.lmrob_m("time ~ n.shocks", data=shock, control=ctrl)
        R(
            "library(RobStatTM); data(shock); "
            "cont <- lmrobM.control(bb=0.5, efficiency=0.85, family='bisquare'); "
            "r_fit <- lmrobM(time ~ n.shocks, data=shock, control=cont)"
        )
        assert_scalar_equal(py.scale, R("r_fit$scale"))
        assert py.converged
        assert len(py.residuals) == shock.shape[0]


@needs_r
class TestLmrobdetDCML:
    """DCML regression — alternative to MM, not demoed in examples."""

    def test_mineral_vs_r(self, R):
        df = rpm.datasets.mineral()
        py = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        R("library(RobStatTM); data(mineral); "
          "r_fit <- lmrobdetDCML(zinc ~ copper, data=mineral)")
        assert_scalar_equal(py.scale, R("r_fit$scale"))
        assert py.converged


@needs_r
class TestStepwiseAndLinearTest:
    """Stepwise RFPE + nested model test on stackloss (Example 5.3 style)."""

    @pytest.fixture(scope="class")
    def stackloss(self):
        return rpm.datasets.stackloss()

    def test_stepwise_rfpe(self, stackloss, R):
        rpm.set_seed(300)
        full = rpm.lmrobdet_mm(
            "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
            data=stackloss,
            control=BOOK_CTRL,
        )
        step = rpm.step_lmrobdet(full)
        assert step.final_formula  # non-empty selected formula
        assert len(step.anova_rfpe) >= 1
        assert step.scale > 0

    def test_rob_linear_test_nested(self, stackloss, R):
        rpm.set_seed(42)
        full = rpm.lmrobdet_mm(
            "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
            data=stackloss,
        )
        reduced = rpm.lmrobdet_mm(
            "stack.loss ~ Air.Flow + Water.Temp",
            data=stackloss,
        )
        test = rpm.rob_linear_test(full, reduced)
        assert test.test > 0
        assert 0 <= test.chisq_pvalue <= 1
        assert test.df == (1, full.df_residual)

    def test_rfpe_method_on_fit(self, stackloss):
        fit = rpm.lmrobdet_mm(
            "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
            data=stackloss,
        )
        score = fit.rfpe()
        assert np.isfinite(score)


@needs_r
class TestAlgaeDotFormula:
    """Multi-predictor dot formula (algae.R Example 5.4)."""

    def test_v12_dot_vs_r(self, R):
        algae = rpm.datasets.algae()
        py = rpm.lmrobdet_mm("V12 ~ .", data=algae, control=BOOK_CTRL)
        R(
            "library(RobStatTM); data(algae); "
            "cont <- lmrobdet.control(bb=0.5, efficiency=0.85, family='bisquare'); "
            "r_fit <- lmrobdetMM(V12 ~ ., data=algae, control=cont)"
        )
        assert_scalar_equal(py.scale, R("r_fit$scale"))
        assert py.rank >= 2
