"""Tests for backend resolution."""
from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")

from robstatm_py.plot import _backends, _deps  # noqa: E402


def test_auto_resolves_native_when_matplotlib_present():
    assert _backends.resolve_backend("auto", has_native=True, has_r=True) == "native"


def test_auto_falls_back_to_r_without_matplotlib(monkeypatch):
    monkeypatch.setattr(_deps, "have_matplotlib", lambda: False)
    # _backends imported the name, so patch there too
    monkeypatch.setattr(_backends, "have_matplotlib", lambda: False)
    assert _backends.resolve_backend("auto", has_native=True, has_r=True) == "r"


def test_auto_raises_when_nothing_available(monkeypatch):
    monkeypatch.setattr(_backends, "have_matplotlib", lambda: False)
    monkeypatch.setattr(_backends, "have_plotnine", lambda: False)
    with pytest.raises(ImportError, match="no plotting backend"):
        _backends.resolve_backend("auto", has_native=True, has_r=False)


def test_unknown_backend_raises():
    with pytest.raises(ValueError, match="unknown backend"):
        _backends.resolve_backend("svg", has_native=True, has_r=True)


def test_r_backend_requires_r_renderer():
    with pytest.raises(ValueError, match="no R"):
        _backends.resolve_backend("r", has_native=True, has_r=False)


def test_native_backend_requires_native_renderer():
    with pytest.raises(ValueError, match="no native"):
        _backends.resolve_backend("native", has_native=False, has_r=True)


def test_plotnine_backend_raises_without_plotnine(monkeypatch):
    if _deps.have_plotnine():
        pytest.skip("plotnine installed; can't test the missing-dep path")
    with pytest.raises(ImportError, match="plotnine"):
        _backends.resolve_backend("plotnine", has_native=True, has_r=True)


def test_r_kwargs_whitelist():
    out = _backends.r_kwargs({"dpi": 200, "width": 5, "highlight": [1], "style": object()})
    assert out == {"dpi": 200, "width": 5}
