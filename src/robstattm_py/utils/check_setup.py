"""Environment diagnostics.

Prints a one-screen status table of the R + Python + CRAN-package versions and
returns ``True`` if all *core* packages are available, ``False`` otherwise.
See ``docs/user_interface.md §8``.

``robstattm-py doctor`` reports the same facts in more depth (including the
R-discovery trace). This function stays because it is public API and works from
inside a notebook, where shelling out is awkward.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

# Single source of truth, shared with `robstattm-py doctor`:
#   core     -- the wrappers cannot work without these
#   stretch  -- pense / gse / tsgs only
#   optional -- example-script reproduction (D-024); `robcbi` also needs the
#               Fortran package `robeth`.
from robstattm_py._renv.report import (
    CORE_R_PACKAGES,
    OPTIONAL_R_PACKAGES,
    STRETCH_R_PACKAGES,
    install_hint,
    rpy2_version,
)


def _stdout_supports_unicode() -> bool:
    """True if ``sys.stdout`` can encode the check-mark glyphs.

    The Windows default console encoding (cp1252) raises on U+2713/U+2717,
    making ``check_setup()`` crash mid-print.  We probe ``stdout.encoding``
    instead of catching the exception so the report stays clean either
    way.
    """
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "✓✗⚠".encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


@dataclass(frozen=True, slots=True)
class _PackageStatus:
    name: str
    version: str | None  # None = not installed
    is_core: bool


def _check_r_package(name: str) -> str | None:
    """Return version string if installed, None otherwise."""
    from robstattm_py._r import r

    rr = r().r
    try:
        v = rr(f"tryCatch(as.character(packageVersion('{name}')), error=function(e) NA_character_)")
        s = v[0] if len(v) else None
        if s is None or (isinstance(s, str) and s == "NA"):
            return None
        return str(s)
    except Exception:
        return None


def check_setup(*, verbose: bool = True) -> bool:
    """Diagnose the RobStatTM-Py runtime environment.

    Parameters
    ----------
    verbose : bool, default True
        Print a status report. Set False to suppress output.

    Returns
    -------
    bool
        True if all *core* CRAN packages are installed, False otherwise.

    Examples
    --------
    >>> import robstattm_py
    >>> robstattm_py.check_setup(verbose=False)  # doctest: +SKIP
    True
    """
    from robstattm_py import __version__ as package_version
    from robstattm_py._r import r

    lines: list[str] = ["RobStatTM-Py setup check", "=" * 24]
    lines.append(f"Python:       {sys.version.split()[0]}")
    lines.append(f"robstattm_py: {package_version}")

    # Read from package metadata, not `rpy2.__version__`: rpy2 3.6 removed that
    # attribute, so the old attribute lookup reported "unknown" on every
    # current install.
    rpy2_ver = rpy2_version()
    lines.append(f"rpy2:         {rpy2_ver if rpy2_ver else '(missing)'}")

    try:
        rver = r().r("R.version.string")[0]
    except Exception as e:
        if verbose:
            print("\n".join(lines))
            print(f"R:            (cannot start - {e})")
        return False
    lines.append(f"R:            {rver}")

    statuses: list[_PackageStatus] = []
    for pkg in CORE_R_PACKAGES:
        statuses.append(_PackageStatus(pkg, _check_r_package(pkg), is_core=True))
    for pkg in STRETCH_R_PACKAGES + OPTIONAL_R_PACKAGES:
        statuses.append(_PackageStatus(pkg, _check_r_package(pkg), is_core=False))

    # Use unicode marks when the terminal supports it; ASCII otherwise.
    # Windows cp1252 consoles crash on U+2713 (✓), U+2717 (✗), U+26A0 (⚠).
    use_unicode = _stdout_supports_unicode()
    ok_mark = "✓" if use_unicode else "[OK]"
    bad_mark = "✗" if use_unicode else "[MISSING]"
    warn_mark = "⚠" if use_unicode else "[WARN]"

    # Width driven by the longest name actually being reported, so a new package
    # cannot silently break the alignment (`robustvarComp` is 13 characters and
    # used to overflow a hardcoded 12).
    name_width = max(len(s.name) for s in statuses)

    for s in statuses:
        if s.version is None:
            mark = bad_mark if s.is_core else warn_mark
            label = "(not installed)" + ("" if s.is_core else "  stretch wrappers unavailable")
            lines.append(f"  {s.name:<{name_width}}  {label:<30}  {mark}")
        else:
            lines.append(f"  {s.name:<{name_width}}  {s.version:<30}  {ok_mark}")

    missing_core = [s.name for s in statuses if s.is_core and s.version is None]
    missing_stretch = [s.name for s in statuses if not s.is_core and s.version is None]

    # The install command depends on whether R was provisioned by us (in which
    # case there is no R console for the user to type into).
    from robstattm_py._renv import r_home_info

    info = r_home_info()

    if missing_core:
        lines.append("")
        lines.append("Missing CORE packages:")
        lines.append("  " + install_hint(missing_core, info).replace("\n", "\n  "))
    if missing_stretch:
        lines.append("")
        lines.append("Optional packages - install them if you want those wrappers:")
        lines.append("  " + install_hint(missing_stretch, info).replace("\n", "\n  "))
        if "robcbi" in missing_stretch:
            lines.append(
                "  # robcbi needs the Fortran package 'robeth' (Rtools on Windows); "
                "both are CRAN-archived - see docs/guides/external.md"
            )

    # ASCII hyphens, not em dashes: this report is routinely read on a Windows
    # cp1252 console, where a U+2014 renders as a replacement character. The
    # status glyphs above already fall back; these lines used to be missed.
    lines.append("")
    if missing_core:
        lines.append("Result: NOT READY - core packages missing.")
    elif missing_stretch:
        lines.append("Result: READY for core wrappers. STRETCH WRAPPERS UNAVAILABLE.")
    else:
        lines.append("Result: READY - all core and stretch packages installed.")

    if verbose:
        print("\n".join(lines))
    return not missing_core
