"""``robstatm_py.plot`` — native Python plotting suite.

Publication-quality, themable, composable figures that complement the Path-A
(R-via-rpy2) layer in :mod:`robstatm_py.plotting`. See ``docs/plotting_suite_plan.md``
and decision D-023.

Quickstart
----------
>>> import robstatm_py as rpm
>>> rpm.plot.set_theme("publication")           # doctest: +SKIP
>>> fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())  # doctest: +SKIP
>>> ax = rpm.plot.residuals(fit)                 # matplotlib Axes  # doctest: +SKIP
>>> ax = rpm.plot.residuals(fit, backend="r")    # PNG Path (Path A)  # doctest: +SKIP

Every plot function takes a uniform set of keywords: ``backend`` (``"auto"`` |
``"native"``/``"matplotlib"`` | ``"plotnine"`` | ``"r"``), ``ax=``/``fig=``,
``style=`` (a :class:`PlotStyle`), ``highlight=`` (indices), ``labels=``,
``annotate=``, ``title=``, ``save=``, ``show=``, plus per-call style overrides.

matplotlib/plotnine are optional (the ``[plots]`` extra); they are imported only
when a figure is actually drawn.
"""
from __future__ import annotations

from robstatm_py.plot._style import (
    OKABE_ITO,
    PlotStyle,
    get_theme,
    set_theme,
    theme_names,
)
from robstatm_py.plot.multivariate import (
    biplot,
    cov_heatmap,
    distance_distance,
    loadings,
    mahalanobis_panel,
    scores,
    scree,
)
from robstatm_py.plot.regression import (
    compare_fits,
    diagnostics,
    qq,
    resid_vs_leverage,
    residuals,
    scale_location,
    scatter_with_fit,
    weights,
)
from robstatm_py.plot.univariate import location_scale

__all__ = [
    # theming
    "PlotStyle",
    "set_theme",
    "get_theme",
    "theme_names",
    "OKABE_ITO",
    # regression diagnostics
    "residuals",
    "qq",
    "scale_location",
    "weights",
    "resid_vs_leverage",
    "diagnostics",
    "scatter_with_fit",
    "compare_fits",
    # multivariate
    "distance_distance",
    "mahalanobis_panel",
    "scree",
    "scores",
    "loadings",
    "biplot",
    "cov_heatmap",
    # univariate
    "location_scale",
]
