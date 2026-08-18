"""Architecture detection from shared-library headers.

These matter more than their size suggests: the arch check is the only thing
standing between a mismatched R and a hard interpreter crash. rpy2 ``dlopen``s R
at import time, so a wrong answer here is not an exception the user can catch,
it is a process that disappears.
"""
from __future__ import annotations

import pytest

from robstattm_py._renv.probe import Probe, normalise_machine
from robstattm_py._renv.validate import probe_arch

from .conftest import elf_header, macho_fat_header, macho_header, pe_header


@pytest.mark.parametrize("arch", ["x86_64", "arm64", "i386"])
def test_pe_header(tmp_path, arch):
    lib = tmp_path / "R.dll"
    lib.write_bytes(pe_header(arch))
    assert probe_arch(lib) == arch


@pytest.mark.parametrize("arch", ["x86_64", "arm64", "i386", "ppc64le"])
def test_elf_header_little_endian(tmp_path, arch):
    lib = tmp_path / "libR.so"
    lib.write_bytes(elf_header(arch))
    assert probe_arch(lib) == arch


def test_elf_header_big_endian_is_read_with_correct_endianness(tmp_path):
    """A big-endian ELF must not be misread as some other architecture."""
    lib = tmp_path / "libR.so"
    lib.write_bytes(elf_header("x86_64", little_endian=False))
    assert probe_arch(lib) == "x86_64"


def test_elf_big_endian_ppc64_is_not_reported_as_ppc64le(tmp_path):
    """EM_PPC64 big-endian is ppc64, which conda-forge does not build for."""
    lib = tmp_path / "libR.so"
    lib.write_bytes(elf_header("ppc64le", little_endian=False))
    assert probe_arch(lib) == "unknown"


@pytest.mark.parametrize("arch", ["x86_64", "arm64", "i386"])
def test_macho_thin_little_endian(tmp_path, arch):
    lib = tmp_path / "libR.dylib"
    lib.write_bytes(macho_header(arch))
    assert probe_arch(lib) == arch


def test_macho_thin_big_endian(tmp_path):
    lib = tmp_path / "libR.dylib"
    lib.write_bytes(macho_header("x86_64", little_endian=False))
    assert probe_arch(lib) == "x86_64"


def test_macho_fat_prefers_arm64(tmp_path):
    """A universal binary containing arm64 is arm64 on Apple Silicon."""
    lib = tmp_path / "libR.dylib"
    lib.write_bytes(macho_fat_header("x86_64", "arm64"))
    assert probe_arch(lib) == "arm64"


def test_macho_fat_intel_only(tmp_path):
    lib = tmp_path / "libR.dylib"
    lib.write_bytes(macho_fat_header("x86_64"))
    assert probe_arch(lib) == "x86_64"


def test_unrecognised_format_is_unknown_not_an_error(tmp_path):
    """Refusing to run because a header is exotic would be worse than trying."""
    lib = tmp_path / "libR.so"
    lib.write_bytes(b"this is not a shared library at all, but it is long enough")
    assert probe_arch(lib) == "unknown"


def test_missing_file_is_unknown(tmp_path):
    assert probe_arch(tmp_path / "does-not-exist.so") == "unknown"


def test_truncated_file_is_unknown(tmp_path):
    lib = tmp_path / "R.dll"
    lib.write_bytes(b"MZ")
    assert probe_arch(lib) == "unknown"


def test_pe_with_bogus_offset_is_unknown(tmp_path):
    """A corrupt e_lfanew must not raise out of the parser."""
    lib = tmp_path / "R.dll"
    data = bytearray(pe_header("x86_64"))
    data[0x3C:0x40] = (0xFFFFFF).to_bytes(4, "little")
    lib.write_bytes(bytes(data))
    assert probe_arch(lib) == "unknown"


# ---------------------------------------------------------------------------
# Host architecture normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AMD64", "x86_64"),
        ("x86_64", "x86_64"),
        ("x64", "x86_64"),
        ("arm64", "arm64"),
        ("ARM64", "arm64"),
        ("aarch64", "arm64"),
        ("i686", "i386"),
        ("ppc64le", "ppc64le"),
        ("s390x", "unknown"),
    ],
)
def test_normalise_machine(raw, expected):
    assert normalise_machine(raw) == expected


def test_32bit_python_on_64bit_cpu_reports_i386():
    """A 32-bit interpreter can only load a 32-bit R, whatever the CPU is."""
    probe = Probe(system="Windows", machine="AMD64", is_64bit=False, environ={})
    assert probe.arch == "i386"


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Windows", "AMD64", "win-64"),
        ("Darwin", "x86_64", "osx-64"),
        ("Darwin", "arm64", "osx-arm64"),
        ("Linux", "x86_64", "linux-64"),
        ("Linux", "aarch64", "linux-aarch64"),
        ("Linux", "ppc64le", "linux-ppc64le"),
        ("Linux", "s390x", "unknown"),
        ("Windows", "ARM64", "unknown"),
    ],
)
def test_conda_subdir_mapping(system, machine, expected):
    probe = Probe(system=system, machine=machine, is_64bit=True, environ={})
    assert probe.subdir == expected
