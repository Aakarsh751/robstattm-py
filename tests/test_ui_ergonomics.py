"""Tests for the §6, §10, §11 UI surfaces added in the ergonomics pass."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from robstattm_py._r import r as _r

try:
    _r()
    HAS_R = True
except Exception:
    HAS_R = False

needs_r = pytest.mark.skipif(not HAS_R, reason="rpy2/R not available")


# --------------------------------------------------------------------- §6


@needs_r
class TestResultErgonomics:
    """to_dict / to_r / coef_df / _repr_html_ on a regression fit."""

    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_mm("zinc ~ copper", data=df)

    def test_to_dict_returns_plain_dict(self, fit):
        d = fit.to_dict()
        assert isinstance(d, dict)
        assert "coefficients" in d
        assert "scale" in d
        # private fields are skipped
        assert not any(k.startswith("_") for k in d)

    def test_to_dict_arrays_preserved(self, fit):
        d = fit.to_dict()
        assert isinstance(d["coefficients"], np.ndarray)
        np.testing.assert_array_equal(d["coefficients"], fit.coefficients)

    def test_to_r_returns_r_object(self, fit):
        r_obj = fit.to_r()
        # rpy2 NamedList / ListVector — either is acceptable
        assert hasattr(r_obj, "__class__")
        assert "rpy2" in type(r_obj).__module__ or "rlike" in type(r_obj).__module__

    def test_to_r_raises_when_r_fit_missing(self, fit):
        # Build a synthetic copy with _r_fit set to None to verify to_r()
        # raises a helpful error rather than returning None.
        from dataclasses import replace
        stripped = replace(fit, _r_fit=None)
        with pytest.raises(RuntimeError, match="unavailable"):
            stripped.to_r()

    def test_coef_df_is_pandas_series(self, fit):
        cdf = fit.coef_df()
        assert isinstance(cdf, pd.Series)
        assert list(cdf.index) == list(fit.coef_names)
        np.testing.assert_array_equal(cdf.to_numpy(), fit.coefficients)

    def test_repr_html_returns_html(self, fit):
        h = fit._repr_html_()
        assert isinstance(h, str)
        assert "<table" in h and "LmrobdetMMResult" in h


# --------------------------------------------------------------------- §3


@needs_r
class TestArrayForm:
    """(X, y) invocation form for the three regression families."""

    @pytest.fixture(scope="class")
    def reference(self):
        df = rpm.datasets.mineral()
        formula_fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
        return df, formula_fit

    def test_lmrobdet_mm_xy_numpy(self, reference):
        df, formula_fit = reference
        X = df[["copper"]].to_numpy()
        y = df["zinc"].to_numpy()
        fit = rpm.lmrobdet_mm(X=X, y=y)
        np.testing.assert_array_equal(fit.coefficients, formula_fit.coefficients)

    def test_lmrobdet_mm_xy_pandas(self, reference):
        df, formula_fit = reference
        fit = rpm.lmrobdet_mm(X=df[["copper"]], y=df["zinc"])
        np.testing.assert_array_equal(fit.coefficients, formula_fit.coefficients)
        # response column name auto-resolved from the Series
        assert fit.formula == "zinc ~ copper"

    def test_lmrobdet_dcml_xy(self, reference):
        df, _ = reference
        rpm.set_seed(0)
        fit_formula = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
        rpm.set_seed(0)
        fit_xy = rpm.lmrobdet_dcml(X=df[["copper"]], y=df["zinc"])
        np.testing.assert_array_equal(fit_xy.coefficients, fit_formula.coefficients)

    def test_lmrob_m_xy(self, reference):
        df, _ = reference
        fit_formula = rpm.lmrob_m("zinc ~ copper", data=df)
        fit_xy = rpm.lmrob_m(X=df[["copper"]], y=df["zinc"])
        np.testing.assert_array_equal(fit_xy.coefficients, fit_formula.coefficients)

    def test_cannot_mix_forms(self, reference):
        df, _ = reference
        with pytest.raises(TypeError, match="Pass either"):
            rpm.lmrobdet_mm("zinc ~ copper", data=df,
                            X=df[["copper"]], y=df["zinc"])

    def test_missing_both_forms_raises(self):
        with pytest.raises(TypeError, match="Provide either"):
            rpm.lmrobdet_mm()


# --------------------------------------------------------------------- §9


class TestHelp:

    def test_help_with_r_name(self, capsys):
        rpm.help("lmrobdetMM")
        out = capsys.readouterr().out
        assert "lmrobdet_mm" in out
        assert "R: lmrobdetMM" in out

    def test_help_with_python_name(self, capsys):
        rpm.help("lmrobdet_mm")
        out = capsys.readouterr().out
        assert "lmrobdet_mm" in out

    def test_help_with_dotted_r_name(self, capsys):
        rpm.help("step.lmrobdetMM")
        out = capsys.readouterr().out
        assert "step_lmrobdet" in out

    def test_help_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown name"):
            rpm.help("not_a_function_at_all_xyz")

    def test_list_names_contains_expected(self):
        m = rpm.list_names()
        assert m["lmrobdetMM"] == "lmrobdet_mm"
        assert m["covRobMM"] == "cov_rob_mm"


# --------------------------------------------------------------------- §11


@needs_r
class TestBenchAndPerf:

    def test_r_started_true_after_use(self):
        # Anything that touched R earlier in this session is enough.
        rpm.datasets.mineral()
        assert rpm.r_started() is True

    def test_set_n_jobs_round_trip(self):
        prev = rpm.set_n_jobs(2)
        assert isinstance(prev, int)
        new = rpm.set_n_jobs(prev or 1)
        assert new == 2

    def test_set_n_jobs_validates(self):
        with pytest.raises(ValueError, match="positive int"):
            rpm.set_n_jobs(0)
        with pytest.raises(ValueError, match="positive int"):
            rpm.set_n_jobs(-1)

    def test_timer_returns_breakdown(self):
        df = rpm.datasets.mineral()
        t = rpm.bench.timer(lambda: rpm.lmrobdet_mm("zinc ~ copper", data=df))
        assert t.total_seconds > 0
        assert t.r_seconds >= 0
        assert t.py_overhead_seconds >= 0
        # r_seconds and total_seconds are measured by different clocks
        # (R Sys.time vs Python perf_counter) so they can drift slightly;
        # just check the breakdown is plausible (within a few ms).
        assert abs((t.r_seconds + t.py_overhead_seconds) - t.total_seconds) < 0.05
        assert "TimerResult" in repr(t)

    def test_timer_repeat(self):
        df = rpm.datasets.mineral()
        t = rpm.bench.timer(
            lambda: rpm.lmrobdet_mm("zinc ~ copper", data=df), repeat=2,
        )
        assert t.total_seconds > 0


# --------------------------------------------------------------------- §10


@needs_r
class TestDiagnosticPlots:
    """plot_residuals / plot_qq / plot_diagnostics.

    Per D-023 the shortcuts now default to the native suite and return a
    matplotlib ``Axes`` (single panel) / ``Figure`` (diagnostics); the Path-A
    PNG is still reachable via ``backend="r"``.
    """

    @pytest.fixture(scope="class")
    def fit(self):
        df = rpm.datasets.mineral()
        return rpm.lmrobdet_mm("zinc ~ copper", data=df)

    def _check_png(self, path):
        assert path.exists()
        assert path.stat().st_size > 0
        # PNG magic bytes
        with open(path, "rb") as f:
            assert f.read(4) == b"\x89PNG"

    # ----- native default (returns Axes / Figure) -----

    def test_plot_residuals_native_returns_axes(self, fit):
        pytest.importorskip("matplotlib")
        from matplotlib.axes import Axes

        assert isinstance(fit.plot_residuals(), Axes)

    def test_plot_qq_native_returns_axes(self, fit):
        pytest.importorskip("matplotlib")
        from matplotlib.axes import Axes

        assert isinstance(fit.plot_qq(), Axes)

    def test_plot_diagnostics_native_returns_figure(self, fit):
        pytest.importorskip("matplotlib")
        from matplotlib.figure import Figure

        assert isinstance(fit.plot_diagnostics(), Figure)

    # ----- Path A (backend="r") still returns a PNG path -----

    def test_plot_residuals_r_png(self, fit, tmp_path):
        p = fit.plot_residuals(backend="r", path=tmp_path / "res.png",
                               dpi=72, width=4, height=3)
        self._check_png(p)

    def test_plot_qq_r_png(self, fit, tmp_path):
        p = fit.plot_qq(backend="r", path=tmp_path / "qq.png",
                        dpi=72, width=4, height=3)
        self._check_png(p)

    def test_plot_diagnostics_r_png(self, fit, tmp_path):
        p = fit.plot_diagnostics(backend="r", path=tmp_path / "diag.png", dpi=72)
        self._check_png(p)
