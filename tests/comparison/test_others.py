"""Strict-tier parity for the rlm / lmrob / ltsReg / glm comparison wrappers."""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from robstattm_py.regression._formula import df_with_r_names
from tests.conftest import _r_pkg_available, needs_r

needs_MASS = pytest.mark.skipif(
    not _r_pkg_available("MASS"), reason="R package 'MASS' unavailable"
)
needs_robustbase = pytest.mark.skipif(
    not _r_pkg_available("robustbase"), reason="R package 'robustbase' unavailable"
)


@pytest.fixture
def mineral_in_r():
    from robstattm_py._r import r

    ro = r()
    ro.globalenv["cmp_d"] = df_with_r_names(rpm.datasets.mineral())
    yield ro
    ro.r("for (v in c('cmp_d','cmp_fit')) if (exists(v)) rm(list=v)")


@needs_r
@needs_MASS
class TestRlm:
    def test_coefficients(self, mineral_in_r):
        ro = mineral_in_r
        py = rpm.rlm("zinc ~ copper", data=rpm.datasets.mineral())
        ro.r("cmp_fit <- MASS::rlm(zinc ~ copper, data=cmp_d)")
        np.testing.assert_allclose(
            py.coefficients, np.asarray(ro.r("as.numeric(coef(cmp_fit))"), dtype=float)
        )
        assert py.scale == pytest.approx(float(ro.r("cmp_fit$s")[0]))

    def test_summary_has_no_pvalue_column(self, mineral_in_r):
        py = rpm.rlm("zinc ~ copper", data=rpm.datasets.mineral())
        cols = list(py.summary().coefficients_table.columns)
        assert "t value" in cols and not any("Pr(" in c for c in cols)

    def test_vcov_parity(self, mineral_in_r):
        ro = mineral_in_r
        py = rpm.rlm("zinc ~ copper", data=rpm.datasets.mineral())
        ro.r("cmp_fit <- MASS::rlm(zinc ~ copper, data=cmp_d)")
        np.testing.assert_allclose(
            py.vcov().to_numpy(),
            np.asarray(ro.r("as.matrix(vcov(cmp_fit))"), dtype=float),
        )
        assert py.confint().shape == (2, 2)


@needs_r
@needs_robustbase
class TestLmrob:
    def test_coefficients_seeded(self, mineral_in_r):
        ro = mineral_in_r
        rpm.set_seed(7)
        py = rpm.lmrob("zinc ~ copper", data=rpm.datasets.mineral())
        ro.r("set.seed(7L); cmp_fit <- robustbase::lmrob(zinc ~ copper, data=cmp_d)")
        np.testing.assert_allclose(
            py.coefficients,
            np.asarray(ro.r("as.numeric(coef(cmp_fit))"), dtype=float),
            rtol=1e-6, atol=1e-8,
        )
        assert py.converged in (True, False)
        assert py.scale > 0

    def test_summary_columns(self, mineral_in_r):
        rpm.set_seed(7)
        py = rpm.lmrob("zinc ~ copper", data=rpm.datasets.mineral())
        cols = list(py.summary().coefficients_table.columns)
        assert cols[:2] == ["Estimate", "Std. Error"]


@needs_r
@needs_robustbase
class TestLtsReg:
    def test_coefficients_seeded(self, mineral_in_r):
        ro = mineral_in_r
        rpm.set_seed(11)
        py = rpm.lts_reg("zinc ~ copper", data=rpm.datasets.mineral())
        ro.r("set.seed(11L); cmp_fit <- robustbase::ltsReg(zinc ~ copper, data=cmp_d)")
        np.testing.assert_allclose(
            py.coefficients,
            np.asarray(ro.r("as.numeric(coef(cmp_fit))"), dtype=float),
            rtol=1e-6, atol=1e-8,
        )
        assert py.scale > 0


@needs_r
class TestGlm:
    @pytest.fixture
    def binary(self):
        df = rpm.datasets.mineral().copy()
        df["hi"] = (df["zinc"] > df["zinc"].median()).astype(int)
        return df

    def test_coefficients(self, binary):
        from robstattm_py._r import r

        ro = r()
        py = rpm.glm("hi ~ copper", data=binary, family="binomial")
        ro.globalenv["cmp_gd"] = df_with_r_names(binary)
        try:
            ro.r("cmp_g <- glm(hi ~ copper, data=cmp_gd, family=binomial)")
            np.testing.assert_allclose(
                py.coefficients,
                np.asarray(ro.r("as.numeric(coef(cmp_g))"), dtype=float),
            )
            assert py.family == "binomial"
            assert py.deviance == pytest.approx(float(ro.r("cmp_g$deviance")[0]))
        finally:
            ro.r("for (v in c('cmp_gd','cmp_g')) if (exists(v)) rm(list=v)")

    def test_summary_uses_z_column(self, binary):
        py = rpm.glm("hi ~ copper", data=binary, family="binomial")
        cols = list(py.summary().coefficients_table.columns)
        assert "z value" in cols

    def test_predict_response_in_unit_interval(self, binary):
        py = rpm.glm("hi ~ copper", data=binary, family="binomial")
        p = py.predict(type="response")
        assert np.all((p >= 0) & (p <= 1))

    def test_vcov_parity(self, binary):
        from robstattm_py._r import r

        ro = r()
        py = rpm.glm("hi ~ copper", data=binary, family="binomial")
        ro.globalenv["cmp_gd"] = df_with_r_names(binary)
        try:
            ro.r("cmp_g <- glm(hi ~ copper, data=cmp_gd, family=binomial)")
            np.testing.assert_allclose(
                py.vcov().to_numpy(),
                np.asarray(ro.r("as.matrix(vcov(cmp_g))"), dtype=float),
            )
        finally:
            ro.r("for (v in c('cmp_gd','cmp_g')) if (exists(v)) rm(list=v)")
