"""Validation of a candidate ``R_HOME``.

The interesting cases are the *rejections*: each one corresponds to a real
support question, and each must produce a message that names the actual problem
rather than "R not found".
"""
from __future__ import annotations

import pytest

from robstattm_py._renv.errors import ArchMismatchError, InvalidRHomeError, RTooOldError
from robstattm_py._renv.validate import read_r_version, validate_r_home

from .conftest import make_conda_prefix, make_probe, make_r_home


def test_valid_windows_r_home(tmp_path):
    home = make_r_home(tmp_path, system="Windows", arch="x86_64", version="4.5.2")
    info = validate_r_home(home, probe=make_probe())

    assert info.version == (4, 5, 2)
    assert info.version_string == "4.5.2"
    assert info.arch == "x86_64"
    assert info.minor == "4.5"
    assert info.shared_lib.name == "R.dll"
    assert info.conda_prefix is None


def test_valid_linux_r_home(tmp_path):
    home = make_r_home(tmp_path, "R", system="Linux", arch="x86_64")
    info = validate_r_home(home, probe=make_probe(system="Linux", machine="x86_64"))

    assert info.shared_lib.name == "libR.so"
    assert info.arch == "x86_64"


def test_conda_prefix_is_detected(tmp_path):
    prefix = make_conda_prefix(tmp_path, system="Linux")
    info = validate_r_home(
        prefix / "lib" / "R", probe=make_probe(system="Linux", machine="x86_64")
    )

    assert info.conda_prefix == prefix
    # The conda prefix's own lib dir must be on the search path: R's DLLs link
    # against runtime libraries that live there, not next to R itself.
    assert prefix / "lib" in info.bin_dirs


def test_windows_conda_prefix_collects_library_bin_dirs(tmp_path):
    prefix = make_conda_prefix(tmp_path, system="Windows")
    for sub in ("Library/bin", "Library/mingw-w64/bin", "bin"):
        (prefix / sub).mkdir(parents=True, exist_ok=True)

    info = validate_r_home(prefix / "lib" / "R", probe=make_probe())

    # This breadth is the fix for `LoadLibrary failure`: rpy2 registers one
    # directory, but R's own DLLs need the conda runtime directories too.
    assert prefix / "Library" / "bin" in info.bin_dirs
    assert prefix / "Library" / "mingw-w64" / "bin" in info.bin_dirs
    assert info.bin_dirs[0] == prefix / "lib" / "R" / "bin" / "x64"


def test_missing_directory_is_rejected(tmp_path):
    with pytest.raises(InvalidRHomeError, match="Not a directory"):
        validate_r_home(tmp_path / "nope", probe=make_probe())


def test_directory_without_description_is_rejected(tmp_path):
    """The classic "a stale bin directory is on PATH" case."""
    empty = tmp_path / "not-r"
    empty.mkdir()
    with pytest.raises(InvalidRHomeError, match="does not look like an R installation"):
        validate_r_home(empty, probe=make_probe())


def test_missing_etc_is_rejected(tmp_path):
    home = make_r_home(tmp_path, with_etc=False)
    with pytest.raises(InvalidRHomeError, match="incomplete"):
        validate_r_home(home, probe=make_probe())


def test_missing_shared_library_is_rejected_with_a_clear_reason(tmp_path):
    """Catch this at discovery time, not as an opaque LoadLibrary failure."""
    home = make_r_home(tmp_path, with_lib=False)
    with pytest.raises(InvalidRHomeError, match="no loadable shared library"):
        validate_r_home(home, probe=make_probe())


def test_too_old_r_is_rejected(tmp_path):
    home = make_r_home(tmp_path, "R-3.6.3", version="3.6.3")
    with pytest.raises(RTooOldError, match="too old"):
        validate_r_home(home, probe=make_probe())


def test_arch_mismatch_is_rejected(tmp_path):
    """An x86_64 R must never be handed to an arm64 Python: it would crash."""
    home = make_r_home(tmp_path, system="Darwin", arch="x86_64")
    probe = make_probe(system="Darwin", machine="arm64")

    with pytest.raises(ArchMismatchError, match="is x86_64, but this Python is arm64"):
        validate_r_home(home, probe=probe)


def test_windows_wrong_arch_directory_says_which_arch_is_present(tmp_path):
    """"Only a 32-bit R is installed" must be distinguishable from "no R"."""
    home = make_r_home(tmp_path, arch="i386", lib_arch="i386", system="Windows")
    probe = make_probe(system="Windows", machine="AMD64", is_64bit=True)

    with pytest.raises(InvalidRHomeError, match=r"only a i386 R\.dll is present"):
        validate_r_home(home, probe=probe)


def test_check_arch_false_allows_reporting_on_a_mismatched_r(tmp_path):
    """`doctor` must be able to describe an R it would refuse to load."""
    home = make_r_home(tmp_path, system="Darwin", arch="x86_64")
    probe = make_probe(system="Darwin", machine="arm64")

    info = validate_r_home(home, probe=probe, check_arch=False)
    assert info.arch == "x86_64"


def test_unknown_arch_is_not_treated_as_a_mismatch(tmp_path):
    """If we cannot parse the header, defer to the loader rather than refuse."""
    home = make_r_home(tmp_path, system="Linux", arch="x86_64")
    (home / "lib" / "libR.so").write_bytes(b"\x00" * 128)

    info = validate_r_home(home, probe=make_probe(system="Linux", machine="x86_64"))
    assert info.arch == "unknown"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("4.5.2", (4, 5, 2)), ("4.6", (4, 6, 0)), ("4", (4, 0, 0)), ("4.10.0", (4, 10, 0))],
)
def test_read_r_version_variants(tmp_path, raw, expected):
    home = make_r_home(tmp_path, f"R-{raw}", version=raw)
    parsed = read_r_version(home)
    assert parsed is not None
    assert parsed[0] == expected


def test_read_r_version_missing_file(tmp_path):
    assert read_r_version(tmp_path / "nothing") is None


def test_with_source_preserves_everything_else(tmp_path):
    home = make_r_home(tmp_path)
    info = validate_r_home(home, probe=make_probe(), source="original")
    tagged = info.with_source("provisioned")

    assert tagged.source == "provisioned"
    assert tagged.is_provisioned
    assert tagged.path == info.path
    assert tagged.bin_dirs == info.bin_dirs
