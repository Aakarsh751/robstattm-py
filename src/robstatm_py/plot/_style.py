"""Theme / style system for the native plotting suite.

A single frozen :class:`PlotStyle` carries every visual knob. A global registry
holds named themes (``"publication"`` default, ``"book"``, ``"minimal"``,
``"dark"``) and the *current* theme, settable with :func:`set_theme`.

Resolution order per plot call (highest priority first):
explicit ``**overrides`` kwargs  >  ``style=`` argument  >  global theme  >
built-in ``"publication"``.

Nothing here imports matplotlib; :func:`apply_axes_style` operates on an Axes
the caller already created (so it stays composable and import-light).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from typing import Any

# Okabe–Ito colourblind-safe categorical palette.
OKABE_ITO: tuple[str, ...] = (
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # green
    "#CC79A7",  # purple
    "#E69F00",  # orange
    "#56B4E9",  # sky
    "#F0E442",  # yellow
    "#000000",  # black
)


@dataclass(frozen=True)
class PlotStyle:
    """Immutable bundle of styling defaults for native (matplotlib) plots.

    Override individual fields by passing them to :func:`set_theme` or to any
    plot function as keyword arguments. Construct one directly for a fully
    custom look and pass it as ``style=``.

    Examples
    --------
    >>> from robstatm_py.plot import PlotStyle
    >>> s = PlotStyle(weight_cmap="magma", point_size=50, grid=False)
    >>> s.weight_cmap
    'magma'
    >>> s.merged(point_size=20).point_size
    20.0
    """

    # categorical / point colours
    palette: tuple[str, ...] = OKABE_ITO
    weight_cmap: str = "viridis"
    inlier_color: str = "#0072B2"
    outlier_color: str = "#D55E00"
    highlight_color: str = "#CC79A7"
    # line colours
    fit_color: str = "#D55E00"
    ols_color: str = "#888888"
    ref_line_color: str = "#666666"
    cutoff_color: str = "#D55E00"
    # markers
    point_size: float = 36.0
    alpha: float = 0.85
    # figure
    figsize: tuple[float, float] = (6.4, 4.8)
    dpi: int = 110
    # axis chrome
    spine_top: bool = False
    spine_right: bool = False
    grid: bool = True
    grid_alpha: float = 0.30
    # typography
    base_fontsize: float = 11.0
    font_scale: float = 1.0
    # dark / custom backgrounds (None = matplotlib default)
    face_color: str | None = None
    text_color: str | None = None
    # outlier flagging / annotation
    color_by_weight: bool = True
    annotate_outliers: bool = True
    outlier_weight_thresh: float = 0.50
    outlier_resid_thresh: float = 2.50

    def merged(self, **overrides: Any) -> PlotStyle:
        """Return a copy with the given (non-``None``) overrides applied."""
        names = {f.name for f in fields(self)}
        clean = {k: v for k, v in overrides.items() if v is not None and k in names}
        return replace(self, **clean) if clean else self


# ---------------------------------------------------------------------------
# Named themes
# ---------------------------------------------------------------------------

def _publication() -> PlotStyle:
    return PlotStyle()


def _book() -> PlotStyle:
    """Mimic the base-R look of the Maronna et al. textbook figures."""
    return PlotStyle(
        palette=("#000000", "#D55E00", "#0072B2"),
        color_by_weight=False,
        grid=False,
        spine_top=True,
        spine_right=True,
        inlier_color="#000000",
        outlier_color="#000000",
        fit_color="#000000",
        ref_line_color="#000000",
    )


def _minimal() -> PlotStyle:
    return PlotStyle(grid=False, color_by_weight=False)


def _dark() -> PlotStyle:
    # On a dark background a continuous weight colormap pushes low-weight
    # (outlier) points toward black, where they vanish. So the dark theme
    # defaults to the explicit inlier/outlier split with two bright,
    # high-contrast colours; users can still opt back in with
    # ``color_by_weight=True`` and a light-low colormap (e.g. weight_cmap="cool").
    return PlotStyle(
        weight_cmap="cool",
        color_by_weight=False,
        face_color="#20232a",
        text_color="#e6e6e6",
        ref_line_color="#aaaaaa",
        cutoff_color="#ff8c5a",
        inlier_color="#56B4E9",
        outlier_color="#ff8c5a",
        grid_alpha=0.18,
    )


_THEMES: dict[str, Callable[[], PlotStyle]] = {
    "publication": _publication,
    "book": _book,
    "minimal": _minimal,
    "dark": _dark,
}

_current: PlotStyle = _publication()


def theme_names() -> tuple[str, ...]:
    """Return the registered named-theme keys."""
    return tuple(_THEMES)


def set_theme(theme: str | PlotStyle = "publication", **overrides: Any) -> PlotStyle:
    """Set the global default :class:`PlotStyle` for native plots.

    Parameters
    ----------
    theme : str or PlotStyle, default "publication"
        A named theme (``"publication"``, ``"book"``, ``"minimal"``, ``"dark"``)
        or an explicit :class:`PlotStyle`.
    **overrides
        Field overrides applied on top of ``theme``.

    Returns
    -------
    PlotStyle
        The newly active theme.
    """
    global _current
    if isinstance(theme, PlotStyle):
        base = theme
    elif isinstance(theme, str):
        if theme not in _THEMES:
            raise ValueError(
                f"unknown theme {theme!r}; choose from {sorted(_THEMES)} "
                "or pass a PlotStyle instance"
            )
        base = _THEMES[theme]()
    else:
        raise TypeError("theme must be a theme-name str or a PlotStyle instance")
    _current = base.merged(**overrides)
    return _current


def get_theme() -> PlotStyle:
    """Return the currently active global :class:`PlotStyle`."""
    return _current


def resolve_style(style: PlotStyle | None = None, **overrides: Any) -> PlotStyle:
    """Combine the active theme, an optional ``style=``, and per-call overrides."""
    base = style if isinstance(style, PlotStyle) else _current
    return base.merged(**overrides)


def apply_axes_style(ax: Any, style: PlotStyle) -> None:
    """Apply spine / grid / typography / background settings to one Axes."""
    if not style.spine_top:
        ax.spines["top"].set_visible(False)
    if not style.spine_right:
        ax.spines["right"].set_visible(False)
    if style.grid:
        ax.grid(True, alpha=style.grid_alpha, linewidth=0.6)
    else:
        ax.grid(False)

    fs = style.base_fontsize * style.font_scale
    ax.title.set_fontsize(fs * 1.15)
    ax.xaxis.label.set_fontsize(fs)
    ax.yaxis.label.set_fontsize(fs)
    ax.tick_params(labelsize=fs * 0.9)

    if style.face_color:
        ax.set_facecolor(style.face_color)
        ax.figure.set_facecolor(style.face_color)
    if style.text_color:
        for item in (ax.title, ax.xaxis.label, ax.yaxis.label):
            item.set_color(style.text_color)
        ax.tick_params(colors=style.text_color)
        for spine in ax.spines.values():
            spine.set_color(style.text_color)
