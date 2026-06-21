"""Native univariate + scatter/compare plot tests (R-free)."""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")

import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402

from robstatm_py import plot  # noqa: E402


def test_location_scale_returns_axes(fake_locscale):
    rng = np.random.default_rng(3)
    ax = plot.location_scale(fake_locscale, rng.normal(0, 1, 200))
    assert isinstance(ax, Axes)


def test_location_scale_draws_robust_and_classical_bands(fake_locscale):
    rng = np.random.default_rng(3)
    ax = plot.location_scale(fake_locscale, rng.normal(0, 1, 200),
                             show_classical=True)
    # robust mu line + mean line => at least two vertical lines
    assert len(ax.get_lines()) >= 1
    legend = ax.get_legend()
    labels = [t.get_text() for t in legend.get_texts()]
    assert any("robust" in label for label in labels)
    assert any("mean" in label for label in labels)


def test_location_scale_no_classical(fake_locscale):
    rng = np.random.default_rng(3)
    ax = plot.location_scale(fake_locscale, rng.normal(0, 1, 100),
                             show_classical=False)
    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert not any("mean" in label for label in labels)


def test_location_scale_handles_nan(fake_locscale):
    x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    ax = plot.location_scale(fake_locscale, x)
    assert isinstance(ax, Axes)


def test_scatter_with_fit_draws_line(fake_reg_with_data):
    ax = plot.scatter_with_fit(fake_reg_with_data)
    labels = [ln.get_label() for ln in ax.get_lines()]
    assert "robust fit" in labels


def test_scatter_with_fit_ols_overlay(fake_reg_with_data):
    ax = plot.scatter_with_fit(fake_reg_with_data, show_ols=True)
    labels = [ln.get_label() for ln in ax.get_lines()]
    assert "OLS" in labels


def test_scatter_with_fit_infers_predictor(fake_reg_with_data):
    ax = plot.scatter_with_fit(fake_reg_with_data, x="copper")
    assert ax.get_xlabel() == "copper"
    assert ax.get_ylabel() == "zinc"


def test_compare_fits_multiple_lines(fake_reg_with_data):
    from types import SimpleNamespace

    import pandas as pd

    df = fake_reg_with_data._data
    other = SimpleNamespace(coef_names=("(Intercept)", "copper"),
                            coefficients=np.array([1.0, 1.6]),
                            formula="zinc ~ copper", _data=df)
    ax = plot.compare_fits({"robust": fake_reg_with_data, "other": other},
                           extra_lines=[(1.0, 3.0, "L1")])
    labels = [ln.get_label() for ln in ax.get_lines()]
    assert "robust" in labels and "other" in labels and "L1" in labels
    assert isinstance(df, pd.DataFrame)


def test_compare_fits_needs_at_least_one():
    with pytest.raises(ValueError, match="at least one"):
        plot.compare_fits([])


def test_ax_honored_univariate(fake_locscale):
    rng = np.random.default_rng(3)
    fig, ax = plt.subplots()
    n_before = plt.get_fignums()
    ret = plot.location_scale(fake_locscale, rng.normal(0, 1, 100), ax=ax)
    assert ret is ax
    assert plt.get_fignums() == n_before


def test_plotnine_backend_univariate(fake_locscale, fake_reg_with_data):
    plotnine = pytest.importorskip("plotnine")
    ggplot = plotnine.ggplot
    rng = np.random.default_rng(3)
    assert isinstance(
        plot.location_scale(fake_locscale, rng.normal(0, 1, 100), backend="plotnine"),
        ggplot,
    )
    assert isinstance(
        plot.scatter_with_fit(fake_reg_with_data, show_ols=True, backend="plotnine"),
        ggplot,
    )
    assert isinstance(
        plot.compare_fits({"r": fake_reg_with_data}, backend="plotnine"), ggplot
    )


def test_scatter_compare_do_not_start_r(fake_reg_with_data, monkeypatch):
    import robstatm_py._r as _r

    def _boom(*a, **k):  # pragma: no cover
        raise AssertionError("native plot called the R bridge")

    monkeypatch.setattr(_r, "r", _boom)
    monkeypatch.setattr(_r, "r_pkg", _boom)
    monkeypatch.setattr(_r, "rcall", _boom)

    plot.scatter_with_fit(fake_reg_with_data, show_ols=True)
    plot.compare_fits([fake_reg_with_data])
