"""Completeness of the compat-R alias layer, the help() lookup, and datasets.

These would have caught the recently-fixed gaps: missing names in
``compat_r.__all__`` and ``help()`` failing on external R-style names.
"""
from __future__ import annotations

import importlib

import pytest

import robstatm_py as rpm
from robstatm_py import compat_r


class TestCompatCompleteness:
    def test_every_all_name_is_resolvable(self):
        for name in compat_r.__all__:
            assert hasattr(compat_r, name), f"{name} in __all__ but not defined"
            assert getattr(compat_r, name) is not None

    def test_import_star_exposes_all(self):
        """`from robstatm_py.compat_r import *` must bring every __all__ name —
        a name defined but absent from __all__ would silently not be exported."""
        ns: dict = {}
        exec("from robstatm_py.compat_r import *", ns)
        for name in compat_r.__all__:
            assert name in ns, f"{name} not exported by `import *`"

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            ("drop1", "drop1_lmrobdet"),
            ("drop1_lmrobdetMM", "drop1_lmrobdet"),
            ("pense", "pense"),
            ("pense_cv", "pense_cv"),
            ("GSE", "gse"),
            ("TSGS", "tsgs"),
            ("refine_sm", "refine_sm"),
            ("INVTR2", "invtr2"),
        ],
    )
    def test_alias_points_at_canonical(self, alias, canonical):
        assert getattr(compat_r, alias) is getattr(rpm, canonical)

    def test_callables_are_callable(self):
        for name in compat_r.__all__:
            obj = getattr(compat_r, name)
            # `data` is a function; psi family identifiers + wrappers are callable
            assert callable(obj), f"{name} should be callable"


class TestHelpCompleteness:
    def test_help_runs_for_every_mapped_name(self, capsys):
        """`help(name)` must print for every R→Python name in the map, including
        the external (pense/GSE/TSGS) entries — none may raise."""
        for r_name in rpm.list_names():
            rpm.help(r_name)
            out = capsys.readouterr().out
            assert out.strip(), f"help({r_name!r}) printed nothing"

    @pytest.mark.parametrize("name", ["GSE", "TSGS", "pense", "gse", "tsgs"])
    def test_help_external_names(self, name, capsys):
        rpm.help(name)
        assert capsys.readouterr().out.strip()

    def test_help_resolves_psi_submodule(self, capsys):
        rpm.help("bisquare")
        assert "bisquare" in capsys.readouterr().out


class TestDatasetsCatalog:
    def test_available_lists_twenty(self):
        names = rpm.datasets.available()
        assert len(names) == 20
        assert "mineral" in names and "wine" in names

    @pytest.mark.parametrize("name", ["mineral", "wine", "bus", "resex"])
    def test_info_returns_string(self, name):
        s = rpm.datasets.info(name)
        assert isinstance(s, str) and name in s

    def test_info_unknown_raises(self):
        with pytest.raises(KeyError):
            rpm.datasets.info("definitely_not_a_dataset")

    def test_every_loader_is_callable(self):
        for name in rpm.datasets.available():
            assert callable(getattr(rpm.datasets, name))
