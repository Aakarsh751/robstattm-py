"""Native univariate plot — robust location & scale.

Visualises a :class:`~robstatm_py.univariate.loc_scale_m.LocScaleMResult` over
the sample it was computed from: a histogram/density with the robust location
band (μ ± dispersion) and, optionally, the classical mean ± sd band for
contrast. Reads only the result's scalars (``mu``, ``disper``) — no re-fit.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from robstatm_py.plot._backends import finish, get_ax, resolve_backend
from robstatm_py.plot._style import PlotStyle, resolve_style


def location_scale(
    result,
    data,
    *,
    bins: int | str = "auto",
    density: bool = True,
    show_classical: bool = True,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Histogram of ``data`` with the robust μ ± dispersion band.

    Parameters
    ----------
    result : LocScaleMResult
        Output of :func:`robstatm_py.loc_scale_m` (provides ``mu``/``disper``).
    data : array_like
        The 1-D sample the estimate was computed from.
    show_classical : bool, default True
        Also draw the classical mean ± sd band for comparison.
    """
    be = resolve_backend(backend, has_native=True, has_r=False, has_plotnine=True)
    if be == "plotnine":
        return _location_scale_plotnine(result, data, bins, density, show_classical,
                                        style, title)
    st = resolve_style(style, **kw)
    x = np.asarray(data, float).ravel()
    x = x[~np.isnan(x)]

    mu = float(result.mu)
    disper = float(result.disper)

    _, ax, _ = get_ax(ax, st)
    ax.hist(x, bins=bins, density=density, color=st.inlier_color, alpha=0.45,
            edgecolor="white", linewidth=0.5, zorder=1)

    ax.axvline(mu, color=st.outlier_color, lw=1.6, zorder=4,
               label=f"robust μ = {mu:.3g}")
    ax.axvspan(mu - disper, mu + disper, color=st.outlier_color, alpha=0.12,
               zorder=2, label=f"robust μ ± disp ({disper:.3g})")

    if show_classical:
        m = float(np.mean(x))
        s = float(np.std(x, ddof=1))
        ax.axvline(m, color=st.ref_line_color, lw=1.4, ls="--", zorder=3,
                   label=f"mean = {m:.3g}")
        ax.axvspan(m - s, m + s, facecolor="none", edgecolor=st.ref_line_color,
                   hatch="///", alpha=0.5, zorder=2, label=f"mean ± sd ({s:.3g})")

    ax.set_xlabel("Value")
    ax.set_ylabel("Density" if density else "Count")
    ax.legend(fontsize=st.base_fontsize * st.font_scale * 0.8)
    return finish(ax, st, title=title or "Robust location & scale", save=save, show=show)


def _location_scale_plotnine(result, data, bins, density, show_classical, style, title):
    import pandas as pd
    from plotnine import (
        aes,
        geom_histogram,
        geom_vline,
        ggplot,
        labs,
        theme_bw,
    )

    st = resolve_style(style)
    x = np.asarray(data, float).ravel()
    x = x[~np.isnan(x)]
    mu = float(result.mu)
    disper = float(result.disper)
    nbins = 30 if bins in ("auto", None) else int(bins) if isinstance(bins, int) else 30
    df = pd.DataFrame({"value": x})
    y_aes = "stat(density)" if density else "stat(count)"
    g = (
        ggplot(df, aes("value"))
        + geom_histogram(aes(y=y_aes), bins=nbins, fill=st.inlier_color, alpha=0.45,
                         color="white")
        + geom_vline(xintercept=mu, color=st.outlier_color, size=1.0)
        + geom_vline(xintercept=[mu - disper, mu + disper], color=st.outlier_color,
                     linetype="dotted")
    )
    if show_classical:
        m = float(np.mean(x))
        s = float(np.std(x, ddof=1))
        g = (g + geom_vline(xintercept=m, color=st.ref_line_color, linetype="dashed")
             + geom_vline(xintercept=[m - s, m + s], color=st.ref_line_color,
                          linetype="dotdash"))
    return g + labs(x="Value", y="Density" if density else "Count",
                    title=title or "Robust location & scale") + theme_bw()
