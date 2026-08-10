"""The discovery chain: precedence, fallback, and the audit trail.

The single most valuable test here is
:func:`test_full_precedence_ladder`, which populates *every* rung at once and
then removes them one at a time, asserting the exact winner at each step. A
chain like this rots silently — a reordered tuple or an early ``return`` is
invisible in review but changes which R users get.
"""
from __future__ import annotations

import pytest

from robstattm_py._renv.discovery import Candidate, discover
from robstattm_py._renv.errors import ArchMismatchError, InvalidRHomeError

from .conftest import make_conda_prefix, make_probe, make_r_home


def _linux_probe(tmp_path, **overrides):
    """A Linux probe with no rungs populated, ready to have some filled in."""
    defaults = dict(
        system="Linux",
        machine="x86_64",
        environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")},
        sys_prefix=tmp_path / "nonexistent-prefix",
    )
    defaults.update(overrides)
    return make_probe(**defaults)


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


def test_full_precedence_ladder(tmp_path, monkeypatch):
    """Populate every rung, then peel them off and assert the exact order."""
    rtm_home = tmp_path / "rtm"

    # Rung 0: explicit override.
    override = make_r_home(tmp_path, "override-R", system="Linux")
    # Rung 1: the environment we provisioned.
    provisioned_prefix = rtm_home / "envs" / "r"
    (provisioned_prefix / "conda-meta").mkdir(parents=True)
    make_r_home(provisioned_prefix / "lib", "R", system="Linux")
    # Rung 2: R_HOME.
    env_home = make_r_home(tmp_path, "env-R", system="Linux")
    # Rung 3: an active conda env.
    conda = make_conda_prefix(tmp_path, "conda-env", system="Linux")
    # Rung 5: R on PATH.
    path_r = make_r_home(tmp_path, "path-R", system="Linux")
    # Rung 10: a distro install.
    distro = make_r_home(tmp_path, "usr-lib-R", system="Linux")

    environ = {
        "ROBSTATTM_HOME": str(rtm_home),
        "ROBSTATTM_R_HOME": str(override),
        "R_HOME": str(env_home),
        "CONDA_PREFIX": str(conda),
    }
    exes = {"R": str(path_r / "bin" / "R")}
    (path_r / "bin").mkdir(exist_ok=True)
    (path_r / "bin" / "R").write_text("#!/bin/sh\n")

    # Stand in for /usr/lib/R without touching the real filesystem. This works
    # because _RUNGS names its generators and resolves them at call time.
    monkeypatch.setattr(
        "robstattm_py._renv.discovery._from_linux",
        lambda probe: [Candidate(distro, "linux")],
    )

    def run(env):
        probe = _linux_probe(tmp_path, environ=env, path_exes=exes)
        return discover(probe=probe)

    # 1. Explicit override wins over everything.
    assert run(environ).info.path == override

    # 2. Without it, the provisioned environment wins.
    env = {k: v for k, v in environ.items() if k != "ROBSTATTM_R_HOME"}
    result = run(env)
    assert result.info.source == "provisioned"

    # 3. Without that, R_HOME.
    (provisioned_prefix / "lib" / "R" / "etc").rmdir()
    (provisioned_prefix / "lib" / "R" / "library" / "base" / "DESCRIPTION").unlink()
    assert run(env).info.path == env_home

    # 4. Without R_HOME, the active conda prefix.
    env = {k: v for k, v in env.items() if k != "R_HOME"}
    assert run(env).info.path == conda / "lib" / "R"

    # 5. Without conda, whatever is on PATH.
    env = {k: v for k, v in env.items() if k != "CONDA_PREFIX"}
    assert run(env).info.path == path_r

    # 6. Finally the conventional distro location.
    probe = _linux_probe(tmp_path, environ=env, path_exes={})
    assert discover(probe=probe).info.path == distro


def test_explicit_override_never_falls_through(tmp_path):
    """A setting we cannot honour is an error, not a silent fallback.

    Falling back would leave the user staring at a working session that is
    quietly using a different R than the one they named.
    """
    good = make_r_home(tmp_path, "good-R", system="Linux")
    probe = _linux_probe(
        tmp_path,
        environ={
            "ROBSTATTM_R_HOME": str(tmp_path / "does-not-exist"),
            "R_HOME": str(good),
        },
    )
    with pytest.raises(InvalidRHomeError):
        discover(probe=probe)


def test_explicit_override_arch_mismatch_raises(tmp_path):
    home = make_r_home(tmp_path, "intel-R", system="Darwin", arch="x86_64")
    probe = make_probe(
        system="Darwin",
        machine="arm64",
        environ={"ROBSTATTM_R_HOME": str(home), "ROBSTATTM_HOME": str(tmp_path / "rtm")},
    )
    with pytest.raises(ArchMismatchError):
        discover(probe=probe)


# ---------------------------------------------------------------------------
# Robustness: a broken candidate must not end the search
# ---------------------------------------------------------------------------


def test_broken_r_on_path_does_not_hide_a_good_one(tmp_path):
    """The exact failure rpy2 has: a bogus R on PATH shadowing the registry.

    rpy2 only consults the Windows registry when its ``R RHOME`` subprocess
    *raises*. A stale wrapper script that exits 0 therefore hides every
    registered R. We record the bad candidate and keep going.
    """
    broken = tmp_path / "broken" / "bin"
    broken.mkdir(parents=True)
    (broken / "R.exe").write_text("not really R")

    good = make_r_home(tmp_path, "R-4.5.2", system="Windows")

    probe = make_probe(
        system="Windows",
        environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")},
        path_exes={"R": str(broken / "R.exe")},
        registry=[(good, "HKLM 4.5.2")],
    )
    result = discover(probe=probe)

    assert result.info is not None
    assert result.info.path == good
    assert result.info.source == "winreg"

    # And the rejection is explained, not silently dropped.
    rejected = [r for r in result.trace if not r.ok]
    assert any("does not look like an R installation" in (r.reason or "") for r in rejected)


def test_stale_r_home_is_skipped_not_fatal(tmp_path):
    """A leftover R_HOME in a shell profile is common; it must not be fatal."""
    good = make_r_home(tmp_path, "good-R", system="Linux")
    probe = _linux_probe(
        tmp_path,
        environ={
            "ROBSTATTM_HOME": str(tmp_path / "rtm"),
            "R_HOME": str(tmp_path / "removed-r"),
            "CONDA_PREFIX": str(make_conda_prefix(tmp_path, "conda-env", system="Linux")),
        },
    )
    result = discover(probe=probe)
    assert result.info is not None
    assert result.info.source == "conda:CONDA_PREFIX"
    assert any(r.candidate.source == "env:R_HOME" and not r.ok for r in result.trace)
    del good


def test_mismatched_arch_candidate_is_skipped_and_search_continues(tmp_path):
    """An unusable R is one rejected row, not the end of the search."""
    intel = make_r_home(tmp_path, "intel-R", system="Darwin", arch="x86_64")
    native = make_r_home(tmp_path, "arm-R", system="Darwin", arch="arm64")

    probe = make_probe(
        system="Darwin",
        machine="arm64",
        environ={"ROBSTATTM_HOME": str(tmp_path / "rtm"), "R_HOME": str(intel)},
        sys_prefix=tmp_path / "nope",
        path_exes={"R": str(native / "bin" / "R")},
    )
    (native / "bin").mkdir(exist_ok=True)
    (native / "bin" / "R").write_text("#!/bin/sh\n")

    result = discover(probe=probe)
    assert result.info is not None
    assert result.info.path == native
    assert any("x86_64" in (r.reason or "") for r in result.trace if not r.ok)


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def test_mode_system_ignores_the_provisioned_environment(tmp_path):
    rtm_home = tmp_path / "rtm"
    prefix = rtm_home / "envs" / "r"
    (prefix / "conda-meta").mkdir(parents=True)
    make_r_home(prefix / "lib", "R", system="Linux")
    system_r = make_r_home(tmp_path, "system-R", system="Linux")

    probe = _linux_probe(
        tmp_path,
        environ={"ROBSTATTM_HOME": str(rtm_home), "R_HOME": str(system_r)},
    )
    assert discover(probe=probe, mode="system").info.path == system_r
    assert discover(probe=probe, mode="auto").info.source == "provisioned"


def test_mode_provisioned_ignores_system_installs(tmp_path):
    system_r = make_r_home(tmp_path, "system-R", system="Linux")
    probe = _linux_probe(
        tmp_path,
        environ={"ROBSTATTM_HOME": str(tmp_path / "rtm"), "R_HOME": str(system_r)},
    )
    result = discover(probe=probe, mode="provisioned")
    assert result.info is None


def test_mode_is_read_from_the_environment(tmp_path):
    rtm_home = tmp_path / "rtm"
    prefix = rtm_home / "envs" / "r"
    (prefix / "conda-meta").mkdir(parents=True)
    make_r_home(prefix / "lib", "R", system="Linux")
    system_r = make_r_home(tmp_path, "system-R", system="Linux")

    probe = _linux_probe(
        tmp_path,
        environ={
            "ROBSTATTM_HOME": str(rtm_home),
            "R_HOME": str(system_r),
            "ROBSTATTM_R_MODE": "system",
        },
    )
    assert discover(probe=probe).info.path == system_r


def test_unknown_mode_falls_back_to_auto(tmp_path):
    system_r = make_r_home(tmp_path, "system-R", system="Linux")
    probe = _linux_probe(
        tmp_path,
        environ={"ROBSTATTM_HOME": str(tmp_path / "rtm"), "R_HOME": str(system_r)},
    )
    assert discover(probe=probe, mode="nonsense").info.path == system_r


# ---------------------------------------------------------------------------
# The trace
# ---------------------------------------------------------------------------


def test_nothing_found_yields_an_empty_result_not_an_exception(tmp_path):
    """`discover` reports; only `ensure_r_environment` raises."""
    probe = _linux_probe(tmp_path, environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")})
    result = discover(probe=probe)
    assert result.info is None
    assert not result.found


def test_raise_if_missing_includes_the_trace(tmp_path):
    from robstattm_py._renv.errors import NoRFoundError

    probe = _linux_probe(
        tmp_path,
        environ={"ROBSTATTM_HOME": str(tmp_path / "rtm"), "R_HOME": str(tmp_path / "gone")},
    )
    result = discover(probe=probe)
    with pytest.raises(NoRFoundError) as excinfo:
        result.raise_if_missing()

    message = str(excinfo.value)
    assert "env:R_HOME" in message
    assert "What to do:" in message


def test_trace_renders_one_entry_per_candidate(tmp_path):
    good = make_r_home(tmp_path, "good-R", system="Linux")
    probe = _linux_probe(
        tmp_path,
        environ={
            "ROBSTATTM_HOME": str(tmp_path / "rtm"),
            "R_HOME": str(tmp_path / "missing"),
            "CONDA_PREFIX": str(tmp_path / "also-missing"),
        },
        path_exes={"R": str(good / "bin" / "R")},
    )
    (good / "bin").mkdir(exist_ok=True)
    (good / "bin" / "R").write_text("#!/bin/sh\n")

    rendered = discover(probe=probe).render_trace()
    assert "env:R_HOME" in rendered
    assert "conda:CONDA_PREFIX" in rendered
    assert "[OK  ]" in rendered
    assert "[skip]" in rendered


def test_r_home_derived_from_executable_paths(tmp_path):
    """`<home>/bin/R` and `<home>/bin/<arch>/R.exe` both reduce to `<home>`.

    Built from ``tmp_path`` rather than literal POSIX strings: ``Path.resolve``
    anchors a leading-slash path to the current drive on Windows, so hardcoded
    ``/usr/lib/R`` would compare unequal there for reasons unrelated to the
    logic under test.
    """
    from robstattm_py._renv.discovery import _r_home_from_executable

    home = tmp_path / "R-4.5.2"
    (home / "bin" / "x64").mkdir(parents=True)
    (home / "bin" / "R").write_text("#!/bin/sh\n")
    (home / "bin" / "x64" / "R.exe").write_text("")

    assert _r_home_from_executable(home / "bin" / "R") == home
    assert _r_home_from_executable(home / "bin" / "x64" / "R.exe") == home

    odd = tmp_path / "somewhere" / "odd"
    odd.mkdir(parents=True)
    (odd / "R").write_text("")
    assert _r_home_from_executable(odd / "R") is None
