"""Build ``notebooks/plotting_suite_demo.ipynb``.

Run: ``python notebooks/_build_plotting_demo.py`` (writes the .ipynb next to it).
The notebook is then executed end-to-end by ``tests/test_notebooks.py`` (D-019).
"""
from __future__ import annotations

import pathlib

import nbformat as nbf

nb = nbf.v4.new_notebook()
cells: list = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text.strip("\n")))


md(r"""
# Native plotting suite — demo (`robstatm_py.plot`)

This notebook tours the **native Python plotting suite** added in decision D-023
and compares it with the original **Path A** (R graphics through `rpy2`).

- **Native** (matplotlib, the default) → composable `Axes`/`Figure`, themable,
  outliers annotated, points coloured by robust weight. Never re-fits.
- **`backend="r"`** → the exact R panel (pixel-faithful fidelity reference).

See the [Plotting guide](../docs/guides/plotting.md) and
`docs/plotting_suite_plan.md`.
""")

md("## Setup\n\nOn Windows, point `rpy2` at R before importing the package.")

code(r"""
import os, sys, pathlib

if sys.platform == "win32" and "R_HOME" not in os.environ:
    os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
    os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]

%matplotlib inline
import matplotlib.pyplot as plt
import numpy as np

import robstatm_py as rpm
from robstatm_py import plot
from robstatm_py.plotting import show_png   # Path-A PNG display helper

FIG_DIR = pathlib.Path("figures"); FIG_DIR.mkdir(exist_ok=True)
plot.set_theme("publication")
print("robstatm_py", rpm.__version__)
""")

md("""
## 1. Regression diagnostics — native vs Path A

The native renderer reproduces the textbook diagnostics and adds robust-weight
colouring + automatic outlier labels. `backend="r"` returns the exact R PNG.
""")

code(r"""
mineral = rpm.datasets.mineral()
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
labels = [str(i) for i in range(len(fit.residuals))]

ax = plot.residuals(fit, labels=labels)   # native -> matplotlib Axes (displays inline)
ax.figure
""")

code(r"""
# Same plot, drawn by R's own graphics device (Path A). Returns a PNG path.
png = plot.residuals(fit, backend="r")
show_png(png)
""")

code(r"""
# The full 2x2 diagnostic panel, native.
fig = fit.plot_diagnostics()      # shortcut == plot.diagnostics(fit)
fig
""")

md("""
## 2. Scatter with the robust fit (Figs 5.1 / 5.4)

Observed data with the robust fitted line, plus an OLS line for contrast — note
how the high-leverage point drags OLS but not the robust fit.
""")

code(r"""
plot.scatter_with_fit(fit, show_ols=True, labels=labels).figure
""")

md("""
## 3. Customization — themes & per-call overrides

`set_theme` sets a global look; any `PlotStyle` field can be overridden per call.
""")

code(r"""
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
for ax, theme in zip(axes.ravel(), ("publication", "book", "minimal", "dark")):
    plot.residuals(fit, ax=ax, style=plot.set_theme(theme), colorbar=False, title=theme)
plot.set_theme("publication")
fig.tight_layout(); fig
""")

code(r"""
# Per-call style override: custom colormap, bigger markers, custom thresholds.
style = plot.PlotStyle(weight_cmap="magma", point_size=60, outlier_weight_thresh=0.6)
plot.residuals(fit, style=style, labels=labels).figure
""")

md("""
## 4. Multivariate — robust covariance & PCA (wine)

The **distance–distance** plot unmasks the multivariate outliers that the
classical covariance hides.
""")

code(r"""
wine = rpm.datasets.wine()
rpm.set_seed(42)
rob = rpm.cov_rob_mm(wine)
cl  = rpm.cov_classic(wine)

fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
plot.distance_distance(rob, cl, ax=ax[0])
plot.mahalanobis_panel(rob, ax=ax[1])
fig.tight_layout(); fig
""")

code(r"""
# Robust PCA (prcomp_rob gives full rank): scree, scores, biplot.
rpm.set_seed(1)
pr = rpm.prcomp_rob(wine)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
plot.scree(pr, ax=ax[0])
plot.scores(pr, distances=rob.dist, ax=ax[1])
plot.biplot(pr, ax=ax[2])
fig.tight_layout(); fig
""")

md("""
## 5. Univariate — robust location & scale (flour)

Robust μ ± dispersion hugs the bulk of the data; the classical mean ± sd is
inflated by the outlier.
""")

code(r"""
col = rpm.datasets.flour().iloc[:, 0].to_numpy()
ls = rpm.loc_scale_m(col)
plot.location_scale(ls, col).figure
""")

md("""
## 6. New analytical views (not in the textbook notebooks)

Working with the data directly in Python: a robust influence diagnostic and the
robust − classical correlation difference.
""")

code(r"""
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
plot.resid_vs_leverage(fit, labels=labels, ax=ax[0])
plot.cov_heatmap(rob, cl, ax=ax[1])
fig.tight_layout(); fig
""")

md("## 7. Reproducibility")

code(r"""
import matplotlib, numpy, pandas
print("robstatm_py", rpm.__version__)
print("numpy", numpy.__version__, "| pandas", pandas.__version__,
      "| matplotlib", matplotlib.__version__)
""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}

out = pathlib.Path(__file__).resolve().parent / "plotting_suite_demo.ipynb"
nbf.write(nb, str(out))
print("wrote", out)
