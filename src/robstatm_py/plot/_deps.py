"""Lazy import guards for the optional plotting dependencies.

matplotlib / plotnine live behind the ``[plots]`` extra (see ``pyproject.toml``
and decisions D-008/D-023). Nothing in :mod:`robstatm_py.plot` imports them at
module load — only when a native/plotnine figure is actually drawn — so
``import robstatm_py`` stays cheap and the package installs without them.
"""
from __future__ import annotations

from typing import Any

_PLOTS_EXTRA_HINT = (
    'Install the plotting dependencies with:  pip install "robstatm-py[plots]"'
)


def have_matplotlib() -> bool:
    """True if matplotlib can be imported (no error raised)."""
    try:
        import matplotlib  # noqa: F401

        return True
    except ImportError:
        return False


def have_plotnine() -> bool:
    """True if plotnine can be imported (no error raised)."""
    try:
        import plotnine  # noqa: F401

        return True
    except ImportError:
        return False


def require_matplotlib() -> Any:
    """Import and return the ``matplotlib`` module or raise a helpful error."""
    try:
        import matplotlib  # noqa: F401
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "matplotlib is required for native plotting. " + _PLOTS_EXTRA_HINT
        ) from e
    return matplotlib


def require_pyplot() -> Any:
    """Import and return ``matplotlib.pyplot`` or raise a helpful error."""
    require_matplotlib()
    import matplotlib.pyplot as plt

    return plt


def require_plotnine() -> Any:
    """Import and return the ``plotnine`` module or raise a helpful error."""
    try:
        import plotnine
    except ImportError as e:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "plotnine is required for backend='plotnine'. " + _PLOTS_EXTRA_HINT
        ) from e
    return plotnine
