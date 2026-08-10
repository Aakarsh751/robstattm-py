"""Host-environment probe — the seam that makes discovery testable.

Every platform-dependent fact the discovery chain needs (OS, CPU, environment
variables, ``PATH`` lookups, the user's home directory) is read through a
:class:`Probe` rather than from :mod:`os`/:mod:`sys`/:mod:`platform` directly.

Production code calls :meth:`Probe.current`. Tests construct a synthetic
``Probe`` describing, say, "32-bit Python on Windows with a broken R on PATH"
and assert the resulting discovery order — with no monkeypatching of
``sys.platform``, which is unreliable and leaks between tests.
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

# Normalised architecture names. These are ours, not any vendor's spelling;
# `subdir()` and the binary-header probe both map onto this vocabulary.
ARCH_X86_64 = "x86_64"
ARCH_ARM64 = "arm64"
ARCH_I386 = "i386"
ARCH_PPC64LE = "ppc64le"
ARCH_UNKNOWN = "unknown"

_MACHINE_ALIASES: dict[str, str] = {
    "amd64": ARCH_X86_64,
    "x86_64": ARCH_X86_64,
    "x64": ARCH_X86_64,
    "em64t": ARCH_X86_64,
    "arm64": ARCH_ARM64,
    "aarch64": ARCH_ARM64,
    "armv8": ARCH_ARM64,
    "i386": ARCH_I386,
    "i486": ARCH_I386,
    "i586": ARCH_I386,
    "i686": ARCH_I386,
    "x86": ARCH_I386,
    "ppc64le": ARCH_PPC64LE,
    "powerpc64le": ARCH_PPC64LE,
}


def normalise_machine(machine: str) -> str:
    """Map a :func:`platform.machine` string onto our architecture vocabulary.

    Parameters
    ----------
    machine : str
        Raw machine string, e.g. ``"AMD64"``, ``"x86_64"``, ``"arm64"``.

    Returns
    -------
    str
        One of ``"x86_64"``, ``"arm64"``, ``"i386"``, ``"ppc64le"``, or
        ``"unknown"``.

    Examples
    --------
    >>> normalise_machine("AMD64")
    'x86_64'
    >>> normalise_machine("aarch64")
    'arm64'
    >>> normalise_machine("s390x")
    'unknown'
    """
    return _MACHINE_ALIASES.get(machine.strip().lower(), ARCH_UNKNOWN)


@dataclass(frozen=True, slots=True)
class Probe:
    """A snapshot of the host facts that R discovery depends on.

    Attributes
    ----------
    system : str
        ``"Windows"``, ``"Darwin"``, or ``"Linux"`` (:func:`platform.system`).
    machine : str
        Raw :func:`platform.machine` string. Use :attr:`arch` for the
        normalised form.
    is_64bit : bool
        Whether the *Python interpreter* is 64-bit. On Windows this
        distinguishes ``bin/x64`` from ``bin/i386``.
    environ : Mapping[str, str]
        Environment variables.
    which : Callable[[str], str | None]
        ``PATH`` lookup, defaulting to :func:`shutil.which`.
    home : Path
        The user's home directory.
    sys_prefix : Path
        ``sys.prefix`` — the active Python environment root, which may itself
        be a conda prefix containing R.
    registry_installs : callable, optional
        Returns ``(install_path, label)`` for every R recorded in the Windows
        registry. ``None`` means "read the real registry". Tests inject a stub,
        because the registry is process-global and would otherwise leak the
        host's actual R installations into synthetic scenarios.
    """

    system: str
    machine: str
    is_64bit: bool
    environ: Mapping[str, str]
    which: Callable[[str], str | None] = field(default=shutil.which)
    home: Path = field(default_factory=Path.home)
    sys_prefix: Path = field(default_factory=lambda: Path(sys.prefix))
    registry_installs: Callable[[], list[tuple[Path, str]]] | None = None

    @classmethod
    def current(cls) -> Probe:
        """Return a :class:`Probe` describing the running process."""
        return cls(
            system=platform.system(),
            machine=platform.machine(),
            is_64bit=sys.maxsize > 2**32,
            environ=dict(os.environ),
            which=shutil.which,
            home=Path.home(),
            sys_prefix=Path(sys.prefix),
            registry_installs=None,
        )

    # -- derived properties -------------------------------------------------

    @property
    def arch(self) -> str:
        """Normalised host architecture.

        Falls back to ``i386`` when a 32-bit interpreter reports an x86_64
        machine — a 32-bit Python can only load a 32-bit R, regardless of what
        the CPU is capable of.
        """
        arch = normalise_machine(self.machine)
        if arch == ARCH_X86_64 and not self.is_64bit:
            return ARCH_I386
        return arch

    @property
    def is_windows(self) -> bool:
        """True on Windows."""
        return self.system == "Windows"

    @property
    def is_macos(self) -> bool:
        """True on macOS."""
        return self.system == "Darwin"

    @property
    def is_linux(self) -> bool:
        """True on Linux."""
        return self.system == "Linux"

    @property
    def shared_lib_name(self) -> str:
        """Filename of R's shared library on this platform."""
        if self.is_windows:
            return "R.dll"
        if self.is_macos:
            return "libR.dylib"
        return "libR.so"

    @property
    def subdir(self) -> str:
        """The conda platform identifier for this host, e.g. ``"win-64"``.

        Returns ``"unknown"`` for platforms conda-forge does not build for; the
        provisioning path refuses to run rather than guessing.
        """
        arch = self.arch
        if self.is_windows:
            return "win-64" if arch == ARCH_X86_64 else "unknown"
        if self.is_macos:
            if arch == ARCH_ARM64:
                return "osx-arm64"
            return "osx-64" if arch == ARCH_X86_64 else "unknown"
        if self.is_linux:
            return {
                ARCH_X86_64: "linux-64",
                ARCH_ARM64: "linux-aarch64",
                ARCH_PPC64LE: "linux-ppc64le",
            }.get(arch, "unknown")
        return "unknown"


#: conda-forge platforms this package supports provisioning on.
SUPPORTED_SUBDIRS: tuple[str, ...] = (
    "linux-64",
    "linux-aarch64",
    "linux-ppc64le",
    "osx-64",
    "osx-arm64",
    "win-64",
)

#: Subdirs for which conda-forge has no ``r-robstattm`` / ``r-pyinit`` build,
#: so provisioning must fall back to building those two from source.
#: Verified against the conda-forge API on 2026-07-30.
SOURCE_BUILD_SUBDIRS: frozenset[str] = frozenset({"osx-arm64"})


__all__ = [
    "ARCH_ARM64",
    "ARCH_I386",
    "ARCH_PPC64LE",
    "ARCH_UNKNOWN",
    "ARCH_X86_64",
    "SOURCE_BUILD_SUBDIRS",
    "SUPPORTED_SUBDIRS",
    "Probe",
    "normalise_machine",
]
