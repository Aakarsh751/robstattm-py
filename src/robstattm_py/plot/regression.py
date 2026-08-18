"""Native regression diagnostic plots.

All functions share a uniform signature::

    fn(fit, *, backend="auto", ax=None, style=None, highlight=None,
       labels=None, annotate=None, title=None, save=None, show=False, **kw)

* matplotlib (``backend="native"``/``"matplotlib"``, the default) returns an
  ``Axes`` (single panel) or ``Figure`` (``diagnostics``); accepts ``ax=`` and
  never calls ``plt.show()`` unless ``show=True``.
* ``backend="plotnine"`` returns a ``ggplot``.
* ``backend="r"`` calls the Path-A helpers in :mod:`robstattm_py.plotting` and
  returns a ``pathlib.Path`` to a PNG (refits in R, the fidelity reference).

Native renderers read only extracted arrays, they never re-fit (D-023). The one
exception is :func:`resid_vs_leverage`, which needs the hat matrix and calls
``fit.hatvalues()`` when ``leverage=`` is not supplied.
"""
from __future__ import annotations

from statistics import NormalDist
from typing import Any

import numpy as np

from robstattm_py.plot._backends import (
    finish,
    finish_fig,
    get_ax,
    r_kwargs,
    resolve_backend,
)
from robstattm_py.plot._data import (
    RegData,
    annotate_indices,
    flag_mask,
    regression_data,
)
from robstattm_py.plot._style import PlotStyle, resolve_style

_ND = NormalDist()


# ---------------------------------------------------------------------------
# shared matplotlib primitives
# ---------------------------------------------------------------------------

def _scatter(ax, x, y, data: RegData, style: PlotStyle, *, colorbar=True):
    """Scatter coloured by robust weight (or in/outlier split). Returns mappable."""
    if style.color_by_weight and data.rweights is not None:
        sc = ax.scatter(
            x, y, c=data.rweights, cmap=style.weight_cmap, vmin=0.0, vmax=1.0,
            s=style.point_size, alpha=style.alpha, edgecolors="none", zorder=2,
        )
        if colorbar:
            cb = ax.figure.colorbar(sc, ax=ax, pad=0.02)
            cb.set_label("Robust weight",
                         fontsize=style.base_fontsize * style.font_scale * 0.9)
            if style.text_color:
                cb.set_label("Robust weight", color=style.text_color)
                cb.ax.yaxis.set_tick_params(color=style.text_color)
        return sc

    mask = flag_mask(data, style)
    ax.scatter(
        x[~mask], y[~mask], color=style.inlier_color, s=style.point_size,
        alpha=style.alpha, edgecolors="none", zorder=2, label="inlier",
    )
    if mask.any():
        ax.scatter(
            x[mask], y[mask], color=style.outlier_color, s=style.point_size * 1.25,
            alpha=style.alpha, edgecolors="black", linewidths=0.5, zorder=3,
            label="flagged",
        )
    return None


def _label_points(ax, x, y, idx, labels, style: PlotStyle):
    color = style.text_color or "black"
    fs = style.base_fontsize * style.font_scale * 0.8
    for i in idx:
        text = (
            str(labels[i]) if labels is not None and i < len(labels) else str(i)
        )
        ax.annotate(
            text, (x[i], y[i]), xytext=(4, 4), textcoords="offset points",
            fontsize=fs, color=color, zorder=4,
        )


# ---------------------------------------------------------------------------
# residuals vs fitted
# ---------------------------------------------------------------------------

def residuals(
    fit,
    *,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Residuals-vs-fitted plot (R ``plot(fit, which=1)`` equivalent)."""
    be = resolve_backend(backend, has_native=True, has_r=True)
    if be == "r":
        from robstattm_py import plotting

        return plotting.residuals(fit, **r_kwargs(kw))
    if be == "plotnine":
        return _residuals_plotnine(fit, style, highlight, labels, annotate, title)

    st = resolve_style(style, **kw)
    data = regression_data(fit)
    _, ax, _ = get_ax(ax, st)
    _scatter(ax, data.fitted, data.residuals, data, st, colorbar=kw.get("colorbar", True))
    ax.axhline(0, color=st.ref_line_color, lw=1.0, ls="--", zorder=1)
    ax.set_xlabel("Fitted values")
    ax.set_ylabel("Residuals")
    _label_points(
        ax, data.fitted, data.residuals,
        annotate_indices(data, st, highlight, annotate), labels, st,
    )
    return finish(ax, st, title=title or "Residuals vs Fitted", save=save, show=show)


# ---------------------------------------------------------------------------
# normal Q-Q of standardized residuals
# ---------------------------------------------------------------------------

def _theoretical_quantiles(n: int) -> np.ndarray:
    return np.array([_ND.inv_cdf((i + 0.5) / n) for i in range(n)])


def qq(
    fit,
    *,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Normal Q-Q plot of standardized robust residuals (R ``which=2``)."""
    be = resolve_backend(backend, has_native=True, has_r=True)
    if be == "r":
        from robstattm_py import plotting

        return plotting.qq(fit, **r_kwargs(kw))
    if be == "plotnine":
        return _qq_plotnine(fit, style, title)

    st = resolve_style(style, **kw)
    data = regression_data(fit)
    n = data.n
    z = data.std_resid
    order = np.argsort(z)
    ranks = np.empty(n, dtype=int)
    ranks[order] = np.arange(n)
    theo_sorted = _theoretical_quantiles(n)
    theo = theo_sorted[ranks]  # theoretical quantile aligned to original index

    _, ax, _ = get_ax(ax, st)
    _scatter(ax, theo, z, data, st, colorbar=kw.get("colorbar", True))

    # robust Q-Q reference line through the 1st & 3rd sample/theoretical quartiles.
    qs = (0.25, 0.75)
    sq = np.quantile(z, qs)
    tq = np.array([_ND.inv_cdf(p) for p in qs])
    slope = (sq[1] - sq[0]) / (tq[1] - tq[0])
    intercept = sq[0] - slope * tq[0]
    xs = np.array([theo.min(), theo.max()])
    ax.plot(xs, slope * xs + intercept, color=st.fit_color, lw=1.2, zorder=1)

    ax.set_xlabel("Theoretical quantiles")
    ax.set_ylabel("Standardized residuals")
    _label_points(ax, theo, z, annotate_indices(data, st, highlight, annotate), labels, st)
    return finish(ax, st, title=title or "Normal Q-Q", save=save, show=show)


# ---------------------------------------------------------------------------
# scale-location
# ---------------------------------------------------------------------------

def scale_location(
    fit,
    *,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Scale-location plot: sqrt(|standardized residual|) vs fitted (R ``which=3``)."""
    be = resolve_backend(backend, has_native=True, has_r=False)
    if be == "plotnine":
        return _scale_location_plotnine(fit, style, title)

    st = resolve_style(style, **kw)
    data = regression_data(fit)
    root = np.sqrt(np.abs(data.std_resid))
    _, ax, _ = get_ax(ax, st)
    _scatter(ax, data.fitted, root, data, st, colorbar=kw.get("colorbar", True))
    ax.set_xlabel("Fitted values")
    ax.set_ylabel(r"$\sqrt{|\mathrm{standardized\ residual}|}$")
    _label_points(
        ax, data.fitted, root,
        annotate_indices(data, st, highlight, annotate), labels, st,
    )
    return finish(ax, st, title=title or "Scale-Location", save=save, show=show)


# ---------------------------------------------------------------------------
# robust weights vs index
# ---------------------------------------------------------------------------

def weights(
    fit,
    *,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Robust weight vs observation index, with the down-weighting cutoff line."""
    be = resolve_backend(backend, has_native=True, has_r=False)
    if be == "plotnine":
        return _weights_plotnine(fit, style, title)

    st = resolve_style(style, **kw)
    data = regression_data(fit)
    if data.rweights is None:
        raise TypeError(
            f"{type(fit).__name__} has no 'rweights'; weights() needs a robust fit"
        )
    w = data.rweights
    idx = data.index
    mask = w < st.outlier_weight_thresh

    _, ax, _ = get_ax(ax, st)
    ax.vlines(idx, 0, w, color=st.ref_line_color, alpha=0.4, lw=0.8, zorder=1)
    ax.scatter(idx[~mask], w[~mask], color=st.inlier_color, s=st.point_size,
               alpha=st.alpha, edgecolors="none", zorder=2)
    if mask.any():
        ax.scatter(idx[mask], w[mask], color=st.outlier_color,
                   s=st.point_size * 1.25, alpha=st.alpha, edgecolors="black",
                   linewidths=0.5, zorder=3)
    ax.axhline(st.outlier_weight_thresh, color=st.cutoff_color, ls=":", lw=1.0,
               zorder=1, label=f"cutoff = {st.outlier_weight_thresh:g}")
    ax.set_xlabel("Observation index")
    ax.set_ylabel("Robust weight")
    ax.set_ylim(-0.02, 1.05)

    label_idx = sorted(set(int(i) for i in np.nonzero(mask)[0]) |
                       (set(int(i) for i in highlight) if highlight is not None else set()))
    if annotate is False:
        label_idx = [int(i) for i in highlight] if highlight is not None else []
    _label_points(ax, idx, w, label_idx, labels, st)
    return finish(ax, st, title=title or "Robust weights", save=save, show=show)


# ---------------------------------------------------------------------------
# residual vs leverage  (needs the hat matrix → fit.hatvalues())
# ---------------------------------------------------------------------------

def resid_vs_leverage(
    fit,
    *,
    leverage=None,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Standardized residual vs leverage (influence diagnostic).

    Leverage requires the hat matrix; if ``leverage`` is not provided this calls
    ``fit.hatvalues()`` (which refits in R). All other native plots are
    refit-free.
    """
    be = resolve_backend(backend, has_native=True, has_r=False)
    st = resolve_style(style, **kw)
    data = regression_data(fit)

    if leverage is None:
        hv = getattr(fit, "hatvalues", None)
        if not callable(hv):
            raise TypeError(
                "resid_vs_leverage needs leverages: pass leverage=... or use a "
                "fit exposing .hatvalues()"
            )
        leverage = hv()
    lev = np.asarray(leverage, float).ravel()

    if be == "plotnine":
        return _resid_vs_leverage_plotnine(fit, lev, st, title)

    _, ax, _ = get_ax(ax, st)
    _scatter(ax, lev, data.std_resid, data, st, colorbar=kw.get("colorbar", True))
    ax.axhline(0, color=st.ref_line_color, lw=1.0, ls="--", zorder=1)
    high_lev = 2.0 * lev.mean() if lev.size else 0.0
    if high_lev > 0:
        ax.axvline(high_lev, color=st.cutoff_color, ls=":", lw=1.0, zorder=1,
                   label=f"2·mean leverage = {high_lev:.3g}")
    ax.set_xlabel("Leverage (hat value)")
    ax.set_ylabel("Standardized residuals")
    _label_points(
        ax, lev, data.std_resid,
        annotate_indices(data, st, highlight, annotate), labels, st,
    )
    return finish(ax, st, title=title or "Residuals vs Leverage", save=save, show=show)


# ---------------------------------------------------------------------------
# 2x2 diagnostic panel
# ---------------------------------------------------------------------------

def diagnostics(
    fit,
    *,
    backend: str = "auto",
    fig: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """2x2 diagnostic panel: residuals, Q-Q, scale-location, robust weights.

    Returns a matplotlib ``Figure`` (native) or a ``pathlib.Path`` (``backend="r"``).
    """
    be = resolve_backend(backend, has_native=True, has_r=True)
    if be == "r":
        from robstattm_py import plotting

        return plotting.diagnostics(fit, **r_kwargs(kw))

    from robstattm_py.plot._deps import require_pyplot

    st = resolve_style(style, **kw)
    plt = require_pyplot()
    if fig is None:
        fig, axes = plt.subplots(2, 2, figsize=(st.figsize[0] * 1.7, st.figsize[1] * 1.6),
                                 dpi=st.dpi)
    else:
        axes = np.array(fig.axes).reshape(2, 2) if len(fig.axes) >= 4 else fig.subplots(2, 2)
    a = axes.ravel()
    # suppress per-panel colorbars in the grid for a clean layout
    residuals(fit, ax=a[0], style=st, highlight=highlight, labels=labels,
              annotate=annotate, colorbar=False)
    qq(fit, ax=a[1], style=st, highlight=highlight, labels=labels,
       annotate=annotate, colorbar=False)
    scale_location(fit, ax=a[2], style=st, highlight=highlight, labels=labels,
                   annotate=annotate, colorbar=False)
    weights(fit, ax=a[3], style=st, highlight=highlight, labels=labels,
            annotate=annotate)
    return finish_fig(fig, st, suptitle=title or "Robust regression diagnostics",
                      save=save, show=show)


# ---------------------------------------------------------------------------
# plotnine (secondary engine) - minimal grammar-of-graphics equivalents
# ---------------------------------------------------------------------------

def _reg_df(fit):
    import pandas as pd

    data = regression_data(fit)
    df = pd.DataFrame({
        "fitted": data.fitted,
        "residuals": data.residuals,
        "std_resid": data.std_resid,
        "index": data.index,
    })
    if data.rweights is not None:
        df["weight"] = data.rweights
    return df, data


def _residuals_plotnine(fit, style, highlight, labels, annotate, title):
    from plotnine import (
        aes,
        geom_hline,
        geom_point,
        ggplot,
        labs,
        scale_color_cmap,
        theme_bw,
    )

    df, data = _reg_df(fit)
    st = resolve_style(style)
    color = "weight" if "weight" in df and st.color_by_weight else None
    mapping = aes("fitted", "residuals", **({"color": color} if color else {}))
    g = (
        ggplot(df, mapping)
        + geom_hline(yintercept=0, linetype="dashed", color=st.ref_line_color)
        + geom_point(alpha=st.alpha)
        + labs(x="Fitted values", y="Residuals", title=title or "Residuals vs Fitted")
        + theme_bw()
    )
    if color:
        g = g + scale_color_cmap(name="Robust weight", cmap_name=st.weight_cmap)
    return g


def _qq_plotnine(fit, style, title):
    import pandas as pd
    from plotnine import aes, geom_abline, geom_point, ggplot, labs, theme_bw

    data = regression_data(fit)
    z = np.sort(data.std_resid)
    n = z.size
    theo = _theoretical_quantiles(n)
    df = pd.DataFrame({"theo": theo, "sample": z})
    qs = (0.25, 0.75)
    sq = np.quantile(z, qs)
    tq = np.array([_ND.inv_cdf(p) for p in qs])
    slope = (sq[1] - sq[0]) / (tq[1] - tq[0])
    intercept = sq[0] - slope * tq[0]
    st = resolve_style(style)
    return (
        ggplot(df, aes("theo", "sample"))
        + geom_abline(slope=slope, intercept=intercept, color=st.fit_color)
        + geom_point(alpha=st.alpha)
        + labs(x="Theoretical quantiles", y="Standardized residuals",
               title=title or "Normal Q-Q")
        + theme_bw()
    )


def _scale_location_plotnine(fit, style, title):
    from plotnine import aes, geom_point, ggplot, labs, theme_bw

    df, _ = _reg_df(fit)
    df["root"] = np.sqrt(np.abs(df["std_resid"]))
    st = resolve_style(style)
    return (
        ggplot(df, aes("fitted", "root"))
        + geom_point(alpha=st.alpha)
        + labs(x="Fitted values", y="sqrt(|standardized residual|)",
               title=title or "Scale-Location")
        + theme_bw()
    )


def _weights_plotnine(fit, style, title):
    from plotnine import aes, geom_hline, geom_point, ggplot, labs, theme_bw

    df, _ = _reg_df(fit)
    st = resolve_style(style)
    if "weight" not in df:
        raise TypeError("weights() needs a robust fit with rweights")
    return (
        ggplot(df, aes("index", "weight"))
        + geom_hline(yintercept=st.outlier_weight_thresh, linetype="dotted",
                     color=st.cutoff_color)
        + geom_point(alpha=st.alpha)
        + labs(x="Observation index", y="Robust weight",
               title=title or "Robust weights")
        + theme_bw()
    )


def _resid_vs_leverage_plotnine(fit, lev, style, title):
    import pandas as pd
    from plotnine import aes, geom_hline, geom_point, ggplot, labs, theme_bw

    data = regression_data(fit)
    df = pd.DataFrame({"leverage": lev, "std_resid": data.std_resid})
    st = resolve_style(style)
    return (
        ggplot(df, aes("leverage", "std_resid"))
        + geom_hline(yintercept=0, linetype="dashed", color=st.ref_line_color)
        + geom_point(alpha=st.alpha)
        + labs(x="Leverage (hat value)", y="Standardized residuals",
               title=title or "Residuals vs Leverage")
        + theme_bw()
    )


# ---------------------------------------------------------------------------
# scatter with fitted line(s)  (mineral Figs 5.1 / 5.4 / 5.7)
# ---------------------------------------------------------------------------

def _response_name(formula: str) -> str:
    return formula.split("~", 1)[0].strip()


def _line_from_fit(fit, xname: str, xs: np.ndarray):
    """Evaluate the fitted line for a simple-regression term over ``xs``.

    Returns ``None`` when the fit isn't expressible as a line in ``xname``
    (more than one non-intercept predictor).
    """
    names = list(getattr(fit, "coef_names", ()) or ())
    coefs = np.asarray(getattr(fit, "coefficients", []), float).ravel()
    if not names or coefs.size != len(names):
        return None
    intercept = 0.0
    slope = None
    extra = 0
    for n, c in zip(names, coefs, strict=False):
        if n in ("(Intercept)", "Intercept"):
            intercept = float(c)
        elif n == xname:
            slope = float(c)
        else:
            extra += 1
    if slope is None or extra > 0:
        return None
    return intercept + slope * xs


def _infer_predictor(fit, x):
    if x is not None:
        return x
    names = [n for n in (getattr(fit, "coef_names", ()) or ())
             if n not in ("(Intercept)", "Intercept")]
    if len(names) == 1:
        return names[0]
    raise ValueError(
        "could not infer the predictor to plot against; pass x='<column>'"
    )


def scatter_with_fit(
    fit,
    *,
    x: str | None = None,
    data=None,
    show_ols: bool = False,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    annotate: bool | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Scatter of response vs one predictor with the robust fitted line.

    Points are coloured by robust weight (when available). For a simple
    regression the robust line is drawn from the fitted coefficients (no refit);
    set ``show_ols=True`` to overlay an ordinary least-squares line for contrast.
    Reproduces mineral Figs 5.1 / 5.4.
    """
    be = resolve_backend(backend, has_native=True, has_r=False, has_plotnine=True)
    if be == "plotnine":
        return _scatter_with_fit_plotnine(fit, x, data, show_ols, style, title)
    st = resolve_style(style, **kw)
    df = data if data is not None else getattr(fit, "_data", None)
    if df is None:
        raise ValueError(
            "scatter_with_fit needs the fit's data; it is unavailable (was the "
            "fit unpickled?). Pass data=<DataFrame>."
        )
    xname = _infer_predictor(fit, x)
    yname = _response_name(getattr(fit, "formula", ""))
    if yname not in df or xname not in df:
        raise ValueError(f"columns {yname!r}/{xname!r} not found in the data")
    xv = np.asarray(df[xname], float)
    yv = np.asarray(df[yname], float)
    rdata = regression_data(fit)

    _, ax, _ = get_ax(ax, st)
    _scatter(ax, xv, yv, rdata, st, colorbar=kw.get("colorbar", True))

    xs = np.linspace(xv.min(), xv.max(), 100)
    line = _line_from_fit(fit, xname, xs)
    if line is not None:
        ax.plot(xs, line, color=st.fit_color, lw=1.8, zorder=4, label="robust fit")
    if show_ols:
        slope, intercept = np.polyfit(xv, yv, 1)
        ax.plot(xs, intercept + slope * xs, color=st.ols_color, lw=1.4, ls="--",
                zorder=3, label="OLS")
    ax.set_xlabel(xname)
    ax.set_ylabel(yname)
    if line is not None or show_ols:
        ax.legend(fontsize=st.base_fontsize * st.font_scale * 0.85)
    _label_points(
        ax, xv, yv, annotate_indices(rdata, st, highlight, annotate), labels, st,
    )
    return finish(ax, st, title=title or f"{yname} vs {xname}", save=save, show=show)


# ---------------------------------------------------------------------------
# compare several fits on one scatter  (mineral Figs 5.1 / 5.7)
# ---------------------------------------------------------------------------

def compare_fits(
    fits,
    *,
    x: str | None = None,
    data=None,
    extra_lines=None,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Overlay several fitted lines on one scatter to compare estimators.

    Parameters
    ----------
    fits : mapping or sequence
        ``{label: fit}`` or a sequence of fits. Each contributes a line.
    x : str, optional
        Predictor column; inferred from a simple regression when omitted.
    extra_lines : sequence of (slope, intercept, label), optional
        Additional reference lines (e.g. a hand-computed OLS / L1 fit).

    Reproduces mineral Figs 5.1 (LS / L1 / robust) and 5.7.
    """
    be = resolve_backend(backend, has_native=True, has_r=False, has_plotnine=True)
    if be == "plotnine":
        return _compare_fits_plotnine(fits, x, data, extra_lines, style, title)
    st = resolve_style(style, **kw)

    items = list(fits.items()) if hasattr(fits, "items") else [
        (f"fit {i}", f) for i, f in enumerate(fits)
    ]
    if not items:
        raise ValueError("compare_fits needs at least one fit")

    ref_fit = items[0][1]
    df = data if data is not None else getattr(ref_fit, "_data", None)
    if df is None:
        raise ValueError("compare_fits needs the data; pass data=<DataFrame>.")
    xname = _infer_predictor(ref_fit, x)
    yname = _response_name(getattr(ref_fit, "formula", ""))
    xv = np.asarray(df[xname], float)
    yv = np.asarray(df[yname], float)

    _, ax, _ = get_ax(ax, st)
    ax.scatter(xv, yv, color=st.inlier_color, s=st.point_size, alpha=0.55,
               edgecolors="none", zorder=2)
    xs = np.linspace(xv.min(), xv.max(), 100)
    palette = st.palette
    ci = 0
    for label, fit in items:
        line = _line_from_fit(fit, xname, xs)
        if line is None:
            continue
        ax.plot(xs, line, color=palette[ci % len(palette)], lw=1.8, zorder=4,
                label=label)
        ci += 1
    for sl, ic, label in (extra_lines or []):
        ax.plot(xs, ic + sl * xs, color=palette[ci % len(palette)], lw=1.6,
                ls="--", zorder=3, label=label)
        ci += 1
    ax.set_xlabel(xname)
    ax.set_ylabel(yname)
    ax.legend(fontsize=st.base_fontsize * st.font_scale * 0.85)
    return finish(ax, st, title=title or f"{yname} vs {xname}: fit comparison",
                  save=save, show=show)


def _scatter_with_fit_plotnine(fit, x, data, show_ols, style, title):
    import pandas as pd
    from plotnine import aes, geom_abline, geom_point, ggplot, labs, theme_bw

    st = resolve_style(style)
    df = data if data is not None else getattr(fit, "_data", None)
    if df is None:
        raise ValueError("scatter_with_fit needs the fit's data; pass data=.")
    xname = _infer_predictor(fit, x)
    yname = _response_name(getattr(fit, "formula", ""))
    xv = np.asarray(df[xname], float)
    yv = np.asarray(df[yname], float)
    pdf = pd.DataFrame({xname: xv, yname: yv})
    g = ggplot(pdf, aes(xname, yname)) + geom_point(alpha=st.alpha)

    line = _line_from_fit(fit, xname, np.array([0.0, 1.0]))
    if line is not None:
        intercept = float(line[0])
        slope = float(line[1] - line[0])
        g = g + geom_abline(slope=slope, intercept=intercept, color=st.fit_color)
    if show_ols:
        sl, ic = np.polyfit(xv, yv, 1)
        g = g + geom_abline(slope=sl, intercept=ic, color=st.ols_color,
                            linetype="dashed")
    return g + labs(title=title or f"{yname} vs {xname}") + theme_bw()


def _compare_fits_plotnine(fits, x, data, extra_lines, style, title):
    import pandas as pd
    from plotnine import aes, geom_abline, geom_point, ggplot, labs, theme_bw

    st = resolve_style(style)
    items = list(fits.items()) if hasattr(fits, "items") else [
        (f"fit {i}", f) for i, f in enumerate(fits)
    ]
    if not items:
        raise ValueError("compare_fits needs at least one fit")
    ref_fit = items[0][1]
    df = data if data is not None else getattr(ref_fit, "_data", None)
    if df is None:
        raise ValueError("compare_fits needs the data; pass data=.")
    xname = _infer_predictor(ref_fit, x)
    yname = _response_name(getattr(ref_fit, "formula", ""))
    xv = np.asarray(df[xname], float)
    yv = np.asarray(df[yname], float)
    pdf = pd.DataFrame({xname: xv, yname: yv})
    g = ggplot(pdf, aes(xname, yname)) + geom_point(alpha=0.55,
                                                    color=st.inlier_color)
    palette = st.palette
    ci = 0
    for _label, fit in items:
        line = _line_from_fit(fit, xname, np.array([0.0, 1.0]))
        if line is None:
            continue
        intercept = float(line[0])
        slope = float(line[1] - line[0])
        g = g + geom_abline(slope=slope, intercept=intercept,
                            color=palette[ci % len(palette)])
        ci += 1
    for sl, ic, _label in (extra_lines or []):
        g = g + geom_abline(slope=sl, intercept=ic,
                            color=palette[ci % len(palette)], linetype="dashed")
        ci += 1
    return g + labs(title=title or f"{yname} vs {xname}: fit comparison") + theme_bw()
