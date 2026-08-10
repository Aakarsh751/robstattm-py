"""Filesystem layout for the package-private R environment.

Everything robstattm-py owns lives under a single root, so ``robstattm-py
uninstall`` can remove it all and nothing outside it is ever touched::

    <root>/
      bin/micromamba[.exe]     the provisioning launcher
      pkgs/                    conda package cache (survives a failed setup)
      envs/r/                  the private R environment
      rlibs/<R minor>/<subdir>/  R packages conda-forge does not ship
      logs/                    setup-<timestamp>.log
      state.json               what is provisioned, and from which spec
      .lock                    held for the duration of a setup

The root defaults to the platform user-data directory and is overridable with
``ROBSTATTM_HOME`` — needed when the default path contains a space or
non-ASCII character (both common on Windows, where the default contains the
username), or when the user's home directory is on a small or network drive.

**Nothing in this module creates directories.** Path construction is pure so
that ``import robstattm_py`` and ``robstattm-py info`` are side-effect free;
callers that actually write must call :func:`ensure_dir` explicitly.
"""
from __future__ import annotations

import os
from pathlib import Path

from robstattm_py._renv.probe import Probe

#: Environment variable overriding the root of the private environment.
ENV_HOME = "ROBSTATTM_HOME"

#: Application name used for the platform user-data directory.
APP_NAME = "robstattm-py"


def root(probe: Probe | None = None) -> Path:
    """Return the root directory of the package-private R environment.

    Honours ``ROBSTATTM_HOME`` when set and non-empty; otherwise uses the
    platform user-data directory (``%LOCALAPPDATA%\\robstattm-py`` on Windows,
    ``~/Library/Application Support/robstattm-py`` on macOS,
    ``$XDG_DATA_HOME/robstattm-py`` or ``~/.local/share/robstattm-py`` on
    Linux).

    Parameters
    ----------
    probe : Probe, optional
        Host snapshot. Defaults to the running process.

    Returns
    -------
    Path
        Absolute path. Not created.
    """
    probe = probe or Probe.current()
    override = probe.environ.get(ENV_HOME, "").strip()
    if override:
        return Path(override).expanduser().absolute()

    # platformdirs is a hard dependency, but fall back rather than fail if a
    # minimal install is missing it — the fallback matches its own conventions.
    try:
        from platformdirs import user_data_dir
    except ImportError:  # pragma: no cover - platformdirs is a declared dep
        return _fallback_data_dir(probe)
    return Path(user_data_dir(APP_NAME, appauthor=False)).absolute()


def _fallback_data_dir(probe: Probe) -> Path:
    """Reproduce platformdirs' user-data directory without the dependency."""
    if probe.is_windows:
        base = probe.environ.get("LOCALAPPDATA") or str(probe.home / "AppData" / "Local")
        return Path(base) / APP_NAME
    if probe.is_macos:
        return probe.home / "Library" / "Application Support" / APP_NAME
    base = probe.environ.get("XDG_DATA_HOME") or str(probe.home / ".local" / "share")
    return Path(base) / APP_NAME


#: Longest path we have observed *inside* the package cache, relative to the
#: root. conda-forge's ``mingw-w64-ucrt-x86_64-headers`` (a dependency of
#: ``r-base`` on Windows) contains Windows SDK headers with very long names, and
#: micromamba stores them under a URL-shaped cache path::
#:
#:   pkgs\https\conda.anaconda.org\conda-forge\noarch\<pkg>-<version>-<build>\
#:       Library\x86_64-w64-mingw32\sysroot\usr\include\
#:       windows.security.exchangeactivesyncprovisioning.h
#:
#: Measured at 215 characters on 2026-08-10.
DEEPEST_INTERNAL_PATH = 215

#: Windows refuses paths longer than this unless long-path support is enabled.
WINDOWS_MAX_PATH = 260


def max_safe_root_length() -> int:
    """Longest root directory that still fits inside Windows' path limit."""
    return WINDOWS_MAX_PATH - DEEPEST_INTERNAL_PATH


def windows_long_paths_enabled() -> bool:
    """True when Windows has been configured to allow paths over 260 characters.

    Off by default on Windows, and turning it on needs administrator rights, so
    we cannot rely on it - we size the install path to fit without it.
    """
    try:
        import winreg
    except ImportError:  # pragma: no cover - non-Windows
        return True
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
            return bool(value)
    except OSError:
        return False


def env_prefix(probe: Probe | None = None) -> Path:
    """Return the conda prefix holding the private R."""
    return root(probe) / "envs" / "r"


def mamba_root(probe: Probe | None = None) -> Path:
    """Return the value to use for ``MAMBA_ROOT_PREFIX``.

    Points at our root so the package cache lands in ``<root>/pkgs`` and never
    in the user's own ``~/micromamba`` or conda installation.
    """
    return root(probe)


def pkgs_dir(probe: Probe | None = None) -> Path:
    """Return the conda package cache directory.

    Deliberately preserved across a failed or forced re-``setup``: rebuilding
    the environment from a warm cache takes seconds rather than minutes.
    """
    return root(probe) / "pkgs"


def bin_dir(probe: Probe | None = None) -> Path:
    """Return the directory holding the micromamba launcher."""
    return root(probe) / "bin"


def micromamba_exe(probe: Probe | None = None) -> Path:
    """Return the path to the micromamba binary (whether or not it exists)."""
    probe = probe or Probe.current()
    name = "micromamba.exe" if probe.is_windows else "micromamba"
    return bin_dir(probe) / name


def rlib_dir(r_minor: str, subdir: str, probe: Probe | None = None) -> Path:
    """Return the private R library for a given R minor version and platform.

    Parameters
    ----------
    r_minor : str
        R's major.minor version, e.g. ``"4.5"``.
    subdir : str
        conda platform identifier, e.g. ``"win-64"``.

    Notes
    -----
    Keying on **both** R minor and platform is required, not tidiness: compiled
    R packages are ABI-incompatible across R minor versions, and loading a
    package built for 4.4 into 4.5 segfaults the interpreter rather than
    raising. :func:`robstattm_py._renv.rlibs.wire` refuses to add a library
    whose stamp does not match the R actually in use.
    """
    return root(probe) / "rlibs" / r_minor / subdir


def log_dir(probe: Probe | None = None) -> Path:
    """Return the directory holding setup logs."""
    return root(probe) / "logs"


def state_file(probe: Probe | None = None) -> Path:
    """Return the path of the provisioning state file."""
    return root(probe) / "state.json"


def lock_file(probe: Probe | None = None) -> Path:
    """Return the path of the setup lock file."""
    return root(probe) / ".lock"


def provisioned_r_home(probe: Probe | None = None) -> Path:
    """Return where R lives inside the provisioned conda prefix.

    conda-forge keeps the ``lib/R`` layout on every platform, Windows included
    (where ``R.dll`` then sits in ``lib/R/bin/x64``).
    """
    return env_prefix(probe) / "lib" / "R"


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if absent and return it.

    The single place in this module that touches the filesystem.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_within_root(path: Path, probe: Probe | None = None) -> bool:
    """Return True if ``path`` is inside our root directory.

    Guard for every destructive operation in ``uninstall``: we only ever delete
    things we created.
    """
    try:
        resolved = path.absolute()
        base = root(probe).absolute()
    except OSError:  # pragma: no cover - pathological filesystem state
        return False
    return resolved == base or base in resolved.parents


def describe_env_vars() -> dict[str, str]:
    """Return the environment variables this package reads, with descriptions.

    Surfaced by ``robstattm-py info`` so users can see every knob in one place
    instead of hunting through documentation.
    """
    return {
        ENV_HOME: "Root directory for the private R environment and caches.",
        "ROBSTATTM_R_HOME": "Use this exact R installation; skip all auto-detection.",
        "ROBSTATTM_R_MODE": "auto (default), provisioned, or system.",
        "ROBSTATTM_NO_PROVISION": "Set to 1 to forbid provisioning (used by the test suite).",
        "ROBSTATTM_AUTO_SETUP": "Set to 1 to allow provisioning on first import.",
        "R_HOME": "Standard R variable; honoured if ROBSTATTM_R_HOME is unset.",
        "RPY2_CFFI_MODE": "Set to ABI by us when rpy2's compiled module mismatches R.",
        "RPM_VERBOSE": "Set to 1 to print a line when the R session starts.",
    }


def current_root_env() -> str | None:
    """Return the raw ``ROBSTATTM_HOME`` value, or None when unset."""
    value = os.environ.get(ENV_HOME, "").strip()
    return value or None


__all__ = [
    "APP_NAME",
    "ENV_HOME",
    "bin_dir",
    "current_root_env",
    "describe_env_vars",
    "ensure_dir",
    "env_prefix",
    "is_within_root",
    "lock_file",
    "log_dir",
    "mamba_root",
    "micromamba_exe",
    "pkgs_dir",
    "provisioned_r_home",
    "rlib_dir",
    "root",
    "state_file",
]
