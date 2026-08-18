"""R environment management: discovery, activation, and provisioning.

The public entry point is :func:`ensure_r_environment`, called once from
``robstattm_py._r._install_conversion`` immediately before rpy2 is imported.

Design constraint worth keeping in mind when editing anything here: **importing
robstattm_py must stay free of side effects.** No network access, no directory
creation, no subprocesses, and above all no provisioning. A user who types
``import robstattm_py`` on a machine without R gets a clear exception telling
them to run ``robstattm-py setup``, they do not get a silent multi-gigabyte
install.
``tests/renv/test_no_import_side_effects.py`` enforces this in a subprocess.
"""
from __future__ import annotations

import threading

from robstattm_py._renv import activate, paths
from robstattm_py._renv.discovery import (
    DiscoveryResult,
    discover,
    rpy2_already_loaded_r_home,
)
from robstattm_py._renv.errors import (
    ArchMismatchError,
    InvalidRHomeError,
    NoRFoundError,
    RenvError,
    RPackagesMissingError,
    RpyAlreadyLoadedError,
    RTooOldError,
)
from robstattm_py._renv.probe import Probe
from robstattm_py._renv.validate import RHomeInfo, validate_r_home

#: Set to "1" to forbid provisioning outright (used by the test suite).
ENV_NO_PROVISION = "ROBSTATTM_NO_PROVISION"

#: Set to "1" to opt in to provisioning R automatically on first use.
ENV_AUTO_SETUP = "ROBSTATTM_AUTO_SETUP"

_lock = threading.Lock()
_resolved: RHomeInfo | None = None


def ensure_r_environment(
    *,
    allow_provision: bool = False,
    probe: Probe | None = None,
) -> RHomeInfo:
    """Resolve, validate and activate an R installation for this process.

    Memoised: the search runs once per process. Safe to call from multiple
    threads, though R itself remains a singleton.

    Parameters
    ----------
    allow_provision : bool, optional
        Reserved for the CLI. Provisioning is never triggered from an ordinary
        import; see the module docstring.
    probe : Probe, optional
        Host snapshot, for tests.

    Returns
    -------
    RHomeInfo
        The activated R.

    Raises
    ------
    NoRFoundError
        Nothing usable was found. The exception carries the full discovery
        trace, listing every location checked and why each was rejected.
    RpyAlreadyLoadedError
        rpy2 is already bound to a different R, which cannot be undone within
        this process.
    """
    global _resolved
    with _lock:
        if _resolved is not None:
            return _resolved

        probe = probe or Probe.current()

        # If rpy2 is already up, its R wins - the binding is immutable at this
        # point, so the only honest options are to agree or to say so plainly.
        already = rpy2_already_loaded_r_home()

        result = discover(probe=probe)
        info = result.info

        if already:
            info = _reconcile_with_loaded_rpy2(already, info, probe)
        elif info is None:
            _raise_not_found(result, probe, allow_provision=allow_provision)

        assert info is not None  # narrowed by the branches above
        activate.apply(info, private_lib=_existing_private_lib(info, probe))
        _resolved = info
        return info


def _reconcile_with_loaded_rpy2(
    already: str,
    discovered: RHomeInfo | None,
    probe: Probe,
) -> RHomeInfo:
    """Reconcile our choice of R with one rpy2 has already loaded."""
    from pathlib import Path

    loaded_path = Path(already)
    if discovered is not None and discovered.path == loaded_path:
        return discovered

    try:
        loaded_info = validate_r_home(
            loaded_path, probe=probe, source="rpy2-preloaded", check_arch=False
        )
    except RenvError:
        loaded_info = None

    if discovered is None:
        if loaded_info is not None:
            return loaded_info
        raise RpyAlreadyLoadedError(
            f"rpy2 is already loaded against {already}, which does not validate "
            "as a usable R installation.",
        )

    raise RpyAlreadyLoadedError(
        f"rpy2 was already initialised against R at {already}, but robstattm_py "
        f"selected {discovered.path}.",
        detail=(
            "rpy2 resolves R_HOME when it is first imported, so the choice "
            "cannot be changed afterwards in this process."
        ),
    )


def _raise_not_found(result: DiscoveryResult, probe: Probe, *, allow_provision: bool) -> None:
    """Raise :class:`NoRFoundError` with the discovery trace and a tailored remedy."""
    no_provision = probe.environ.get(ENV_NO_PROVISION, "") == "1"
    # On Windows (and often elsewhere) pip drops the `robstattm-py` script into a
    # Scripts/ directory that is not on PATH, so the command in the remedy fails
    # for exactly the user who most needs it. The module form always works.
    path_independent = (
        "\n  If `robstattm-py` is not recognised as a command (common on "
        "Windows, where pip may install it off PATH), use the identical\n  "
        "`python -m robstattm_py.cli setup` instead."
    )
    if no_provision:
        remedy = (
            "Provisioning is disabled by ROBSTATTM_NO_PROVISION=1. Install R and "
            "set R_HOME, or unset that variable and run `robstattm-py setup`."
            + path_independent
        )
    elif probe.subdir == "unknown":
        remedy = (
            f"Install R yourself and set R_HOME - this platform "
            f"({probe.system}/{probe.machine}) is not one robstattm-py can "
            "provision R for automatically."
        )
    else:
        remedy = (
            "Run `robstattm-py setup` to download a private R (about 400 MB, "
            "a few minutes), or install R yourself and set R_HOME."
            + path_independent
        )
    raise NoRFoundError(
        "No usable R installation was found.",
        detail="Locations checked:\n" + result.render_trace(),
        remedy=remedy,
    )


def _existing_private_lib(info: RHomeInfo, probe: Probe):
    """Return the private R library for this R, when one has been created."""
    subdir = probe.subdir
    if subdir == "unknown":
        return None
    candidate = paths.rlib_dir(info.minor, subdir, probe)
    return candidate if candidate.is_dir() else None


def r_home_info() -> RHomeInfo | None:
    """Return the resolved R without triggering a search.

    Cheap and side-effect free, returns ``None`` if nothing has resolved R
    yet. Use :func:`ensure_r_environment` when you actually need R.
    """
    return _resolved


def discover_only(probe: Probe | None = None) -> DiscoveryResult:
    """Run discovery for reporting purposes, changing nothing.

    Used by ``robstattm-py doctor``, which must be able to explain a failing
    environment without modifying it.
    """
    return discover(probe=probe)


def reset_for_tests() -> None:
    """Clear memoised state. Test-support only."""
    global _resolved
    _resolved = None
    activate.reset_for_tests()


__all__ = [
    "ENV_AUTO_SETUP",
    "ENV_NO_PROVISION",
    "ArchMismatchError",
    "DiscoveryResult",
    "InvalidRHomeError",
    "NoRFoundError",
    "Probe",
    "RHomeInfo",
    "RPackagesMissingError",
    "RTooOldError",
    "RenvError",
    "RpyAlreadyLoadedError",
    "discover_only",
    "ensure_r_environment",
    "paths",
    "r_home_info",
    "reset_for_tests",
    "validate_r_home",
]
