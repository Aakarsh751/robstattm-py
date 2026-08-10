"""Filesystem layout: overrides, platform defaults, and containment."""
from __future__ import annotations

from pathlib import Path

import pytest

from robstattm_py._renv import paths

from .conftest import make_probe


def test_robstattm_home_overrides_the_default(tmp_path):
    probe = make_probe(environ={"ROBSTATTM_HOME": str(tmp_path / "custom")})
    assert paths.root(probe) == (tmp_path / "custom").absolute()


def test_blank_override_is_ignored(tmp_path):
    """An empty variable is a common shell accident, not an instruction."""
    probe = make_probe(system="Linux", machine="x86_64", environ={"ROBSTATTM_HOME": "   "})
    assert paths.root(probe) != Path("   ")


def test_override_expands_user(tmp_path):
    probe = make_probe(environ={"ROBSTATTM_HOME": "~/rtm-test"})
    assert "~" not in str(paths.root(probe))


@pytest.mark.parametrize(
    ("system", "machine", "env", "expected_tail"),
    [
        ("Windows", "AMD64", {"LOCALAPPDATA": r"C:\Users\x\AppData\Local"}, "robstattm-py"),
        ("Darwin", "arm64", {}, "robstattm-py"),
        ("Linux", "x86_64", {"XDG_DATA_HOME": "/home/x/.local/share"}, "robstattm-py"),
    ],
)
def test_fallback_data_dir_per_platform(system, machine, env, expected_tail):
    probe = make_probe(system=system, machine=machine, environ=env, home=Path("/home/x"))
    assert paths._fallback_data_dir(probe).name == expected_tail


def test_layout_is_all_under_one_root(tmp_path):
    """Everything we create must be removable by deleting a single directory."""
    probe = make_probe(environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")})
    root = paths.root(probe)

    for path in (
        paths.env_prefix(probe),
        paths.pkgs_dir(probe),
        paths.bin_dir(probe),
        paths.micromamba_exe(probe),
        paths.log_dir(probe),
        paths.state_file(probe),
        paths.lock_file(probe),
        paths.provisioned_r_home(probe),
        paths.rlib_dir("4.5", "win-64", probe),
    ):
        assert root in path.parents or path == root, path


def test_provisioned_r_home_uses_lib_r_on_every_platform(tmp_path):
    """conda-forge keeps the lib/R layout on Windows too."""
    for system, machine in (("Windows", "AMD64"), ("Darwin", "arm64"), ("Linux", "x86_64")):
        probe = make_probe(
            system=system, machine=machine, environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")}
        )
        assert paths.provisioned_r_home(probe) == paths.env_prefix(probe) / "lib" / "R"


def test_micromamba_exe_has_the_right_extension(tmp_path):
    env = {"ROBSTATTM_HOME": str(tmp_path / "rtm")}
    win = make_probe(system="Windows", environ=env)
    nix = make_probe(system="Linux", machine="x86_64", environ=env)
    assert paths.micromamba_exe(win).name == "micromamba.exe"
    assert paths.micromamba_exe(nix).name == "micromamba"


def test_rlib_dir_is_keyed_on_r_minor_and_platform(tmp_path):
    """Compiled R packages are ABI-incompatible across R minors."""
    probe = make_probe(environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")})
    a = paths.rlib_dir("4.4", "win-64", probe)
    b = paths.rlib_dir("4.5", "win-64", probe)
    c = paths.rlib_dir("4.5", "linux-64", probe)
    assert a != b != c and a != c


def test_is_within_root_guards_destructive_operations(tmp_path):
    probe = make_probe(environ={"ROBSTATTM_HOME": str(tmp_path / "rtm")})
    assert paths.is_within_root(paths.env_prefix(probe), probe)
    assert paths.is_within_root(paths.root(probe), probe)
    assert not paths.is_within_root(tmp_path / "elsewhere", probe)
    assert not paths.is_within_root(Path("/"), probe)


def test_no_path_helper_creates_anything(tmp_path):
    """`robstattm-py info` and plain imports must not touch the filesystem."""
    root = tmp_path / "rtm"
    probe = make_probe(environ={"ROBSTATTM_HOME": str(root)})

    for fn in (
        paths.root,
        paths.env_prefix,
        paths.pkgs_dir,
        paths.bin_dir,
        paths.micromamba_exe,
        paths.log_dir,
        paths.state_file,
        paths.lock_file,
        paths.provisioned_r_home,
    ):
        fn(probe)

    assert not root.exists()


def test_ensure_dir_is_the_only_creator(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    assert paths.ensure_dir(target).is_dir()
    assert paths.ensure_dir(target).is_dir()  # idempotent


def test_documented_env_vars_are_non_empty():
    described = paths.describe_env_vars()
    assert "ROBSTATTM_HOME" in described
    assert "ROBSTATTM_R_HOME" in described
    assert all(v.strip() for v in described.values())
