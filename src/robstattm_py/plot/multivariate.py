"""Native multivariate plots — robust covariance & robust PCA.

Renderers read only the extracted arrays on the covariance / PCA result
dataclasses (``dist``, ``cov``, ``cor``, ``repre``/``scores``,
``eigvec``/``rotation``, ``prop_spc``/``sdev``). They never re-fit (D-023).

All functions return a matplotlib ``Axes`` and accept ``ax=``, ``style=``,
``highlight=``, ``labels=``, ``title=``, ``save=``, ``show=``, plus per-call
style overrides. ``backend="r"`` is not offered for these (no single Path-A R
function); ``backend="auto"``/``"native"``/``"matplotlib"`` all use matplotlib.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from robstattm_py.plot._backends import finish, get_ax, resolve_backend
from robstattm_py.plot._data import (
    chi2_quantile,
    corr_from_cov,
    maha_distance,
    pca_loadings,
    pca_proportions,
    pca_scores,
)
from robstattm_py.plot._style import PlotStyle, resolve_style


def _col_names(result: object, p: int) -> list[str]:
    names = getattr(result, "column_names", None)
    if names is not None and len(names) == p:
        return [str(n) for n in names]
    return [f"V{i + 1}" for i in range(p)]


def _native(backend: str, *, has_r: bool = False, has_plotnine: bool = True) -> str:
    return resolve_backend(backend, has_native=True, has_r=has_r,
                           has_plotnine=has_plotnine)


def _label(ax, x, y, idx, labels, style: PlotStyle):
    color = style.text_color or "black"
    fs = style.base_fontsize * style.font_scale * 0.8
    for i in idx:
        text = str(labels[i]) if labels is not None and i < len(labels) else str(i)
        ax.annotate(text, (x[i], y[i]), xytext=(4, 4), textcoords="offset points",
                    fontsize=fs, color=color, zorder=4)


# ---------------------------------------------------------------------------
# distance-distance plot (robust vs classical Mahalanobis)
# ---------------------------------------------------------------------------

def distance_distance(
    robust,
    classical,
    *,
    level: float = 0.975,
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
    """Robust vs classical Mahalanobis distance, with the χ² outlier cutoff.

    Points above the robust cutoff are flagged outliers (the robust fit detects
    multivariate outliers the classical fit masks). Pass a robust covariance
    result (``cov_rob_mm`` / ``cov_rob_rocke``) and a ``cov_classic`` result.
    """
    if _native(backend) == "plotnine":
        return _distance_distance_plotnine(robust, classical, level, style, title)
    st = resolve_style(style, **kw)
    rd = maha_distance(robust)
    cd = maha_distance(classical)
    p = np.asarray(robust.cov, float).shape[0]
    cut = float(np.sqrt(chi2_quantile(level, p)))

    flagged = rd > cut
    _, ax, _ = get_ax(ax, st)
    ax.scatter(cd[~flagged], rd[~flagged], color=st.inlier_color, s=st.point_size,
               alpha=st.alpha, edgecolors="none", zorder=2, label="inlier")
    if flagged.any():
        ax.scatter(cd[flagged], rd[flagged], color=st.outlier_color,
                   s=st.point_size * 1.25, alpha=st.alpha, edgecolors="black",
                   linewidths=0.5, zorder=3, label="outlier")
    ax.axhline(cut, color=st.cutoff_color, ls=":", lw=1.0, zorder=1)
    ax.axvline(cut, color=st.cutoff_color, ls=":", lw=1.0, zorder=1,
               label=f"χ² cutoff ({level:g})")
    lim = max(cd.max(), rd.max()) * 1.02
    ax.plot([0, lim], [0, lim], color=st.ref_line_color, ls="--", lw=0.8, zorder=1)
    ax.set_xlabel("Classical Mahalanobis distance")
    ax.set_ylabel("Robust Mahalanobis distance")

    idx = set(int(i) for i in np.nonzero(flagged)[0]) if (
        st.annotate_outliers if annotate is None else annotate) else set()
    if highlight is not None:
        idx |= {int(i) for i in highlight}
    _label(ax, cd, rd, sorted(idx), labels, st)
    return finish(ax, st, title=title or "Distance–distance plot", save=save, show=show)


# ---------------------------------------------------------------------------
# Mahalanobis index panel
# ---------------------------------------------------------------------------

def mahalanobis_panel(
    cov,
    *,
    level: float = 0.975,
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
    """Robust Mahalanobis distance vs observation index, with χ² cutoff."""
    if _native(backend) == "plotnine":
        return _mahalanobis_panel_plotnine(cov, level, style, title)
    st = resolve_style(style, **kw)
    d = maha_distance(cov)
    p = np.asarray(cov.cov, float).shape[0]
    cut = float(np.sqrt(chi2_quantile(level, p)))
    idx = np.arange(d.size)
    flagged = d > cut

    _, ax, _ = get_ax(ax, st)
    ax.vlines(idx, 0, d, color=st.ref_line_color, alpha=0.35, lw=0.8, zorder=1)
    ax.scatter(idx[~flagged], d[~flagged], color=st.inlier_color, s=st.point_size,
               alpha=st.alpha, edgecolors="none", zorder=2)
    if flagged.any():
        ax.scatter(idx[flagged], d[flagged], color=st.outlier_color,
                   s=st.point_size * 1.25, alpha=st.alpha, edgecolors="black",
                   linewidths=0.5, zorder=3)
    ax.axhline(cut, color=st.cutoff_color, ls=":", lw=1.0, zorder=1,
               label=f"χ² cutoff ({level:g})")
    ax.set_xlabel("Observation index")
    ax.set_ylabel("Robust Mahalanobis distance")

    lab = set(int(i) for i in np.nonzero(flagged)[0]) if (
        st.annotate_outliers if annotate is None else annotate) else set()
    if highlight is not None:
        lab |= {int(i) for i in highlight}
    _label(ax, idx, d, sorted(lab), labels, st)
    return finish(ax, st, title=title or "Robust Mahalanobis distances",
                  save=save, show=show)


# ---------------------------------------------------------------------------
# scree
# ---------------------------------------------------------------------------

def scree(
    pca,
    *,
    cumulative: bool = True,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Scree plot: per-component proportion of (robust) variance / scale."""
    if _native(backend) == "plotnine":
        return _scree_plotnine(pca, cumulative, style, title)
    st = resolve_style(style, **kw)
    prop = pca_proportions(pca)
    k = prop.size
    comp = np.arange(1, k + 1)

    _, ax, _ = get_ax(ax, st)
    ax.bar(comp, prop, color=st.inlier_color, alpha=st.alpha, zorder=2,
           label="proportion")
    if cumulative:
        ax.plot(comp, np.cumsum(prop), color=st.outlier_color, marker="o",
                ms=4, lw=1.2, zorder=3, label="cumulative")
    ax.set_xlabel("Principal component")
    ax.set_ylabel("Proportion of variance")
    ax.set_xticks(comp)
    ax.legend(fontsize=st.base_fontsize * st.font_scale * 0.85)
    return finish(ax, st, title=title or "Scree plot", save=save, show=show)


# ---------------------------------------------------------------------------
# scores scatter
# ---------------------------------------------------------------------------

def scores(
    pca,
    *,
    comps: tuple[int, int] = (0, 1),
    distances=None,
    level: float = 0.975,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    highlight=None,
    labels=None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Scatter of two principal-component scores.

    If ``distances`` (robust Mahalanobis distances, e.g. from a companion
    covariance fit) are supplied, points beyond the χ² cutoff are flagged.
    """
    if _native(backend) == "plotnine":
        return _scores_plotnine(pca, comps, distances, level, style, title)
    st = resolve_style(style, **kw)
    scr = pca_scores(pca)
    i, j = comps
    if scr.shape[1] <= max(i, j):
        raise ValueError(
            f"scores() needs components {comps} but the fit has only "
            f"{scr.shape[1]} component(s). Use prcomp_rob (full rank) or fit "
            "pca_rob_s with a larger ncomp."
        )
    x, y = scr[:, i], scr[:, j]

    _, ax, _ = get_ax(ax, st)
    if distances is not None:
        d = np.asarray(distances, float).ravel()
        cut = float(np.sqrt(chi2_quantile(level, scr.shape[1])))
        flagged = d > cut
        ax.scatter(x[~flagged], y[~flagged], color=st.inlier_color, s=st.point_size,
                   alpha=st.alpha, edgecolors="none", zorder=2)
        if flagged.any():
            ax.scatter(x[flagged], y[flagged], color=st.outlier_color,
                       s=st.point_size * 1.25, alpha=st.alpha, edgecolors="black",
                       linewidths=0.5, zorder=3)
        flag_idx = set(int(t) for t in np.nonzero(flagged)[0])
    else:
        ax.scatter(x, y, color=st.inlier_color, s=st.point_size, alpha=st.alpha,
                   edgecolors="none", zorder=2)
        flag_idx = set()

    ax.axhline(0, color=st.ref_line_color, lw=0.7, ls="--", zorder=1)
    ax.axvline(0, color=st.ref_line_color, lw=0.7, ls="--", zorder=1)
    ax.set_xlabel(f"PC{i + 1}")
    ax.set_ylabel(f"PC{j + 1}")

    if highlight is not None:
        flag_idx |= {int(t) for t in highlight}
    _label(ax, x, y, sorted(flag_idx), labels, st)
    return finish(ax, st, title=title or "PCA scores", save=save, show=show)


# ---------------------------------------------------------------------------
# loadings heatmap
# ---------------------------------------------------------------------------

def loadings(
    pca,
    *,
    ncomp: int | None = None,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Heatmap of the loadings / principal directions (variables × components)."""
    if _native(backend) == "plotnine":
        return _loadings_plotnine(pca, ncomp, style, title)
    st = resolve_style(style, **kw)
    load = pca_loadings(pca)
    if ncomp is not None:
        load = load[:, :ncomp]
    p, q = load.shape
    var_names = _col_names(pca, p)

    _, ax, _ = get_ax(ax, st)
    vmax = float(np.abs(load).max()) or 1.0
    im = ax.imshow(load, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(q))
    ax.set_xticklabels([f"PC{i + 1}" for i in range(q)])
    ax.set_yticks(range(p))
    ax.set_yticklabels(var_names)
    cb = ax.figure.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("Loading", fontsize=st.base_fontsize * st.font_scale * 0.9)
    ax.set_xlabel("Component")
    ax.set_ylabel("Variable")
    # turn off grid for heatmaps
    ax.grid(False)
    out = finish(ax, st, title=title or "PCA loadings", save=save, show=show)
    ax.grid(False)
    return out


# ---------------------------------------------------------------------------
# biplot
# ---------------------------------------------------------------------------

def biplot(
    pca,
    *,
    comps: tuple[int, int] = (0, 1),
    arrow_scale: float | None = None,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    labels=None,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Biplot: PC scores overlaid with loading arrows for each variable."""
    if _native(backend) == "plotnine":
        return _biplot_plotnine(pca, comps, arrow_scale, style, labels, title)
    st = resolve_style(style, **kw)
    scr = pca_scores(pca)
    load = pca_loadings(pca)
    i, j = comps
    if scr.shape[1] <= max(i, j) or load.shape[1] <= max(i, j):
        raise ValueError(
            f"biplot() needs components {comps} but the fit has only "
            f"{scr.shape[1]} component(s). Use prcomp_rob or a larger ncomp."
        )
    x, y = scr[:, i], scr[:, j]
    p = load.shape[0]
    var_names = _col_names(pca, p)

    _, ax, _ = get_ax(ax, st)
    ax.scatter(x, y, color=st.inlier_color, s=st.point_size * 0.7, alpha=0.6,
               edgecolors="none", zorder=2)

    span = max(np.abs(x).max(), np.abs(y).max())
    lmax = max(np.abs(load[:, i]).max(), np.abs(load[:, j]).max()) or 1.0
    scale = arrow_scale if arrow_scale is not None else 0.9 * span / lmax
    for v in range(p):
        dx, dy = load[v, i] * scale, load[v, j] * scale
        ax.annotate("", xy=(dx, dy), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color=st.outlier_color, lw=1.2),
                    zorder=3)
        ax.text(dx * 1.08, dy * 1.08,
                str(labels[v]) if labels is not None and v < len(labels) else var_names[v],
                color=st.outlier_color, fontsize=st.base_fontsize * st.font_scale * 0.8,
                ha="center", va="center", zorder=4)
    ax.axhline(0, color=st.ref_line_color, lw=0.7, ls="--", zorder=1)
    ax.axvline(0, color=st.ref_line_color, lw=0.7, ls="--", zorder=1)
    ax.set_xlabel(f"PC{i + 1}")
    ax.set_ylabel(f"PC{j + 1}")
    return finish(ax, st, title=title or "Robust PCA biplot", save=save, show=show)


# ---------------------------------------------------------------------------
# covariance / correlation heatmap (with optional robust − classical delta)
# ---------------------------------------------------------------------------

def cov_heatmap(
    cov,
    other=None,
    *,
    backend: str = "auto",
    ax: Any = None,
    style: PlotStyle | None = None,
    annot: bool = True,
    title: str | None = None,
    save=None,
    show: bool = False,
    **kw,
):
    """Correlation heatmap from a covariance result.

    If ``other`` is given, plot the *difference* ``corr(cov) − corr(other)`` —
    e.g. robust minus classical, showing how outliers distort the classical
    correlation structure (a new analytical view, not in the example notebooks).
    """
    if _native(backend) == "plotnine":
        return _cov_heatmap_plotnine(cov, other, annot, style, title)
    st = resolve_style(style, **kw)
    corr = corr_from_cov(cov.cov)
    if other is not None:
        corr = corr - corr_from_cov(other.cov)
        default_title = "Δ correlation (robust − classical)"
    else:
        default_title = "Robust correlation"
    p = corr.shape[0]
    names = _col_names(cov, p)

    _, ax, _ = get_ax(ax, st)
    vmax = float(np.abs(corr).max()) or 1.0
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(p))
    ax.set_xticklabels(names, rotation=90)
    ax.set_yticks(range(p))
    ax.set_yticklabels(names)
    cb = ax.figure.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("correlation", fontsize=st.base_fontsize * st.font_scale * 0.9)
    if annot and p <= 12:
        for r in range(p):
            for c in range(p):
                ax.text(c, r, f"{corr[r, c]:.2f}", ha="center", va="center",
                        fontsize=st.base_fontsize * st.font_scale * 0.7,
                        color="black" if abs(corr[r, c]) < 0.5 * vmax else "white")
    ax.grid(False)
    out = finish(ax, st, title=title or default_title, save=save, show=show)
    ax.grid(False)
    return out


# ---------------------------------------------------------------------------
# plotnine (secondary engine) renderers
# ---------------------------------------------------------------------------

def _tile_df(mat, row_names, col_names):
    import pandas as pd

    rows, cols, vals = [], [], []
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            rows.append(row_names[r])
            cols.append(col_names[c])
            vals.append(float(mat[r, c]))
    return pd.DataFrame({"row": rows, "col": cols, "value": vals})


def _distance_distance_plotnine(robust, classical, level, style, title):
    import pandas as pd
    from plotnine import (
        aes,
        geom_abline,
        geom_hline,
        geom_point,
        geom_vline,
        ggplot,
        labs,
        scale_color_manual,
        theme_bw,
    )

    st = resolve_style(style)
    rd = maha_distance(robust)
    cd = maha_distance(classical)
    p = np.asarray(robust.cov, float).shape[0]
    cut = float(np.sqrt(chi2_quantile(level, p)))
    df = pd.DataFrame({"classical": cd, "robust": rd, "outlier": rd > cut})
    return (
        ggplot(df, aes("classical", "robust", color="outlier"))
        + geom_abline(slope=1, intercept=0, linetype="dashed", color=st.ref_line_color)
        + geom_hline(yintercept=cut, linetype="dotted", color=st.cutoff_color)
        + geom_vline(xintercept=cut, linetype="dotted", color=st.cutoff_color)
        + geom_point(alpha=st.alpha)
        + scale_color_manual(values={False: st.inlier_color, True: st.outlier_color})
        + labs(x="Classical Mahalanobis distance", y="Robust Mahalanobis distance",
               title=title or "Distance–distance plot")
        + theme_bw()
    )


def _mahalanobis_panel_plotnine(cov, level, style, title):
    import pandas as pd
    from plotnine import (
        aes,
        geom_hline,
        geom_point,
        geom_segment,
        ggplot,
        labs,
        scale_color_manual,
        theme_bw,
    )

    st = resolve_style(style)
    d = maha_distance(cov)
    p = np.asarray(cov.cov, float).shape[0]
    cut = float(np.sqrt(chi2_quantile(level, p)))
    df = pd.DataFrame({"index": np.arange(d.size), "dist": d, "outlier": d > cut})
    return (
        ggplot(df, aes("index", "dist", color="outlier"))
        + geom_segment(aes(x="index", xend="index", y=0, yend="dist"),
                       color=st.ref_line_color, alpha=0.35)
        + geom_hline(yintercept=cut, linetype="dotted", color=st.cutoff_color)
        + geom_point(alpha=st.alpha)
        + scale_color_manual(values={False: st.inlier_color, True: st.outlier_color})
        + labs(x="Observation index", y="Robust Mahalanobis distance",
               title=title or "Robust Mahalanobis distances")
        + theme_bw()
    )


def _scree_plotnine(pca, cumulative, style, title):
    import pandas as pd
    from plotnine import aes, geom_col, geom_line, geom_point, ggplot, labs, theme_bw

    st = resolve_style(style)
    prop = pca_proportions(pca)
    comp = np.arange(1, prop.size + 1)
    df = pd.DataFrame({"component": comp, "proportion": prop,
                       "cumulative": np.cumsum(prop)})
    g = (
        ggplot(df, aes("component", "proportion"))
        + geom_col(fill=st.inlier_color, alpha=st.alpha)
        + labs(x="Principal component", y="Proportion of variance",
               title=title or "Scree plot")
        + theme_bw()
    )
    if cumulative:
        g = (g + geom_line(aes("component", "cumulative"), color=st.outlier_color)
             + geom_point(aes("component", "cumulative"), color=st.outlier_color))
    return g


def _scores_plotnine(pca, comps, distances, level, style, title):
    import pandas as pd
    from plotnine import (
        aes,
        geom_hline,
        geom_point,
        geom_vline,
        ggplot,
        labs,
        scale_color_manual,
        theme_bw,
    )

    st = resolve_style(style)
    scr = pca_scores(pca)
    i, j = comps
    if scr.shape[1] <= max(i, j):
        raise ValueError(
            f"scores() needs components {comps} but the fit has only "
            f"{scr.shape[1]} component(s). Use prcomp_rob or a larger ncomp."
        )
    df = pd.DataFrame({"x": scr[:, i], "y": scr[:, j]})
    color = None
    if distances is not None:
        d = np.asarray(distances, float).ravel()
        cut = float(np.sqrt(chi2_quantile(level, scr.shape[1])))
        df["outlier"] = d > cut
        color = "outlier"
    mapping = aes("x", "y", color=color) if color else aes("x", "y")
    g = (
        ggplot(df, mapping)
        + geom_hline(yintercept=0, linetype="dashed", color=st.ref_line_color)
        + geom_vline(xintercept=0, linetype="dashed", color=st.ref_line_color)
        + geom_point(alpha=st.alpha)
        + labs(x=f"PC{i + 1}", y=f"PC{j + 1}", title=title or "PCA scores")
        + theme_bw()
    )
    if color:
        g = g + scale_color_manual(values={False: st.inlier_color,
                                           True: st.outlier_color})
    return g


def _loadings_plotnine(pca, ncomp, style, title):
    from plotnine import (
        aes,
        element_blank,
        geom_tile,
        ggplot,
        labs,
        scale_fill_gradient2,
        theme,
        theme_bw,
    )

    load = pca_loadings(pca)
    if ncomp is not None:
        load = load[:, :ncomp]
    p, q = load.shape
    var_names = _col_names(pca, p)
    comp_names = [f"PC{i + 1}" for i in range(q)]
    df = _tile_df(load, var_names, comp_names)
    df["row"] = df["row"].astype("category").cat.reorder_categories(var_names[::-1])
    df["col"] = df["col"].astype("category").cat.reorder_categories(comp_names)
    return (
        ggplot(df, aes("col", "row", fill="value"))
        + geom_tile()
        + scale_fill_gradient2(low="#2166AC", mid="white", high="#B2182B",
                               midpoint=0, name="Loading")
        + labs(x="Component", y="Variable", title=title or "PCA loadings")
        + theme_bw()
        + theme(panel_grid=element_blank())
    )


def _biplot_plotnine(pca, comps, arrow_scale, style, labels, title):
    import pandas as pd
    from plotnine import (
        aes,
        arrow,
        geom_point,
        geom_segment,
        geom_text,
        ggplot,
        labs,
        theme_bw,
    )

    st = resolve_style(style)
    scr = pca_scores(pca)
    load = pca_loadings(pca)
    i, j = comps
    if scr.shape[1] <= max(i, j) or load.shape[1] <= max(i, j):
        raise ValueError(
            f"biplot() needs components {comps} but the fit has only "
            f"{scr.shape[1]} component(s). Use prcomp_rob or a larger ncomp."
        )
    x, y = scr[:, i], scr[:, j]
    p = load.shape[0]
    var_names = _col_names(pca, p)
    span = max(np.abs(x).max(), np.abs(y).max())
    lmax = max(np.abs(load[:, i]).max(), np.abs(load[:, j]).max()) or 1.0
    scale = arrow_scale if arrow_scale is not None else 0.9 * span / lmax
    pts = pd.DataFrame({"x": x, "y": y})
    arr = pd.DataFrame({
        "x": 0.0, "y": 0.0,
        "xend": load[:, i] * scale, "yend": load[:, j] * scale,
        "label": [str(labels[v]) if labels is not None and v < len(labels)
                  else var_names[v] for v in range(p)],
    })
    return (
        ggplot()
        + geom_point(pts, aes("x", "y"), color=st.inlier_color, alpha=0.6)
        + geom_segment(arr, aes(x="x", y="y", xend="xend", yend="yend"),
                       color=st.outlier_color, arrow=arrow(length=0.1))
        + geom_text(arr, aes("xend", "yend", label="label"),
                    color=st.outlier_color, size=8, nudge_y=0.02)
        + labs(x=f"PC{i + 1}", y=f"PC{j + 1}", title=title or "Robust PCA biplot")
        + theme_bw()
    )


def _cov_heatmap_plotnine(cov, other, annot, style, title):
    from plotnine import (
        aes,
        element_blank,
        geom_text,
        geom_tile,
        ggplot,
        labs,
        scale_fill_gradient2,
        theme,
        theme_bw,
    )

    corr = corr_from_cov(cov.cov)
    default_title = "Robust correlation"
    if other is not None:
        corr = corr - corr_from_cov(other.cov)
        default_title = "Δ correlation (robust − classical)"
    p = corr.shape[0]
    names = _col_names(cov, p)
    df = _tile_df(corr, names, names)
    df["row"] = df["row"].astype("category").cat.reorder_categories(names[::-1])
    df["col"] = df["col"].astype("category").cat.reorder_categories(names)
    g = (
        ggplot(df, aes("col", "row", fill="value"))
        + geom_tile()
        + scale_fill_gradient2(low="#2166AC", mid="white", high="#B2182B",
                               midpoint=0, name="correlation")
        + labs(x="", y="", title=title or default_title)
        + theme_bw()
        + theme(panel_grid=element_blank())
    )
    if annot and p <= 12:
        df2 = df.copy()
        df2["txt"] = df2["value"].map(lambda v: f"{v:.2f}")
        g = g + geom_text(df2, aes("col", "row", label="txt"), size=7)
    return g
