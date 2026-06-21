"""Native multivariate plot tests (R-free)."""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")

import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402

from robstatm_py import plot  # noqa: E402


def test_distance_distance_returns_axes(fake_cov_pair):
    robust, classical = fake_cov_pair
    ax = plot.distance_distance(robust, classical)
    assert isinstance(ax, Axes)


def test_distance_distance_flags_planted_outliers(fake_cov_pair):
    robust, classical = fake_cov_pair
    ax = plot.distance_distance(robust, classical,
                                labels=[f"o{i}" for i in range(45)])
    texts = [t.get_text() for t in ax.texts]
    assert "o2" in texts and "o9" in texts


def test_mahalanobis_panel(fake_cov_pair):
    robust, _ = fake_cov_pair
    ax = plot.mahalanobis_panel(robust)
    assert isinstance(ax, Axes)


def test_cov_heatmap_and_delta(fake_cov_pair):
    robust, classical = fake_cov_pair
    assert isinstance(plot.cov_heatmap(robust), Axes)
    assert isinstance(plot.cov_heatmap(robust, classical), Axes)


def test_scree(fake_pca):
    ax = plot.scree(fake_pca)
    assert isinstance(ax, Axes)
    # bars = number of components
    assert len([p for p in ax.patches]) == 3


def test_scores_and_with_distances(fake_pca, fake_cov_pair):
    robust, _ = fake_cov_pair
    assert isinstance(plot.scores(fake_pca), Axes)
    assert isinstance(plot.scores(fake_pca, distances=robust.dist), Axes)


def test_loadings_and_biplot(fake_pca):
    assert isinstance(plot.loadings(fake_pca), Axes)
    assert isinstance(plot.biplot(fake_pca), Axes)


@pytest.mark.parametrize("name,args", [
    ("mahalanobis_panel", "cov"),
    ("scree", "pca"),
    ("scores", "pca"),
    ("loadings", "pca"),
    ("cov_heatmap", "cov"),
])
def test_ax_is_honored(name, args, fake_cov_pair, fake_pca):
    fig, ax = plt.subplots()
    obj = fake_cov_pair[0] if args == "cov" else fake_pca
    n_before = plt.get_fignums()
    ret = getattr(plot, name)(obj, ax=ax)
    assert ret is ax
    assert plt.get_fignums() == n_before


def test_scores_rejects_too_few_components():
    from types import SimpleNamespace

    one_comp = SimpleNamespace(repre=np.zeros((10, 1)), eigvec=np.zeros((4, 1)),
                               prop_spc=np.array([1.0]), column_names=tuple("abcd"))
    with pytest.raises(ValueError, match="component"):
        plot.scores(one_comp, comps=(0, 1))
    with pytest.raises(ValueError, match="component"):
        plot.biplot(one_comp, comps=(0, 1))


def test_distance_distance_needs_distances():
    from types import SimpleNamespace

    bad = SimpleNamespace(cov=np.eye(2))  # no dist
    with pytest.raises(TypeError, match="dist"):
        plot.distance_distance(bad, bad)


def test_multivariate_does_not_start_r(fake_cov_pair, fake_pca, monkeypatch):
    import robstatm_py._r as _r

    def _boom(*a, **k):  # pragma: no cover
        raise AssertionError("multivariate plot called the R bridge")

    monkeypatch.setattr(_r, "r", _boom)
    monkeypatch.setattr(_r, "r_pkg", _boom)
    monkeypatch.setattr(_r, "rcall", _boom)

    robust, classical = fake_cov_pair
    plot.distance_distance(robust, classical)
    plot.mahalanobis_panel(robust)
    plot.cov_heatmap(robust, classical)
    plot.scree(fake_pca)
    plot.scores(fake_pca)
    plot.loadings(fake_pca)
    plot.biplot(fake_pca)


def test_plotnine_backend_multivariate(fake_cov_pair, fake_pca):
    """With plotnine installed every multivariate fn returns a ggplot;
    without it, a clear ImportError is raised."""
    robust, classical = fake_cov_pair
    plotnine = pytest.importorskip("plotnine")
    ggplot = plotnine.ggplot
    assert isinstance(plot.distance_distance(robust, classical, backend="plotnine"), ggplot)
    assert isinstance(plot.mahalanobis_panel(robust, backend="plotnine"), ggplot)
    assert isinstance(plot.scree(fake_pca, backend="plotnine"), ggplot)
    assert isinstance(plot.scores(fake_pca, backend="plotnine"), ggplot)
    assert isinstance(plot.scores(fake_pca, distances=robust.dist, backend="plotnine"), ggplot)
    assert isinstance(plot.loadings(fake_pca, backend="plotnine"), ggplot)
    assert isinstance(plot.biplot(fake_pca, backend="plotnine"), ggplot)
    assert isinstance(plot.cov_heatmap(robust, classical, backend="plotnine"), ggplot)
