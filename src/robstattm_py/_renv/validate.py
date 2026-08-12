"""Validate a candidate ``R_HOME`` — cheaply, and without risking a crash.

Two properties drive the design.

**No subprocess, no ``dlopen``.** Validation reads files only. Spawning
``R RHOME`` or ``R CMD config`` is slow (tens of milliseconds each, times a
dozen candidates), hangs when the R install is broken, and pops a console
window on Windows. Everything we need — the version and the architecture — is
readable directly from ``library/base/DESCRIPTION`` and from the first bytes of
R's shared library.

**Architecture is checked before rpy2 sees the path.** Handing rpy2 an R built
for a different architecture does not raise a Python exception; it terminates
the interpreter. Since rpy2 resolves and ``dlopen``s R at *module import* time
(``rpy2/rinterface_lib/openrlib.py``), by the time anything could catch the
problem the process is already gone. So we parse the PE / ELF / Mach-O header
ourselves and reject the candidate first.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path

from robstattm_py._renv.errors import ArchMismatchError, InvalidRHomeError, RTooOldError
from robstattm_py._renv.probe import (
    ARCH_ARM64,
    ARCH_I386,
    ARCH_PPC64LE,
    ARCH_UNKNOWN,
    ARCH_X86_64,
    Probe,
)

#: Oldest R we support. RobStatTM itself declares ``R (>= 3.5.0)``, but rpy2
#: 3.6 requires 4.2+, and that is the binding that actually has to load.
MIN_R_VERSION: tuple[int, int, int] = (4, 2, 0)

_VERSION_LINE = re.compile(r"^Version:\s*([0-9]+(?:\.[0-9]+)*)", re.MULTILINE)

# Windows architecture subdirectory under <R_HOME>/bin, by normalised arch.
_WIN_ARCH_DIRS: dict[str, str] = {
    ARCH_X86_64: "x64",
    ARCH_ARM64: "arm64",
    ARCH_I386: "i386",
}


@dataclass(frozen=True, slots=True)
class RHomeInfo:
    """A validated R installation.

    Attributes
    ----------
    path : Path
        ``R_HOME`` — the installation root containing ``library/`` and ``etc/``.
    version : tuple[int, int, int]
        Parsed R version, zero-padded to three components.
    version_string : str
        Version as written in ``library/base/DESCRIPTION``, e.g. ``"4.5.2"``.
    arch : str
        Normalised architecture of R's shared library.
    shared_lib : Path
        The ``R.dll`` / ``libR.so`` / ``libR.dylib`` that rpy2 will load.
    bin_dirs : tuple[Path, ...]
        Directories that must be on the DLL / library search path, in priority
        order. Applied by :mod:`robstattm_py._renv.activate`.
    source : str
        Identifier of the discovery rung that produced this candidate.
    conda_prefix : Path or None
        The conda environment root when this R is a conda installation.
    """

    path: Path
    version: tuple[int, int, int]
    version_string: str
    arch: str
    shared_lib: Path
    bin_dirs: tuple[Path, ...]
    source: str = "unknown"
    conda_prefix: Path | None = None

    @property
    def minor(self) -> str:
        """R's ``major.minor`` version, e.g. ``"4.5"`` — the ABI key."""
        return f"{self.version[0]}.{self.version[1]}"

    @property
    def is_provisioned(self) -> bool:
        """True when this R is the one robstattm-py provisioned itself."""
        return self.source == "provisioned"

    def with_source(self, source: str) -> RHomeInfo:
        """Return a copy tagged with a different discovery source."""
        return RHomeInfo(
            path=self.path,
            version=self.version,
            version_string=self.version_string,
            arch=self.arch,
            shared_lib=self.shared_lib,
            bin_dirs=self.bin_dirs,
            source=source,
            conda_prefix=self.conda_prefix,
        )


# ---------------------------------------------------------------------------
# Binary header parsing
# ---------------------------------------------------------------------------


def probe_arch(shared_lib: Path) -> str:
    """Return the architecture of a native shared library.

    Reads at most 4 KiB and understands PE (Windows), ELF (Linux), and both
    thin and fat Mach-O (macOS).

    Parameters
    ----------
    shared_lib : Path
        Path to a ``.dll`` / ``.so`` / ``.dylib``.

    Returns
    -------
    str
        A normalised architecture name, or ``"unknown"`` if the format is not
        recognised. ``"unknown"`` is deliberately *not* treated as a mismatch by
        callers — refusing to run because we could not parse an exotic binary
        would be worse than trying and letting the loader decide.
    """
    try:
        with shared_lib.open("rb") as fh:
            head = fh.read(4096)
    except OSError:
        return ARCH_UNKNOWN
    if len(head) < 8:
        return ARCH_UNKNOWN

    if head[:2] == b"MZ":
        return _probe_pe(head)
    if head[:4] == b"\x7fELF":
        return _probe_elf(head)
    return _probe_macho(head)


def _probe_pe(head: bytes) -> str:
    """Parse a PE (Windows) header's ``Machine`` field."""
    machines = {0x8664: ARCH_X86_64, 0xAA64: ARCH_ARM64, 0x014C: ARCH_I386}
    try:
        e_lfanew = struct.unpack_from("<I", head, 0x3C)[0]
        if head[e_lfanew : e_lfanew + 4] != b"PE\0\0":
            return ARCH_UNKNOWN
        machine = struct.unpack_from("<H", head, e_lfanew + 4)[0]
    except (struct.error, IndexError):
        return ARCH_UNKNOWN
    return machines.get(machine, ARCH_UNKNOWN)


def _probe_elf(head: bytes) -> str:
    """Parse an ELF header's ``e_machine`` field, honouring endianness."""
    machines = {
        0x03: ARCH_I386,
        0x3E: ARCH_X86_64,
        0xB7: ARCH_ARM64,
        0x15: ARCH_PPC64LE,  # EM_PPC64; little-endian variant is ppc64le
    }
    try:
        endian = "<" if head[5] == 1 else ">"
        machine = struct.unpack_from(f"{endian}H", head, 18)[0]
    except (struct.error, IndexError):
        return ARCH_UNKNOWN
    arch = machines.get(machine, ARCH_UNKNOWN)
    # EM_PPC64 big-endian is ppc64, which conda-forge does not target.
    if arch == ARCH_PPC64LE and head[5] != 1:
        return ARCH_UNKNOWN
    return arch


#: Mach-O ``cputype`` values. The 0x01000000 bit marks the 64-bit variant.
_MACHO_CPU_TYPES: dict[int, str] = {
    0x01000007: ARCH_X86_64,
    0x0100000C: ARCH_ARM64,
    0x00000007: ARCH_I386,
}


def _probe_macho(head: bytes) -> str:
    """Parse a thin or fat Mach-O header.

    For a fat (universal) binary, every slice is inspected and the *preferred*
    architecture returned — arm64 ahead of x86_64, matching what the macOS
    loader picks on Apple Silicon.
    """
    try:
        magic = struct.unpack_from(">I", head, 0)[0]
    except struct.error:
        return ARCH_UNKNOWN

    # Thin Mach-O. 0xFEEDFACE/0xFEEDFACF are big-endian-as-read; the byte
    # swapped forms indicate a little-endian file (the usual case on Intel/ARM).
    if magic in (0xFEEDFACE, 0xFEEDFACF):
        endian = ">"
    elif magic in (0xCEFAEDFE, 0xCFFAEDFE):
        endian = "<"
    elif magic in (0xCAFEBABE, 0xBEBAFECA):
        return _probe_macho_fat(head, ">" if magic == 0xCAFEBABE else "<")
    else:
        return ARCH_UNKNOWN

    try:
        cputype = struct.unpack_from(f"{endian}I", head, 4)[0]
    except struct.error:
        return ARCH_UNKNOWN
    return _MACHO_CPU_TYPES.get(cputype, ARCH_UNKNOWN)


def _probe_macho_fat(head: bytes, endian: str) -> str:
    """Return the preferred architecture among a fat binary's slices."""
    try:
        nfat = struct.unpack_from(f"{endian}I", head, 4)[0]
    except struct.error:
        return ARCH_UNKNOWN
    found: set[str] = set()
    for i in range(min(nfat, 32)):  # 32 slices is far beyond any real binary
        offset = 8 + i * 20
        try:
            cputype = struct.unpack_from(f"{endian}I", head, offset)[0]
        except struct.error:
            break
        arch = _MACHO_CPU_TYPES.get(cputype)
        if arch:
            found.add(arch)
    for preferred in (ARCH_ARM64, ARCH_X86_64, ARCH_I386):
        if preferred in found:
            return preferred
    return ARCH_UNKNOWN


# ---------------------------------------------------------------------------
# R home validation
# ---------------------------------------------------------------------------


def read_r_version(r_home: Path) -> tuple[tuple[int, int, int], str] | None:
    """Read R's version from ``library/base/DESCRIPTION``.

    Every R installation — CRAN, conda, distro-packaged — ships this file, so it
    is a reliable version source that costs one small file read instead of an
    ``R --version`` subprocess.

    Returns
    -------
    tuple or None
        ``((major, minor, patch), raw_string)``, or ``None`` when the file is
        absent or has no parseable ``Version:`` line.
    """
    desc = r_home / "library" / "base" / "DESCRIPTION"
    try:
        text = desc.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _VERSION_LINE.search(text)
    if not match:
        return None
    raw = match.group(1)
    parts = [int(p) for p in raw.split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2]), raw


def find_shared_lib(r_home: Path, probe: Probe) -> tuple[Path | None, str | None]:
    """Locate R's shared library under ``r_home``.

    Returns
    -------
    tuple
        ``(path, None)`` on success, or ``(None, reason)`` describing why it
        could not be found. When the only library present is for a different
        architecture, ``reason`` says so — that distinction is what turns a
        baffling ``LoadLibrary failure`` into an actionable message.
    """
    name = probe.shared_lib_name

    if not probe.is_windows:
        for rel in ("lib", "lib64", "bin"):
            candidate = r_home / rel / name
            if candidate.is_file():
                return candidate, None
        return None, f"no {name} under {r_home}/lib"

    # Windows: prefer the subdirectory matching this interpreter, then the flat
    # bin/ layout, and only then report a same-name library for another arch.
    wanted = _WIN_ARCH_DIRS.get(probe.arch)
    ordered = [r_home / "bin" / wanted / name] if wanted else []
    ordered.append(r_home / "bin" / name)
    for candidate in ordered:
        if candidate.is_file():
            return candidate, None

    for other_arch, other_dir in _WIN_ARCH_DIRS.items():
        if other_arch == probe.arch:
            continue
        if (r_home / "bin" / other_dir / name).is_file():
            return None, (
                f"only a {other_arch} {name} is present (in bin\\{other_dir}); "
                f"this Python needs {probe.arch}"
            )
    return None, f"no {name} under {r_home}\\bin"


def _conda_prefix_of(r_home: Path) -> Path | None:
    """Return the conda prefix when ``r_home`` is ``<prefix>/lib/R``."""
    if r_home.name != "R" or r_home.parent.name != "lib":
        return None
    prefix = r_home.parent.parent
    return prefix if (prefix / "conda-meta").is_dir() else None


def _bin_dirs_for(r_home: Path, shared_lib: Path, probe: Probe,
                  conda_prefix: Path | None) -> tuple[Path, ...]:
    """Build the ordered search-path list for this R.

    On Windows this is the crux of the ``LoadLibrary`` fix. rpy2 adds exactly
    one directory, and only via :func:`os.add_dll_directory`
    (``openrlib.py``) — but R's own ``library(stats)`` calls plain
    ``LoadLibrary("stats.dll")``, whose default search order consults ``PATH``
    and ignores ``add_dll_directory`` entries. We therefore collect *every*
    relevant directory and :mod:`~robstattm_py._renv.activate` applies them to
    both mechanisms.
    """
    dirs: list[Path] = [shared_lib.parent]
    if probe.is_windows:
        dirs.append(r_home / "bin")
        if conda_prefix is not None:
            # conda on Windows scatters runtime DLLs (the mingw runtime,
            # openblas, gfortran, zlib, ...) across these; R's own DLLs link
            # against them.
            #
            # The order is conda's own activation order, verified by reading
            # what `micromamba run` puts on PATH, and it is deliberate rather
            # than alphabetical: `Library\mingw-w64\bin` must precede
            # `Library\bin`, because both can hold a copy of the same runtime
            # DLL and Windows takes the first match. Using a different order
            # here than conda uses is how one process ends up with two
            # toolchains' DLLs and the "32 bit pseudo relocation out of range"
            # failure. `Scripts` was missing altogether.
            dirs.extend(
                [
                    conda_prefix,
                    conda_prefix / "Library" / "mingw-w64" / "bin",
                    conda_prefix / "Library" / "usr" / "bin",
                    conda_prefix / "Library" / "bin",
                    conda_prefix / "Scripts",
                    conda_prefix / "bin",
                ]
            )
    else:
        dirs.extend([r_home / "lib", r_home / "bin"])
        if conda_prefix is not None:
            dirs.append(conda_prefix / "lib")

    seen: set[Path] = set()
    ordered: list[Path] = []
    for d in dirs:
        if d.is_dir() and d not in seen:
            seen.add(d)
            ordered.append(d)
    return tuple(ordered)


def validate_r_home(
    path: Path | str,
    *,
    probe: Probe | None = None,
    source: str = "unknown",
    min_version: tuple[int, int, int] = MIN_R_VERSION,
    check_arch: bool = True,
) -> RHomeInfo:
    """Validate a candidate ``R_HOME`` and describe it.

    Parameters
    ----------
    path : Path or str
        Candidate R installation root.
    probe : Probe, optional
        Host snapshot. Defaults to the running process.
    source : str, optional
        Discovery rung identifier, recorded on the result.
    min_version : tuple, optional
        Minimum acceptable R version.
    check_arch : bool, optional
        Set False only for reporting on an R we will not load.

    Returns
    -------
    RHomeInfo

    Raises
    ------
    InvalidRHomeError
        The path is not an R installation, or its shared library is missing.
    RTooOldError
        R is older than ``min_version``.
    ArchMismatchError
        R's architecture differs from this interpreter's.
    """
    probe = probe or Probe.current()
    r_home = Path(path).expanduser()

    if not r_home.is_dir():
        raise InvalidRHomeError(
            f"Not a directory: {r_home}",
            detail="Expected the R installation root.",
        )

    version_info = read_r_version(r_home)
    if version_info is None:
        raise InvalidRHomeError(
            f"{r_home} does not look like an R installation.",
            detail=(
                "Expected to find library/base/DESCRIPTION with a Version: line. "
                "This is usually a leftover directory on PATH, or R_HOME pointing "
                "at a bin/ subdirectory rather than the installation root."
            ),
        )
    version, version_string = version_info

    if not (r_home / "etc").is_dir():
        raise InvalidRHomeError(
            f"{r_home} has library/base but no etc/ - the installation looks incomplete.",
        )

    if version < min_version:
        want = ".".join(str(p) for p in min_version)
        raise RTooOldError(
            f"R {version_string} at {r_home} is too old; {want} or newer is required.",
        )

    shared_lib, reason = find_shared_lib(r_home, probe)
    if shared_lib is None:
        raise InvalidRHomeError(
            f"R at {r_home} has no loadable shared library: {reason}.",
            detail=(
                "rpy2 loads this library directly, so R cannot be used without it. "
                "A partially removed or relocated R install is the usual cause."
            ),
        )

    arch = probe_arch(shared_lib)
    if check_arch and arch != ARCH_UNKNOWN and arch != probe.arch:
        raise ArchMismatchError(
            f"R at {r_home} is {arch}, but this Python is {probe.arch}.",
            detail=(
                f"Shared library: {shared_lib}\n"
                "Loading it would terminate the Python process, so it was skipped."
            ),
        )

    conda_prefix = _conda_prefix_of(r_home)
    return RHomeInfo(
        path=r_home,
        version=version,
        version_string=version_string,
        arch=arch,
        shared_lib=shared_lib,
        bin_dirs=_bin_dirs_for(r_home, shared_lib, probe, conda_prefix),
        source=source,
        conda_prefix=conda_prefix,
    )


__all__ = [
    "MIN_R_VERSION",
    "RHomeInfo",
    "find_shared_lib",
    "probe_arch",
    "read_r_version",
    "validate_r_home",
]
