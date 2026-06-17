"""Strict-tier tests for pyinit vs direct R (pyinit::pyinit)."""
from __future__ import annotations

import numpy as np
import pytest

import robstatm_py as rpm
from robstatm_py import set_seed
from tests.conftest import needs_r


def _pyinit_available() -> bool:
    try:
        from robstatm_py._r import r_pkg

        r_pkg("pyinit")
        return True
    except Exception:
        return False


needs_pyinit = pytest.mark.skipif(
    not _pyinit_available(),
    reason="pyinit R package not installed",
)


class TestValidation:
    def test_mismatched_lengths(self):
        with pytest.raises(ValueError):
            rpm.pyinit(np.ones((10, 2)), np.ones(5))


@needs_r
@needs_pyinit
class TestMineralVsR:
    @pytest.fixture
    def setup(self):
        from robstatm_py._r import r

        ro = r()
        ro.r("library(RobStatTM); library(pyinit); data(mineral); "
             "X_pi <- as.matrix(mineral['copper']); y_pi <- mineral$zinc; "
             "set.seed(42L); p_check <- pyinit::pyinit(x=X_pi, y=y_pi, cc=1.5476, "
             "psc_keep=0.5, resid_keep_prop=0.2, resid_keep_thresh=2)")
        set_seed(42)
        df = rpm.datasets.mineral()
        py = rpm.pyinit(df[["copper"]].to_numpy(dtype=float),
                        df["zinc"].to_numpy(dtype=float))
        return py

    def test_coefficients(self, setup, R):
        np.testing.assert_array_equal(
            setup.coefficients,
            np.asarray(R("p_check$coefficients"), dtype=float),
        )

    def test_objective(self, setup, R):
        np.testing.assert_array_equal(
            setup.objective,
            np.asarray(R("p_check$objective"), dtype=float),
        )

    def test_best_is_min_objective_column(self, setup):
        best_idx = int(np.argmin(setup.objective))
        np.testing.assert_array_equal(
            setup.best, setup.coefficients[:, best_idx]
        )


@needs_r
@needs_pyinit
def test_pyinit_repr():
    df = rpm.datasets.mineral()
    set_seed(42)
    res = rpm.pyinit(
        df[["copper"]].to_numpy(dtype=float),
        df["zinc"].to_numpy(dtype=float),
    )
    assert "PyinitResult" in repr(res)
