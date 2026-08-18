"""``rob_linear_test`` accepts lmrobM fits, as R does.

R's ``rob.linear.test`` guards on ``'lmrobdetMM' %in% class(x) | 'lmrobM' %in%
class(x)`` (``RobStatTM-master/R/lmrobdet.R``), the R help page's own example
uses ``lmrobM``, and so does the book's Example 4.2 (``oats.R``). The wrapper
used to reject ``LmrobMResult`` outright, which made that example impossible to
reproduce from Python.

The second half of the fix matters just as much and is not visible from the
type signature: each fit has to be replayed in R with the estimator that
produced it. Refitting an M fit with ``lmrobdetMM`` would have returned a
plausible number for the wrong pair of models.
"""
from __future__ import annotations

import pytest

import robstattm_py as rpm

try:
    from robstattm_py._r import r as _r

    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


@pytest.fixture(scope="module")
def oats():
    data = rpm.datasets.oats()
    for column in ("variety", "block"):
        data[column] = data[column].astype("category")
    return data


@pytest.fixture(scope="module")
def control():
    return rpm.lmrobm_control(bb=0.5, efficiency=0.85, family="bisquare")


@needs_r
class TestAcceptsLmrobM:
    def test_lmrob_m_pair_is_accepted(self, oats, control):
        full = rpm.lmrob_m("response1 ~ variety + block", data=oats, control=control)
        reduced = rpm.lmrob_m("response1 ~ block", data=oats, control=control)

        result = rpm.rob_linear_test(full, reduced)

        assert 0.0 <= result.f_pvalue <= 1.0
        assert 0.0 <= result.chisq_pvalue <= 1.0
        assert result.test > 0
        # Dropping `variety` from the original response is strongly significant.
        assert result.f_pvalue < 0.01

    def test_matches_r_exactly(self, oats, control):
        """Strict tier: identical to calling rob.linear.test in R directly."""
        from robstattm_py._r import r

        full = rpm.lmrob_m("response1 ~ variety + block", data=oats, control=control)
        reduced = rpm.lmrob_m("response1 ~ block", data=oats, control=control)
        ours = rpm.rob_linear_test(full, reduced)

        ro = r()
        # Everything here is namespace-qualified and loads into a private
        # environment. Neither is fussiness: `oats` is also a dataset in MASS
        # and in nlme, both of which other tests in this suite pull in
        # transitively, so a bare `data(oats)` picked up whichever package
        # happened to be attached - this test passed alone and failed in the
        # full run with "object 'response1' not found". Same masking hazard
        # that datasets.load() documents for MASS::huber.
        ro.r(
            "rpm_lt_env <- new.env();"
            "utils::data(oats, package='RobStatTM', envir=rpm_lt_env);"
            "rpm_lt_ctrl <- RobStatTM::lmrobdet.control("
            "    bb=0.5, efficiency=0.85, family='bisquare');"
            "rpm_lt_o1 <- RobStatTM::lmrobM(response1 ~ variety+block,"
            "    control=rpm_lt_ctrl, data=rpm_lt_env$oats);"
            "rpm_lt_o2 <- RobStatTM::lmrobM(response1 ~ block,"
            "    control=rpm_lt_ctrl, data=rpm_lt_env$oats);"
            "rpm_lt_res <- RobStatTM::rob.linear.test(rpm_lt_o1, rpm_lt_o2)"
        )
        try:
            assert ours.test == float(ro.r("rpm_lt_res$test")[0])
            assert ours.f_pvalue == float(ro.r("rpm_lt_res$F.pvalue")[0])
            assert ours.chisq_pvalue == float(ro.r("rpm_lt_res$chisq.pvalue")[0])
        finally:
            ro.r(
                "rm(list=intersect(c('rpm_lt_env','rpm_lt_ctrl','rpm_lt_o1',"
                "'rpm_lt_o2','rpm_lt_res'), ls()))"
            )

    def test_mm_pair_still_works(self, oats, control):
        mm_control = rpm.lmrobdet_control(
            bb=0.5, efficiency=0.85, family="bisquare"
        )
        full = rpm.lmrobdet_mm(
            "response1 ~ variety + block", data=oats, control=mm_control
        )
        reduced = rpm.lmrobdet_mm("response1 ~ block", data=oats, control=mm_control)

        assert 0.0 <= rpm.rob_linear_test(full, reduced).f_pvalue <= 1.0


class TestRejectsOtherResults:
    def test_a_non_regression_result_is_refused(self):
        # No R needed - the type guard runs before anything is pushed to R.
        with pytest.raises(TypeError, match="lmrobdet_mm or lmrob_m"):
            rpm.rob_linear_test("not a fit", "also not a fit")
