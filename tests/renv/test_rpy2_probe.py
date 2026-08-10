"""Compatibility shims for rpy2's Windows start-up probe.

Importing ``rpy2.rinterface_lib.openrlib`` on Windows runs
``R CMD config --ldflags`` to locate R's libraries, and
``rpy2/situation/__init__.py`` indexes the first line of the output without
checking that there is one. ``R CMD`` is a shell script, so against an R with no
shell - precisely the conda-forge R that ``robstattm-py setup`` installs - the
command produces no output and rpy2 raises ``IndexError``. rpy2 only guards that
call with ``except CalledProcessError``, so the error escapes and
``import rpy2.robjects`` fails.

The symptom is nastily conditional: with no other R on ``PATH`` the command
exits non-zero, rpy2 catches ``CalledProcessError``, and everything works. It
breaks only for users who *also* have a normal R installed - which is most of
the people likely to try the provisioned R in the first place.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from robstattm_py import _r

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="the probe only runs on Windows"
)


@pytest.fixture
def fake_situation(monkeypatch):
    """Provide a stand-in ``rpy2.situation`` with a controllable probe."""
    situation = pytest.importorskip("rpy2.situation")
    # Make the shim believe rpy2 has not been imported yet, so it will patch.
    monkeypatch.delitem(sys.modules, "rpy2.rinterface_lib.openrlib", raising=False)
    original = situation.get_r_flags
    yield situation
    monkeypatch.setattr(situation, "get_r_flags", original, raising=False)


def test_index_error_becomes_the_error_rpy2_handles(fake_situation, monkeypatch):
    """The whole point: rpy2's own fallback must get a chance to run."""

    def _raises_index_error(r_home, flags):
        raise IndexError("list index out of range")

    monkeypatch.setattr(fake_situation, "get_r_flags", _raises_index_error)
    _r._harden_rpy2_windows_probe()

    with pytest.raises(subprocess.CalledProcessError):
        fake_situation.get_r_flags("C:/R", "--ldflags")


def test_successful_probes_are_passed_through_untouched(fake_situation, monkeypatch):
    sentinel = object()
    monkeypatch.setattr(fake_situation, "get_r_flags", lambda r_home, flags: sentinel)
    _r._harden_rpy2_windows_probe()

    assert fake_situation.get_r_flags("C:/R", "--ldflags") is sentinel


def test_other_errors_are_not_swallowed(fake_situation, monkeypatch):
    """Only the known IndexError is translated; everything else propagates."""

    def _raises_runtime_error(r_home, flags):
        raise RuntimeError("something genuinely wrong")

    monkeypatch.setattr(fake_situation, "get_r_flags", _raises_runtime_error)
    _r._harden_rpy2_windows_probe()

    with pytest.raises(RuntimeError, match="genuinely wrong"):
        fake_situation.get_r_flags("C:/R", "--ldflags")


def test_patching_is_idempotent(fake_situation, monkeypatch):
    """Repeated calls must not stack wrappers."""

    def _raises_index_error(r_home, flags):
        raise IndexError("boom")

    monkeypatch.setattr(fake_situation, "get_r_flags", _raises_index_error)
    _r._harden_rpy2_windows_probe()
    first = fake_situation.get_r_flags
    _r._harden_rpy2_windows_probe()

    assert fake_situation.get_r_flags is first


# ---------------------------------------------------------------------------
# stderr filtering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "'sh' is not recognized as an internal or external command,",
        "operable program or batch file.",
        "C:/rtm/envs/r/lib/R/bin/config.sh: line 196: make: command not found",
        "R was not built as a library",
    ],
)
def test_known_probe_noise_is_recognised(line):
    assert any(marker in line for marker in _r._PROBE_NOISE)


@pytest.mark.parametrize(
    "line",
    [
        "Error in library(RobStatTM) : there is no package called 'RobStatTM'",
        "Segmentation fault",
        "LoadLibrary failure: The specified module could not be found.",
        "Error: cannot allocate vector of size 2.0 Gb",
    ],
)
def test_real_errors_are_never_filtered(line):
    """The filter must stay narrow: a swallowed error is worse than noise."""
    assert not any(marker in line for marker in _r._PROBE_NOISE)
