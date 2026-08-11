"""Apply a discovered R to the current process, before rpy2 loads it.

This module is where the Windows ``LoadLibrary failure: The specified module
could not be found`` class of failure is actually fixed, so the reasoning is
worth recording.

rpy2 does two things at ``rpy2.rinterface_lib.openrlib`` import time: it
resolves ``R_HOME``, and it adds **one** directory to the DLL search path via
:func:`os.add_dll_directory`. That is not enough. ``add_dll_directory`` only
influences resolution for libraries loaded through Python's own loader with
``LOAD_LIBRARY_SEARCH_*`` flags — but once R is running, ``library(stats)``
performs a plain ``LoadLibrary("stats.dll")`` from inside R, and *that* search
order consults ``PATH`` and ignores the added directories entirely. R's own
DLLs also link against runtime libraries (OpenBLAS, gfortran, zlib) that, in a
conda layout, live several directories away from ``R.dll``.

So :func:`apply` registers **every** relevant directory through **both**
mechanisms: ``os.add_dll_directory`` *and* a ``PATH`` prefix.

The other half of the job is ordering: everything here must happen before
``rpy2.robjects`` is imported for the first time. :func:`apply` is called from
``robstattm_py._r._install_conversion``, immediately before that import.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from robstattm_py._renv.validate import RHomeInfo

# Handles returned by os.add_dll_directory must be kept alive: the directory is
# removed from the search path when the handle is garbage-collected.
_dll_handles: list[object] = []

# The R this process has been configured for. Applying twice is a no-op.
_applied: RHomeInfo | None = None


def applied() -> RHomeInfo | None:
    """Return the R this process has been activated against, if any."""
    return _applied


def reset_for_tests() -> None:
    """Forget the applied state. Test-support only."""
    global _applied
    _applied = None
    _dll_handles.clear()


def apply(info: RHomeInfo, *, private_lib: Path | None = None) -> RHomeInfo:
    """Configure the process environment to load ``info``'s R.

    Idempotent: calling it again with the same R does nothing. Calling it with
    a *different* R after rpy2 has already loaded one cannot work, and is
    rejected by the caller (``_r.ensure_r_environment``) rather than silently
    producing a mixed configuration.

    Parameters
    ----------
    info : RHomeInfo
        A validated R installation.
    private_lib : Path, optional
        A directory to prepend to ``R_LIBS``.

    Returns
    -------
    RHomeInfo
        The argument, for convenient chaining.
    """
    global _applied
    if _applied is not None and _applied.path == info.path:
        return _applied

    os.environ["R_HOME"] = str(info.path)
    _register_search_dirs(info)

    if private_lib is not None:
        prepend_r_libs(private_lib)

    if info.conda_prefix is not None:
        # A user's ~/.Renviron can redirect R_LIBS_USER or R_PROFILE at a
        # library built for a different R. For an environment we provisioned we
        # want a predictable, self-contained R.
        os.environ.setdefault("R_ENVIRON_USER", "")
        os.environ.pop("R_ARCH", None)

    _applied = info
    return info


def _register_search_dirs(info: RHomeInfo) -> None:
    """Put R's library directories on both Windows DLL search mechanisms."""
    if sys.platform == "win32":
        for directory in info.bin_dirs:
            if not directory.is_dir():
                continue
            add = getattr(os, "add_dll_directory", None)
            if add is not None:
                try:
                    _dll_handles.append(add(str(directory)))
                except OSError:
                    # Non-fatal: the PATH entry below usually suffices.
                    pass
        _prepend_path([d for d in info.bin_dirs if d.is_dir()])
    else:
        # On POSIX the dynamic loader path is fixed at process start, so
        # LD_LIBRARY_PATH cannot usefully be changed here; conda and system R
        # builds both encode an rpath. PATH still matters for Rscript and for
        # R's own child processes.
        _prepend_path([d for d in info.bin_dirs if d.is_dir()])


def _prepend_path(directories: list[Path]) -> None:
    """Prepend directories to ``PATH``, preserving order and avoiding repeats."""
    if not directories:
        return
    current = os.environ.get("PATH", "")
    existing = {p.lower() for p in current.split(os.pathsep) if p}
    additions = [str(d) for d in directories if str(d).lower() not in existing]
    if not additions:
        return
    os.environ["PATH"] = os.pathsep.join(additions) + (os.pathsep + current if current else "")


def prepend_r_libs(library: Path) -> None:
    """Prepend a directory to ``R_LIBS``.

    ``R_LIBS`` is used deliberately in preference to ``R_LIBS_USER``. R
    *appends* ``R_LIBS`` entries ahead of the default library set, whereas
    setting ``R_LIBS_USER`` **replaces** the user's personal library — which
    would silently hide packages they installed themselves. Since our directory
    ends up first on ``.libPaths()``, a bare ``install.packages()`` inside the
    embedded session also defaults to it, so the user's system library is
    protected by construction rather than by convention.
    """
    entry = str(library)
    current = os.environ.get("R_LIBS", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if any(p.lower() == entry.lower() for p in parts):
        return
    os.environ["R_LIBS"] = os.pathsep.join([entry, *parts])


__all__ = [
    "apply",
    "applied",
    "prepend_r_libs",
    "reset_for_tests",
]
