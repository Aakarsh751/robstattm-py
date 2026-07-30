"""Pre-render the plotting-gallery images for the Sphinx site.

The Sphinx build itself is R-free (``conf.py`` never imports the package), so the
gallery is shipped as static PNGs under ``docs/_static/plots/``. This script
regenerates them; it needs a working R bridge (for the live fits and the Path-A
``backend="r"`` panels) and the ``[plots]`` extra.

Run from the package root (``robstattm-py/``)::

    # Windows (PowerShell) — set the R env first:
    $env:R_HOME = "C:\\Program Files\\R\\R-4.5.2"
    $env:PATH   = "C:\\Program Files\\R\\R-4.5.2\\bin\\x64;" + $env:PATH
    python docs/scripts/render_plots.py

Every figure is saved twice where a Path-A equivalent exists, so the docs can
show native vs R side-by-side.
"""
from __future__ import annotations

import pathlib
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import robstattm_py as rpm  # noqa: E402
from robstattm_py import plot  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "_static" / "plots"
OUT.mkdir(parents=True, exist_ok=True)


def save(fig_or_ax, name: str) -> None:
    fig = getattr(fig_or_ax, "figure", fig_or_ax)
    fig.savefig(OUT / name, bbox_inches="tight", dpi=120)
    plt.close(fig)
    print("wrote", name)


def copy_r(path, name: str) -> None:
    shutil.copyfile(path, OUT / name)
    print("wrote", name, "(Path A / R)")


def main() -> None:
    plot.set_theme("publication")

    # ---- regression diagnostics (mineral) ----
    mineral = rpm.datasets.mineral()
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
    labels = [str(i) for i in range(len(fit.residuals))]

    save(plot.residuals(fit, labels=labels), "residuals_native.png")
    copy_r(plot.residuals(fit, backend="r"), "residuals_r.png")
    save(plot.qq(fit, labels=labels), "qq_native.png")
    copy_r(plot.qq(fit, backend="r"), "qq_r.png")
    save(plot.diagnostics(fit), "diagnostics_native.png")
    copy_r(plot.diagnostics(fit, backend="r"), "diagnostics_r.png")

    # scatter with robust + OLS line, and a multi-fit comparison
    save(plot.scatter_with_fit(fit, show_ols=True, labels=labels),
         "scatter_with_fit.png")
    save(plot.compare_fits({"robust MM": fit}, x="copper"), "compare_fits.png")

    # ---- new analytical: residual vs leverage ----
    save(plot.resid_vs_leverage(fit, labels=labels), "resid_vs_leverage.png")

    # ---- customization: the four built-in themes ----
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, theme in zip(axes.ravel(), ("publication", "book", "minimal", "dark"),
                         strict=True):
        plot.residuals(fit, ax=ax, style=plot.set_theme(theme), colorbar=False,
                       title=theme)
    plot.set_theme("publication")
    fig.tight_layout()
    save(fig, "themes.png")

    # ---- multivariate (wine) ----
    wine = rpm.datasets.wine()
    rpm.set_seed(42)
    rob = rpm.cov_rob_mm(wine)
    cl = rpm.cov_classic(wine)
    save(plot.distance_distance(rob, cl), "distance_distance.png")
    save(plot.mahalanobis_panel(rob), "mahalanobis_panel.png")
    save(plot.cov_heatmap(rob, cl), "cov_heatmap_delta.png")

    rpm.set_seed(1)
    pr = rpm.prcomp_rob(wine)
    save(plot.scree(pr), "scree.png")
    save(plot.scores(pr, distances=rob.dist), "scores.png")
    save(plot.loadings(pr, ncomp=5), "loadings.png")
    save(plot.biplot(pr), "biplot.png")

    # ---- univariate (flour) ----
    flour = rpm.datasets.flour()
    col = flour.iloc[:, 0].to_numpy()
    ls = rpm.loc_scale_m(col)
    save(plot.location_scale(ls, col), "location_scale.png")

    print("\nAll gallery images written to", OUT)


if __name__ == "__main__":
    main()
