"""Tests for the PlotStyle theme system."""
from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")

from robstatm_py.plot import PlotStyle, get_theme, set_theme, theme_names  # noqa: E402


def test_default_theme_is_publication():
    set_theme("publication")
    st = get_theme()
    assert isinstance(st, PlotStyle)
    assert st.color_by_weight is True
    assert st.spine_top is False


def test_named_themes_exist_and_differ():
    names = theme_names()
    for n in ("publication", "book", "minimal", "dark"):
        assert n in names
    book = set_theme("book")
    assert book.color_by_weight is False
    assert book.grid is False
    dark = set_theme("dark")
    assert dark.face_color is not None


def test_unknown_theme_raises():
    with pytest.raises(ValueError, match="unknown theme"):
        set_theme("does-not-exist")


def test_set_theme_with_overrides():
    st = set_theme("publication", point_size=99, weight_cmap="magma")
    assert st.point_size == 99
    assert st.weight_cmap == "magma"


def test_set_theme_accepts_plotstyle_instance():
    custom = PlotStyle(point_size=12, grid=False)
    st = set_theme(custom)
    assert st.point_size == 12
    assert st.grid is False


def test_set_theme_bad_type_raises():
    with pytest.raises(TypeError):
        set_theme(123)


def test_merged_ignores_none_and_unknown_keys():
    st = PlotStyle()
    merged = st.merged(point_size=None, not_a_field=5, alpha=0.5)
    assert merged.point_size == st.point_size  # None ignored
    assert merged.alpha == 0.5
    assert not hasattr(merged, "not_a_field")


def test_style_is_frozen():
    import dataclasses

    st = PlotStyle()
    with pytest.raises(dataclasses.FrozenInstanceError):
        st.point_size = 1  # type: ignore[misc]
