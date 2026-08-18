"""``check_setup()``, the first thing a new user runs.

It had no test coverage at all, which is how two defects survived in it:
``rpy2.__version__`` was removed in rpy2 3.6 so the version always printed as
"unknown", and the report mixed em dashes into output that is routinely read on
a Windows cp1252 console, where they render as replacement characters.
"""
from __future__ import annotations

import io
import sys
from importlib import import_module

import pytest

from ..conftest import needs_r

# `from robstattm_py.utils import check_setup` yields the *function*: the
# package re-exports it, shadowing the submodule of the same name. Import the
# module explicitly so the private helpers are reachable too.
mod = import_module("robstattm_py.utils.check_setup")


@needs_r
def test_returns_true_when_core_packages_are_present(capsys):
    assert mod.check_setup(verbose=False) is True
    assert capsys.readouterr().out == "", "verbose=False must print nothing"


@needs_r
def test_report_contains_the_essential_facts(capsys):
    mod.check_setup()
    out = capsys.readouterr().out

    assert "RobStatTM-Py setup check" in out
    assert "Python:" in out
    assert "rpy2:" in out
    assert "R:" in out
    for package in mod.CORE_R_PACKAGES:
        assert package in out
    assert "Result:" in out


@needs_r
def test_reports_a_real_rpy2_version_not_unknown(capsys):
    """Regression: rpy2 3.6 dropped ``rpy2.__version__``.

    The old attribute lookup silently degraded to "unknown" on every current
    install, which is worse than useless in a diagnostic, it makes a working
    setup look broken.
    """
    mod.check_setup()
    line = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("rpy2:"))

    assert "unknown" not in line
    assert "(missing)" not in line
    assert any(ch.isdigit() for ch in line), f"no version number in {line!r}"


@needs_r
def test_package_table_columns_line_up(capsys):
    """`robustvarComp` is 13 characters and used to overflow a 12-wide column."""
    mod.check_setup()
    all_packages = mod.CORE_R_PACKAGES + mod.STRETCH_R_PACKAGES + mod.OPTIONAL_R_PACKAGES

    # Match only genuine table rows: two-space indent followed immediately by a
    # package name. Substring matching would also pull in the install-hint lines
    # that appear when a package is missing (as `robcbi` is on CI), which are
    # not part of the table and are not expected to align.
    rows = [
        (name, line)
        for line in capsys.readouterr().out.splitlines()
        for name in all_packages
        if line.startswith(f"  {name} ")
    ]
    assert rows, "no package rows found"

    # Where the second column begins: past the name, past its padding.
    def second_column_start(name: str, line: str) -> int:
        after_name = 2 + len(name)
        return after_name + (len(line[after_name:]) - len(line[after_name:].lstrip()))

    starts = {second_column_start(name, line) for name, line in rows}
    assert len(starts) == 1, "version column is ragged:\n" + "\n".join(
        line for _, line in rows
    )


@needs_r
def test_report_survives_a_cp1252_console(monkeypatch):
    """The whole report must encode on a legacy Windows console.

    ``_stdout_supports_unicode`` downgrades the status glyphs, but any stray
    em dash elsewhere in the report would still raise (or print as garbage)
    for a Windows user. Encoding the entire output is the only check that
    covers the lines nobody remembered to guard.
    """
    buffer = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict", newline="")
    monkeypatch.setattr(sys, "stdout", buffer)
    try:
        mod.check_setup()
        buffer.flush()
    finally:
        monkeypatch.undo()

    # Reaching here without a UnicodeEncodeError is the assertion.
    assert buffer.buffer.getvalue()


def test_package_lists_are_shared_with_doctor():
    """One source of truth, so the two diagnostics cannot drift apart."""
    from robstattm_py._renv import report

    assert mod.CORE_R_PACKAGES is report.CORE_R_PACKAGES
    assert mod.STRETCH_R_PACKAGES is report.STRETCH_R_PACKAGES
    assert mod.OPTIONAL_R_PACKAGES is report.OPTIONAL_R_PACKAGES


@pytest.mark.parametrize("encoding", ["cp1252", "ascii", "utf-8"])
def test_unicode_probe_matches_the_encoding(monkeypatch, encoding):
    buffer = io.TextIOWrapper(io.BytesIO(), encoding=encoding, newline="")
    monkeypatch.setattr(sys, "stdout", buffer)
    try:
        supported = mod._stdout_supports_unicode()
    finally:
        monkeypatch.undo()
    assert supported is (encoding == "utf-8")
