"""The provisioned R must find its own DLLs before anything else's.

Reported from a real Windows machine: `robstattm-py setup` downloaded and linked
everything, then died at "[4/4] Verifying" with

    Mingw-w64 runtime failure: 32 bit pseudo relocation at ... out of range

Windows resolves a DLL by scanning PATH left to right and taking the first name
match. The provisioned R needs `R.dll`, `Rblas.dll` and a mingw runtime — names
that a CRAN R installation, Rtools, MSYS2 and Git's bundled mingw all also ship.
Loading a foreign copy into conda's R fails either as a missing module
(0xC0000135) or, when it loads but came from a different toolchain, as the
pseudo-relocation message above: a ±2 GB relocation asked to span more.

`run_in_env` had delegated the whole of PATH to `micromamba run`'s activation.
That works when activation is complete; when it is not, R fails on a DLL. It now
puts the environment's own directories in front itself.

Reproduced by induction and verified in `dev/_verify_dll_fix.py`: with a CRAN R
and Rtools ahead on PATH, a bare Rscript launch exits 0xC0000135, and the
shipped code loads all four R packages against the same PATH.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from robstattm_py._renv import provision
from robstattm_py._renv.probe import Probe


def _windows_prefix(tmp_path: Path) -> Path:
    """A directory tree shaped like a provisioned conda environment."""
    prefix = tmp_path / "envs" / "r"
    for parts in (
        ("Library", "mingw-w64", "bin"),
        ("Library", "usr", "bin"),
        ("Library", "bin"),
        ("Scripts",),
        ("bin",),
    ):
        prefix.joinpath(*parts).mkdir(parents=True, exist_ok=True)
    return prefix


#: Stand-in for "some other R already on PATH". Deliberately free of `:` and
#: `;` so it survives a split on either platform's `os.pathsep` — a real
#: `C:\...` string does not, which is how the first version of these tests
#: passed on Windows and failed everywhere else.
OTHER_R_BIN = "OTHER_R_INSTALLATION_BIN"


def _probe(**environ) -> Probe:
    return Probe(system="Windows", machine="AMD64", is_64bit=True, environ=environ)


class TestEnvPathPrefix:
    def test_lists_every_conda_dll_directory_that_exists(self, tmp_path):
        prefix = _windows_prefix(tmp_path)
        entries = provision.env_path_prefix(prefix, _probe()).split(os.pathsep)

        assert str(prefix) in entries
        for parts in (
            ("Library", "mingw-w64", "bin"),
            ("Library", "usr", "bin"),
            ("Library", "bin"),
            ("Scripts",),
            ("bin",),
        ):
            assert str(prefix.joinpath(*parts)) in entries, parts

    def test_mingw_runtime_comes_before_library_bin(self, tmp_path):
        """Ordering is not cosmetic — it decides which copy of a DLL wins."""
        prefix = _windows_prefix(tmp_path)
        entries = provision.env_path_prefix(prefix, _probe()).split(os.pathsep)
        assert entries.index(str(prefix / "Library" / "mingw-w64" / "bin")) < entries.index(
            str(prefix / "Library" / "bin")
        )

    def test_absent_directories_are_omitted(self, tmp_path):
        prefix = tmp_path / "envs" / "r"
        (prefix / "Library" / "bin").mkdir(parents=True)
        entries = provision.env_path_prefix(prefix, _probe()).split(os.pathsep)
        assert str(prefix / "Library" / "bin") in entries
        assert str(prefix / "Scripts") not in entries

    def test_posix_uses_lib_and_bin(self, tmp_path):
        prefix = tmp_path / "envs" / "r"
        (prefix / "lib").mkdir(parents=True)
        (prefix / "bin").mkdir(parents=True)
        probe = Probe(system="Linux", machine="x86_64", is_64bit=True, environ={})
        entries = provision.env_path_prefix(prefix, probe).split(os.pathsep)
        assert entries == [str(prefix / "lib"), str(prefix / "bin")]

    def test_empty_prefix_yields_empty_string(self, tmp_path):
        """Must not return a bare separator, which would put "" on PATH."""
        assert provision.env_path_prefix(tmp_path / "nope", _probe()) == ""


class TestStartupFailureAdvice:
    """A DLL conflict and a bad download need opposite advice."""

    WINDOWS = _probe()

    def test_mingw_pseudo_relocation_is_recognised(self):
        err = provision._startup_failure(
            "Mingw-w64 runtime failure:\n"
            "32 bit pseudo relocation at 00007FFDF2815D45 out of range",
            1,
            probe=self.WINDOWS,
        )
        assert isinstance(err, provision.RStartupError)

    def test_dll_not_found_returncode_is_recognised(self):
        err = provision._startup_failure("", 3221225781, probe=self.WINDOWS)
        assert isinstance(err, provision.RStartupError)

    def test_it_does_not_tell_you_to_force_rebuild(self):
        """--force redownloads the same correct bytes and fails identically."""
        err = provision._startup_failure("pseudo relocation", 1, probe=self.WINDOWS)
        text = str(err)
        assert "--force will NOT help" in text
        assert "rebuild from scratch" not in text

    def test_it_names_the_actual_causes(self):
        err = provision._startup_failure("pseudo relocation", 1, probe=self.WINDOWS)
        text = str(err).lower()
        for cause in ("path", "rtools", "cran r installation", "conda environments"):
            assert cause in text, cause
        assert "--use-system-r" in str(err)

    def test_an_ordinary_failure_keeps_the_ordinary_advice(self):
        err = provision._startup_failure("some other R problem", 1, probe=self.WINDOWS)
        assert not isinstance(err, provision.RStartupError)
        assert "rebuild from scratch" in str(err)

    def test_dll_wording_is_windows_only(self):
        """The mechanism is Windows DLL search order; do not claim it elsewhere."""
        linux = Probe(system="Linux", machine="x86_64", is_64bit=True, environ={})
        err = provision._startup_failure("pseudo relocation", 1, probe=linux)
        assert not isinstance(err, provision.RStartupError)


class TestRunInEnvPutsEnvFirst:
    def test_env_directories_precede_the_inherited_path(self, tmp_path, monkeypatch):
        prefix = _windows_prefix(tmp_path)
        captured: dict[str, object] = {}

        def fake_run(argv, **kwargs):
            captured["env"] = kwargs["env"]
            return __import__("subprocess").CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(provision.subprocess, "run", fake_run)

        # Two things this test previously got wrong, both of which made it pass
        # on Windows and fail on every Linux and macOS leg:
        #
        #  - the probe must be passed explicitly, or `run_in_env` falls back to
        #    `Probe.current()` and the test describes the machine running it
        #    rather than Windows;
        #  - the stand-in for the inherited PATH must not contain the *running*
        #    platform's `os.pathsep`. "C:\\Program Files\\..." contains a colon,
        #    so on POSIX the split shattered it and `.index()` raised.
        probe = _probe(PATH=OTHER_R_BIN)
        provision.run_in_env(
            tmp_path / "micromamba.exe", prefix, 'cat("hi")', probe=probe
        )

        path_entries = captured["env"]["PATH"].split(os.pathsep)
        assert path_entries[0] == str(prefix)
        assert path_entries.index(str(prefix / "Library" / "bin")) < path_entries.index(
            OTHER_R_BIN
        )

    def test_inherited_path_is_not_discarded(self, tmp_path, monkeypatch):
        """Scrubbing PATH entirely would break micromamba's own dependencies."""
        prefix = _windows_prefix(tmp_path)
        captured: dict[str, object] = {}

        def fake_run(argv, **kwargs):
            captured["env"] = kwargs["env"]
            return __import__("subprocess").CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(provision.subprocess, "run", fake_run)

        probe = _probe(PATH=OTHER_R_BIN)
        provision.run_in_env(
            tmp_path / "micromamba.exe", prefix, 'cat("hi")', probe=probe
        )
        assert OTHER_R_BIN in captured["env"]["PATH"].split(os.pathsep)

    def test_posix_prefix_is_used_on_posix(self, tmp_path, monkeypatch):
        """The same function on a POSIX probe must use lib/ and bin/, not Library/."""
        prefix = tmp_path / "envs" / "r"
        (prefix / "lib").mkdir(parents=True)
        (prefix / "bin").mkdir(parents=True)
        captured: dict[str, object] = {}

        def fake_run(argv, **kwargs):
            captured["env"] = kwargs["env"]
            return __import__("subprocess").CompletedProcess(argv, 0, "", "")

        monkeypatch.setattr(provision.subprocess, "run", fake_run)

        probe = Probe(
            system="Linux", machine="x86_64", is_64bit=True,
            environ={"PATH": "/usr/bin"},
        )
        provision.run_in_env(
            tmp_path / "micromamba", prefix, 'cat("hi")', probe=probe
        )

        entries = captured["env"]["PATH"].split(os.pathsep)
        assert entries[0] == str(prefix / "lib")
        assert "/usr/bin" in entries


@pytest.mark.parametrize("returncode", sorted(provision._DLL_TROUBLE_RETURNCODES))
def test_every_listed_returncode_maps_to_the_dll_error(returncode):
    err = provision._startup_failure("", returncode, probe=_probe())
    assert isinstance(err, provision.RStartupError)
