"""Native regression-diagnostic plot tests (R-free).

Cover the return-type contract, ``ax=`` composability, customization
(highlight / labels / annotate / style), and the **no-refit guard**: native
renderers must never start R.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")

import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from robstatm_py import plot  # noqa: E402

SINGLE_PANEL = ["residuals", "qq", "scale_location", "weights"]


@pytest.mark.parametrize("name", SINGLE_PANEL)
def test_single_panel_returns_axes(fake_fit, name):
    ax = getattr(plot, name)(fake_fit)
    assert isinstance(ax, Axes)


def test_diagnostics_returns_figure_with_four_panels(fake_fit):
    fig = plot.diagnostics(fake_fit)
    assert isinstance(fig, Figure)
    assert len(fig.axes) >= 4  # 4 panels (+ any colorbars suppressed)


@pytest.mark.parametrize("name", SINGLE_PANEL)
def test_ax_is_honored_no_new_figure(fake_fit, name):
    fig, ax = plt.subplots()
    n_before = plt.get_fignums()
    ret = getattr(plot, name)(fake_fit, ax=ax)
    assert ret is ax
    assert ax.figure is fig
    assert plt.get_fignums() == n_before  # no extra figure created


def test_resid_vs_leverage_with_explicit_leverage(fake_fit):
    ax = plot.resid_vs_leverage(fake_fit, leverage=fake_fit._leverage)
    assert isinstance(ax, Axes)


def test_highlight_and_labels_add_annotations(fake_fit):
    ax = plot.residuals(fake_fit, highlight=[0, 1, 2],
                        labels=[f"obs{i}" for i in range(50)], annotate=False)
    texts = [t.get_text() for t in ax.texts]
    assert "obs0" in texts and "obs1" in texts and "obs2" in texts


def test_annotate_false_suppresses_outlier_labels(fake_fit):
    ax = plot.residuals(fake_fit, annotate=False)
    assert len(ax.texts) == 0


def test_annotate_true_labels_planted_outliers(fake_fit):
    ax = plot.residuals(fake_fit, annotate=True,
                        labels=[f"obs{i}" for i in range(50)])
    texts = [t.get_text() for t in ax.texts]
    # observations 4 and 19 were planted as outliers in the fixture
    assert "obs4" in texts and "obs19" in texts


def test_style_override_changes_marker_size(fake_fit):
    ax = plot.residuals(fake_fit, point_size=200, color_by_weight=False,
                        annotate=False)
    sizes = np.concatenate([c.get_sizes() for c in ax.collections if len(c.get_sizes())])
    assert sizes.max() >= 200


def test_title_is_set(fake_fit):
    ax = plot.residuals(fake_fit, title="my title")
    assert ax.get_title() == "my title"


def test_save_writes_file(fake_fit, tmp_path):
    out = tmp_path / "resid.png"
    plot.residuals(fake_fit, save=out)
    assert out.exists() and out.stat().st_size > 0


def test_weights_requires_rweights():
    from types import SimpleNamespace

    bare = SimpleNamespace(residuals=np.arange(5.0), fitted_values=np.arange(5.0),
                           rweights=None, scale=1.0)
    with pytest.raises(TypeError, match="rweights"):
        plot.weights(bare)


def test_missing_field_raises_typeerror():
    from types import SimpleNamespace

    bad = SimpleNamespace(fitted_values=np.arange(5.0))  # no residuals
    with pytest.raises(TypeError, match="residuals"):
        plot.residuals(bad)


def test_native_plots_do_not_start_r(fake_fit, monkeypatch):
    """No-refit guard: native rendering must not import/start the R bridge."""
    import robstatm_py._r as _r

    def _boom(*a, **k):  # pragma: no cover - only runs on failure
        raise AssertionError("native plot unexpectedly called the R bridge")

    monkeypatch.setattr(_r, "r", _boom)
    monkeypatch.setattr(_r, "r_pkg", _boom)
    monkeypatch.setattr(_r, "rcall", _boom)

    for name in SINGLE_PANEL:
        getattr(plot, name)(fake_fit)
    plot.diagnostics(fake_fit)
    plot.resid_vs_leverage(fake_fit, leverage=fake_fit._leverage)


def test_no_implicit_show(fake_fit, monkeypatch):
    """Library must not call plt.show() unless show=True."""
    called = {"n": 0}
    monkeypatch.setattr(plt, "show", lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    plot.residuals(fake_fit)
    plot.diagnostics(fake_fit)
    assert called["n"] == 0
