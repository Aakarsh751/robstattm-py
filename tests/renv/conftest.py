"""Fixtures for the R-free ``_renv`` tests.

Everything here builds a *synthetic* R installation on disk: a
``library/base/DESCRIPTION`` with a version, an ``etc/`` directory, and a
shared library whose first bytes are a hand-built PE / ELF / Mach-O header.
That is exactly the set of things
:func:`robstattm_py._renv.validate.validate_r_home` inspects, so these fakes
exercise the real code path without R, a network, or a 250 MB download.
"""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from robstattm_py._renv.probe import Probe

# ---------------------------------------------------------------------------
# Synthetic binary headers
# ---------------------------------------------------------------------------

_PE_MACHINES = {"x86_64": 0x8664, "arm64": 0xAA64, "i386": 0x014C}
_ELF_MACHINES = {"x86_64": 0x3E, "arm64": 0xB7, "i386": 0x03, "ppc64le": 0x15}
_MACHO_CPUS = {"x86_64": 0x01000007, "arm64": 0x0100000C, "i386": 0x00000007}


def pe_header(arch: str = "x86_64", *, pe_offset: int = 0x80) -> bytes:
    """Build a minimal PE (Windows DLL) header for ``arch``."""
    buf = bytearray(pe_offset + 8)
    buf[0:2] = b"MZ"
    struct.pack_into("<I", buf, 0x3C, pe_offset)
    buf[pe_offset : pe_offset + 4] = b"PE\0\0"
    struct.pack_into("<H", buf, pe_offset + 4, _PE_MACHINES[arch])
    return bytes(buf)


def elf_header(arch: str = "x86_64", *, little_endian: bool = True) -> bytes:
    """Build a minimal ELF (Linux .so) header for ``arch``."""
    buf = bytearray(64)
    buf[0:4] = b"\x7fELF"
    buf[4] = 2  # ELFCLASS64
    buf[5] = 1 if little_endian else 2
    buf[6] = 1  # EV_CURRENT
    endian = "<" if little_endian else ">"
    struct.pack_into(f"{endian}H", buf, 16, 3)  # ET_DYN
    struct.pack_into(f"{endian}H", buf, 18, _ELF_MACHINES[arch])
    return bytes(buf)


def macho_header(arch: str = "x86_64", *, little_endian: bool = True) -> bytes:
    """Build a minimal thin 64-bit Mach-O (macOS .dylib) header for ``arch``."""
    endian = "<" if little_endian else ">"
    return struct.pack(f"{endian}II", 0xFEEDFACF, _MACHO_CPUS[arch]) + b"\0" * 56


def macho_fat_header(*archs: str) -> bytes:
    """Build a fat (universal) Mach-O header containing ``archs`` slices."""
    buf = bytearray(struct.pack(">II", 0xCAFEBABE, len(archs)))
    for i, arch in enumerate(archs):
        # fat_arch: cputype, cpusubtype, offset, size, align
        buf += struct.pack(">IIIII", _MACHO_CPUS[arch], 0, 4096 * (i + 1), 4096, 12)
    return bytes(buf).ljust(256, b"\0")


def header_for(arch: str, system: str) -> bytes:
    """Return an appropriate shared-library header for ``system``."""
    if system == "Windows":
        return pe_header(arch)
    if system == "Darwin":
        return macho_header(arch)
    return elf_header(arch)


# ---------------------------------------------------------------------------
# Synthetic R installations
# ---------------------------------------------------------------------------


def make_r_home(
    base: Path,
    name: str = "R-4.5.2",
    *,
    version: str = "4.5.2",
    arch: str = "x86_64",
    system: str = "Windows",
    with_lib: bool = True,
    with_etc: bool = True,
    lib_arch: str | None = None,
) -> Path:
    """Create a fake R installation and return its ``R_HOME``.

    Parameters
    ----------
    lib_arch : str, optional
        Place the shared library in a *different* architecture's directory than
        ``arch`` implies. Used to reproduce the Windows "only a 32-bit R is
        installed" case.
    """
    home = base / name
    (home / "library" / "base").mkdir(parents=True, exist_ok=True)
    (home / "library" / "base" / "DESCRIPTION").write_text(
        f"Package: base\nVersion: {version}\nPriority: base\n", encoding="utf-8"
    )
    if with_etc:
        (home / "etc").mkdir(exist_ok=True)

    if with_lib:
        placed = lib_arch or arch
        if system == "Windows":
            subdir = {"x86_64": "x64", "arm64": "arm64", "i386": "i386"}[placed]
            libdir = home / "bin" / subdir
            libname = "R.dll"
        elif system == "Darwin":
            libdir = home / "lib"
            libname = "libR.dylib"
        else:
            libdir = home / "lib"
            libname = "libR.so"
        libdir.mkdir(parents=True, exist_ok=True)
        (libdir / libname).write_bytes(header_for(arch, system))
    return home


def make_conda_prefix(
    base: Path,
    name: str = "envs/r",
    *,
    version: str = "4.5.2",
    arch: str = "x86_64",
    system: str = "Linux",
) -> Path:
    """Create a fake conda prefix containing R at ``<prefix>/lib/R``."""
    prefix = base / name
    (prefix / "conda-meta").mkdir(parents=True, exist_ok=True)
    (prefix / "lib").mkdir(parents=True, exist_ok=True)
    make_r_home(prefix / "lib", "R", version=version, arch=arch, system=system)
    return prefix


# ---------------------------------------------------------------------------
# Probe construction
# ---------------------------------------------------------------------------


def make_probe(
    *,
    system: str = "Windows",
    machine: str = "AMD64",
    is_64bit: bool = True,
    environ: dict[str, str] | None = None,
    path_exes: dict[str, str] | None = None,
    home: Path | None = None,
    sys_prefix: Path | None = None,
    registry: list[tuple[Path, str]] | None = None,
    system_roots: tuple[Path, ...] = (),
) -> Probe:
    """Build a synthetic :class:`Probe`.

    ``path_exes`` maps an executable name to the path ``which`` should report,
    letting a test place a working — or deliberately broken — ``R`` on ``PATH``.

    ``registry`` and ``system_roots`` both default to *empty* rather than
    ``None``, which is the important part: ``None`` would mean "look at the real
    machine". A test describing a host with no R must not be quietly
    contradicted by the R that happens to be installed on a CI runner - that is
    precisely how these tests passed locally and failed on Linux, where
    ``/opt/R/4.6.1`` exists.
    """
    exes = path_exes or {}
    installs = list(registry or [])
    return Probe(
        system=system,
        machine=machine,
        is_64bit=is_64bit,
        environ=environ if environ is not None else {},
        which=lambda name: exes.get(name),
        home=home or Path("/nonexistent-home"),
        sys_prefix=sys_prefix or Path("/nonexistent-prefix"),
        registry_installs=lambda: installs,
        system_roots=system_roots,
    )


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point ROBSTATTM_HOME at a scratch directory for the duration of a test."""
    root = tmp_path / "rtm-home"
    monkeypatch.setenv("ROBSTATTM_HOME", str(root))
    return root


@pytest.fixture(autouse=True)
def _reset_renv_state():
    """Clear memoised discovery/activation state between tests."""
    from robstattm_py import _renv

    _renv.reset_for_tests()
    yield
    _renv.reset_for_tests()
