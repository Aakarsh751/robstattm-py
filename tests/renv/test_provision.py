"""Provisioning logic that can be checked without downloading anything.

The expensive parts (an actual ``micromamba create``) are covered by the
``provision.yml`` CI workflow on genuinely clean machines. What is tested here
is everything that can go wrong *before* the network is touched — the package
specification, the command line, environment isolation, state transitions, and
the locking — because those are the parts that silently drift.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from robstattm_py._renv import micromamba, provision, state
from robstattm_py._renv.probe import SOURCE_BUILD_SUBDIRS, SUPPORTED_SUBDIRS

from .conftest import make_probe

# ---------------------------------------------------------------------------
# Package specification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subdir", SUPPORTED_SUBDIRS)
def test_spec_always_requests_r_and_the_core_dependencies(subdir):
    spec = provision.package_spec(subdir)
    assert any(s.startswith("r-base") for s in spec)
    assert "r-robustbase" in spec
    assert "r-rrcov" in spec


@pytest.mark.parametrize("subdir", sorted(set(SUPPORTED_SUBDIRS) - SOURCE_BUILD_SUBDIRS))
def test_spec_uses_prebuilt_robstattm_where_conda_forge_has_it(subdir):
    spec = provision.package_spec(subdir)
    assert "r-robstattm" in spec
    assert "r-pyinit" in spec
    assert "c-compiler" not in spec, "no toolchain needed when binaries exist"


@pytest.mark.parametrize("subdir", sorted(SOURCE_BUILD_SUBDIRS))
def test_spec_requests_a_toolchain_where_conda_forge_lacks_builds(subdir):
    """osx-arm64 has no r-robstattm/r-pyinit, so they are compiled instead."""
    spec = provision.package_spec(subdir)
    assert "r-robstattm" not in spec
    assert "r-pyinit" not in spec
    for tool in ("c-compiler", "cxx-compiler", "fortran-compiler"):
        assert tool in spec


def test_r_base_is_not_pinned_to_an_exact_version():
    """A hard pin fights conda-forge's own run constraints and breaks the solve."""
    spec = provision.package_spec("linux-64")
    r_base = next(s for s in spec if s.startswith("r-base"))
    assert "=" not in r_base.replace(">=", ""), r_base


def test_spec_never_includes_a_second_python():
    """A python in the R environment would shadow the user's interpreter."""
    for subdir in SUPPORTED_SUBDIRS:
        spec = provision.package_spec(subdir)
        assert not any(s == "python" or s.startswith("python=") for s in spec)
        assert "rpy2" not in spec


def test_spec_is_sorted_so_the_hash_is_stable():
    assert provision.package_spec("linux-64") == sorted(provision.package_spec("linux-64"))


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def test_create_argv_isolates_from_user_configuration(tmp_path):
    argv = provision.build_create_argv(
        Path("mm"), tmp_path / "env", ["r-base"], probe=make_probe(
            environ={"ROBSTATTM_HOME": str(tmp_path)}
        )
    )
    # Any of these missing means a user's .condarc or channel list can break us.
    assert "--no-rc" in argv
    assert "--override-channels" in argv
    assert "--channel" in argv and "conda-forge" in argv
    assert "--yes" in argv
    assert "--root-prefix" in argv


def test_create_argv_dry_run_asks_for_json(tmp_path):
    argv = provision.build_create_argv(
        Path("mm"), tmp_path / "env", ["r-base"], dry_run=True,
        probe=make_probe(environ={"ROBSTATTM_HOME": str(tmp_path)}),
    )
    assert "--dry-run" in argv and "--json" in argv


def test_create_argv_can_target_a_foreign_platform(tmp_path):
    """CI solves for all platforms from one Linux runner using this."""
    argv = provision.build_create_argv(
        Path("mm"), tmp_path / "env", ["r-base"], platform="osx-arm64",
        probe=make_probe(environ={"ROBSTATTM_HOME": str(tmp_path)}),
    )
    assert argv[argv.index("--platform") + 1] == "osx-arm64"


# ---------------------------------------------------------------------------
# Environment isolation
# ---------------------------------------------------------------------------


def test_child_env_strips_conda_mamba_and_r_variables(tmp_path):
    polluted = {
        "ROBSTATTM_HOME": str(tmp_path),
        "CONDA_PREFIX": "/opt/conda",
        "CONDA_DEFAULT_ENV": "base",
        "CONDARC": "/home/u/.condarc",
        "MAMBA_ROOT_PREFIX": "/home/u/micromamba",
        "_CE_CONDA": "1",
        "R_HOME": "/usr/lib/R",
        "R_LIBS": "/home/u/R",
        "R_LIBS_USER": "/home/u/R",
        "R_PROFILE_USER": "/home/u/.Rprofile",
        "PATH": "/usr/bin",
    }
    env = provision.child_env(make_probe(environ=polluted))

    for leaked in (
        "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "_CE_CONDA",
        "R_HOME", "R_LIBS", "R_LIBS_USER", "R_PROFILE_USER",
    ):
        assert leaked not in env, f"{leaked} leaked into the child environment"
    assert env["PATH"] == "/usr/bin", "unrelated variables must survive"
    assert env["MAMBA_ROOT_PREFIX"] == str(tmp_path)


def test_child_env_does_not_set_condarc(tmp_path):
    """Regression: CONDARC together with --no-rc makes micromamba abort.

    It reports "Configuration files disabled by 'no_rc'" followed by
    "Incompatible configuration", and creates nothing. Isolation comes from
    *removing* CONDARC from the inherited environment, not from pointing it
    somewhere harmless.
    """
    env = provision.child_env(
        make_probe(environ={"ROBSTATTM_HOME": str(tmp_path), "CONDARC": "/home/u/.condarc"})
    )
    assert "CONDARC" not in env

    argv = provision.build_create_argv(
        Path("mm"), tmp_path / "env", ["r-base"],
        probe=make_probe(environ={"ROBSTATTM_HOME": str(tmp_path)}),
    )
    assert "--no-rc" in argv


# ---------------------------------------------------------------------------
# State and locking
# ---------------------------------------------------------------------------


def test_spec_hash_changes_with_every_input():
    base = state.spec_hash(["a", "b"], "linux-64", "2.9.0-0")
    assert base == state.spec_hash(["b", "a"], "linux-64", "2.9.0-0"), "order must not matter"
    assert base != state.spec_hash(["a"], "linux-64", "2.9.0-0")
    assert base != state.spec_hash(["a", "b"], "win-64", "2.9.0-0")
    assert base != state.spec_hash(["a", "b"], "linux-64", "2.0.0-0")


def test_state_round_trips(isolated_env):
    probe = make_probe(environ={"ROBSTATTM_HOME": str(isolated_env)})
    original = state.State(
        status="ready", spec_hash="abc", r_home="/x/lib/R", r_version="4.5.2",
        subdir="linux-64", packages={"RobStatTM": "1.0.11"},
    )
    original.save(probe)

    loaded = state.State.load(probe)
    assert loaded.is_ready
    assert loaded.matches("abc")
    assert not loaded.matches("different")
    assert loaded.packages == {"RobStatTM": "1.0.11"}


def test_corrupt_state_is_treated_as_absent(isolated_env):
    """A damaged metadata file must cost a rebuild, not break the package."""
    from robstattm_py._renv import paths

    probe = make_probe(environ={"ROBSTATTM_HOME": str(isolated_env)})
    paths.ensure_dir(isolated_env)
    paths.state_file(probe).write_text("{not json", encoding="utf-8")

    loaded = state.State.load(probe)
    assert loaded.status == "absent"
    assert not loaded.is_ready


def test_future_schema_is_treated_as_absent(isolated_env):
    from robstattm_py._renv import paths

    probe = make_probe(environ={"ROBSTATTM_HOME": str(isolated_env)})
    paths.ensure_dir(isolated_env)
    paths.state_file(probe).write_text(
        json.dumps({"schema": 999, "status": "ready"}), encoding="utf-8"
    )
    assert state.State.load(probe).status == "absent"


def test_lock_is_exclusive(isolated_env):
    probe = make_probe(environ={"ROBSTATTM_HOME": str(isolated_env)})
    with state.SetupLock(probe):
        with pytest.raises(state.LockedError, match="already running"):
            with state.SetupLock(probe):
                pass


def test_lock_is_released_even_when_the_body_raises(isolated_env):
    probe = make_probe(environ={"ROBSTATTM_HOME": str(isolated_env)})
    with pytest.raises(ValueError):
        with state.SetupLock(probe):
            raise ValueError("boom")
    # A crashed setup must not wedge the machine permanently.
    with state.SetupLock(probe):
        pass


def test_force_unlock_breaks_a_stale_lock(isolated_env):
    probe = make_probe(environ={"ROBSTATTM_HOME": str(isolated_env)})
    with state.SetupLock(probe):
        with state.SetupLock(probe, force=True):
            pass


# ---------------------------------------------------------------------------
# Uninstall safety
# ---------------------------------------------------------------------------


def test_uninstall_refuses_to_touch_anything_outside_its_own_root(isolated_env, monkeypatch):
    """A misconfigured ROBSTATTM_HOME must not turn this into `rm -rf`."""
    from robstattm_py._renv import paths

    monkeypatch.setenv("ROBSTATTM_HOME", str(isolated_env))
    outside = isolated_env.parent / "not-ours"
    outside.mkdir(parents=True, exist_ok=True)
    (outside / "precious.txt").write_text("keep me", encoding="utf-8")

    assert not paths.is_within_root(outside)

    provision.uninstall(dry_run=True)
    assert (outside / "precious.txt").exists()


def test_uninstall_dry_run_removes_nothing(isolated_env, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(isolated_env))
    env_prefix = isolated_env / "envs" / "r"
    env_prefix.mkdir(parents=True)
    (env_prefix / "file.bin").write_bytes(b"x" * 1024)

    planned = provision.uninstall(dry_run=True)
    assert planned
    assert env_prefix.exists()


def test_uninstall_keeps_the_download_cache_by_default(isolated_env, monkeypatch):
    """Keeping pkgs/ is what makes a re-setup take seconds instead of minutes."""
    monkeypatch.setenv("ROBSTATTM_HOME", str(isolated_env))
    (isolated_env / "envs" / "r").mkdir(parents=True)
    pkgs = isolated_env / "pkgs"
    pkgs.mkdir(parents=True)
    (pkgs / "cached.tar.bz2").write_bytes(b"x" * 512)

    provision.uninstall(env=True, rlibs=True, cache=False)
    assert pkgs.exists()
    assert not (isolated_env / "envs" / "r").exists()


# ---------------------------------------------------------------------------
# micromamba pin
# ---------------------------------------------------------------------------


def test_every_supported_platform_has_a_pinned_checksum():
    """Catches a version bump that forgot a platform."""
    missing = set(SUPPORTED_SUBDIRS) - set(micromamba.MICROMAMBA_SHA256)
    assert not missing, f"no pinned micromamba checksum for: {sorted(missing)}"


@pytest.mark.parametrize("subdir", sorted(micromamba.MICROMAMBA_SHA256))
def test_checksums_look_like_sha256(subdir):
    digest = micromamba.MICROMAMBA_SHA256[subdir]
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


@pytest.mark.parametrize("subdir", sorted(micromamba.MICROMAMBA_SHA256))
def test_download_urls_are_well_formed(subdir):
    url = micromamba.micromamba_url(subdir)
    assert url.startswith("https://github.com/mamba-org/micromamba-releases/releases/download/")
    assert micromamba.MICROMAMBA_VERSION in url
    assert url.endswith(".exe") == subdir.startswith("win")


def test_unsupported_platform_is_reported_clearly():
    with pytest.raises(micromamba.UnsupportedPlatformError, match="linux-s390x"):
        micromamba.micromamba_url("linux-s390x")


# ---------------------------------------------------------------------------
# Windows path length
# ---------------------------------------------------------------------------


def test_preflight_rejects_a_long_windows_path_before_downloading(monkeypatch, tmp_path):
    """Regression: a 261-character cache path failed *after* a 250 MB download.

    conda-forge's Windows R build pulls in a mingw headers package whose files
    sit ~215 characters deep inside the cache. micromamba reports the overflow
    only as "Package cache error", minutes in and with no hint of the cause, so
    this has to be caught up front.
    """
    from robstattm_py._renv import paths

    monkeypatch.setattr(paths, "windows_long_paths_enabled", lambda: False)
    long_root = tmp_path / ("d" * 120)
    probe = make_probe(system="Windows", environ={"ROBSTATTM_HOME": str(long_root)})

    with pytest.raises(provision.LongPathError) as excinfo:
        provision.preflight(probe)

    message = str(excinfo.value)
    assert "ROBSTATTM_HOME" in message
    assert "C:\\rtm" in message, "the fix must be copy-pasteable"


def test_preflight_allows_a_long_path_when_long_paths_are_enabled(monkeypatch, tmp_path):
    from robstattm_py._renv import paths

    monkeypatch.setattr(paths, "windows_long_paths_enabled", lambda: True)
    long_root = tmp_path / ("d" * 120)
    probe = make_probe(system="Windows", environ={"ROBSTATTM_HOME": str(long_root)})

    provision.preflight(probe)  # must not raise


def test_preflight_ignores_path_length_off_windows(monkeypatch, tmp_path):
    long_root = tmp_path / ("d" * 200)
    probe = make_probe(
        system="Linux", machine="x86_64", environ={"ROBSTATTM_HOME": str(long_root)}
    )
    provision.preflight(probe)  # must not raise


def test_the_safe_root_budget_matches_the_observed_depth():
    from robstattm_py._renv import paths

    assert (
        paths.max_safe_root_length()
        == paths.WINDOWS_MAX_PATH - paths.DEEPEST_INTERNAL_PATH
    )
    assert paths.max_safe_root_length() > 0


def test_opaque_micromamba_cache_errors_are_translated(tmp_path):
    """"Package cache error" is really a path overflow; say so."""
    windows = make_probe(system="Windows", environ={"ROBSTATTM_HOME": str(tmp_path)})
    linux = make_probe(
        system="Linux", machine="x86_64", environ={"ROBSTATTM_HOME": str(tmp_path)}
    )
    log = (
        "warning  libmamba Invalid package cache, file '...' is missing\n"
        "error    libmamba Cannot find a valid extracted directory cache for 'x'\n"
        "critical libmamba Package cache error.\n"
    )

    assert provision._looks_like_path_overflow(log, windows)
    # The same words on Linux mean something else; do not mislead.
    assert not provision._looks_like_path_overflow(log, linux)
    assert not provision._looks_like_path_overflow("nothing provides r-base", windows)


def test_licence_notice_names_both_licences():
    """Users must be told what they are downloading before it happens."""
    notice = provision.licence_notice()
    assert "GPL-2" in notice and "GPL-3" in notice
    assert "MIT" in notice
    assert "redistributes" in notice
