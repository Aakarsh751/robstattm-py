"""Strict-tier tests for rob_linear_test."""
from __future__ import annotations

import pytest

import robstattm_py as rpm
from robstattm_py import set_seed
from tests.conftest import needs_r


class TestValidation:
    def test_non_fit_raises(self):
        with pytest.raises(TypeError):
            rpm.rob_linear_test("a", "b")  # type: ignore[arg-type]


@needs_r
class TestStackLossVsR:
    """Test against the stackloss dataset."""

    @pytest.fixture
    def setup(self):
        from robstattm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); data(stackloss); "
             "set.seed(42L); ff_r <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., data=stackloss); "
             "set.seed(42L); rr_r <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp, data=stackloss); "
             "rlt_r <- rob.linear.test(ff_r, rr_r)")
        df = rpm.datasets.stackloss()
        set_seed(42)
        full = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df)
        set_seed(42)
        red = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)
        return rpm.rob_linear_test(full, red)

    def test_statistic(self, setup, R):
        py = setup
        assert py.test == float(R("rlt_r$test")[0])

    def test_chisq_pvalue(self, setup, R):
        py = setup
        assert py.chisq_pvalue == float(R("rlt_r$chisq.pvalue")[0])

    def test_f_pvalue(self, setup, R):
        py = setup
        assert py.f_pvalue == float(R("rlt_r$F.pvalue")[0])

    def test_df(self, setup, R):
        py = setup
        r_df = R("as.integer(rlt_r$df)")
        assert py.df == (int(r_df[0]), int(r_df[1]))


@needs_r
def test_rlt_repr():
    df = rpm.datasets.stackloss()
    set_seed(42)
    full = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df)
    set_seed(42)
    red = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)
    res = rpm.rob_linear_test(full, red)
    assert "RobLinearTestResult" in repr(res)
