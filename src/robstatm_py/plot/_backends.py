"""Backend resolution + shared matplotlib helpers.

``backend="auto"`` (default) picks native matplotlib when available, else the R
graphics path (Path A), else raises a helpful error. See decision D-023.
"""
from __future__ import annotations

from typing import Any

from robstatm_py.plot._deps import (
    have_matplotlib,
    have_plotnine,
    require_matplotlib,
    require_plotnine,
    require_pyplot,
)
from robstatm_py.plot._style import PlotStyle, apply_axes_style

_VALID = {"auto", "native", "matplotlib", "plotnine", "r"}

# kwargs understood by the Path-A (R) helpers in ``robstatm_py.plotting``.
_R_KWARG_KEYS = ("dpi", "width", "height", "path", "bg")


def resolve_backend(
    backend: str,
    *,
    has_native: bool,
    has_r: bool,
    has_plotnine: bool = True,
) -> str:
    """Resolve a requested backend to a concrete one (``native``/``plotnine``/``r``).

    Raises
    ------
    ValueError
        If ``backend`` is unknown or unavailable for this plot.
    ImportError
        If ``auto`` finds no usable backend.
    """
    be = (backend or "auto").lower()
    if be not in _VALID:
        raise ValueError(
            f"unknown backend {backend!r}; choose from "
            "'auto', 'native', 'matplotlib', 'plotnine', 'r'"
        )

    if be == "auto":
        if has_native and have_matplotlib():
            return "native"
        if has_r:
            return "r"
        if has_plotnine and have_plotnine():
            return "plotnine"
        raise ImportError(
            "no plotting backend available — install matplotlib via "
            'pip install "robstatm-py[plots]", or use backend="r" with R set up.'
        )

    if be in ("native", "matplotlib"):
        if not has_native:
            raise ValueError("this plot has no native renderer; try backend='r'")
        require_matplotlib()
        return "native"

    if be == "plotnine":
        if not has_plotnine:
            raise ValueError("this plot has no plotnine renderer")
        require_plotnine()
        return "plotnine"

    # be == "r"
    if not has_r:
        raise ValueError(
            "this plot has no R (Path A) renderer; use backend='native'"
        )
    return "r"


def r_kwargs(kw: dict) -> dict:
    """Filter a kwargs dict down to the keys the Path-A R helpers accept."""
    return {k: kw[k] for k in _R_KWARG_KEYS if k in kw}


def get_ax(ax: Any, style: PlotStyle):
    """Return ``(figure, axes, created)`` — create a figure if ``ax`` is None."""
    plt = require_pyplot()
    if ax is not None:
        return ax.figure, ax, False
    fig, ax = plt.subplots(figsize=style.figsize, dpi=style.dpi)
    return fig, ax, True


def finish(ax: Any, style: PlotStyle, *, title=None, save=None, show=False):
    """Apply axes styling and handle ``title``/``save``/``show``; return ``ax``."""
    if title is not None:
        ax.set_title(title)
    apply_axes_style(ax, style)
    if save is not None:
        ax.figure.savefig(save, bbox_inches="tight", dpi=style.dpi)
    if show:
        require_pyplot().show()
    return ax


def finish_fig(fig: Any, style: PlotStyle, *, suptitle=None, save=None, show=False):
    """Finish a multi-panel Figure (used by ``diagnostics``)."""
    if suptitle is not None:
        fig.suptitle(suptitle, fontsize=style.base_fontsize * style.font_scale * 1.25)
    if style.face_color:
        fig.set_facecolor(style.face_color)
    fig.tight_layout()
    if save is not None:
        fig.savefig(save, bbox_inches="tight", dpi=style.dpi)
    if show:
        require_pyplot().show()
    return fig
