"""Environment diagnostics.

Prints a one-screen status table of the R + Python + CRAN-package versions and
returns ``True`` if all *core* packages are available, ``False`` otherwise.
See ``docs/user_interface.md §8``.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

CORE_R_PACKAGES = ("RobStatTM", "robustbase", "rrcov", "pyinit")
STRETCH_R_PACKAGES = ("pense", "GSE")


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
    from robstatm_py._r import r

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
    >>> import robstatm_py
    >>> robstatm_py.check_setup(verbose=False)  # doctest: +SKIP
    True
    """
    from robstatm_py import __version__ as PYVER
    from robstatm_py._r import r

    lines: list[str] = ["RobStatTM-Py setup check", "=" * 24]
    lines.append(f"Python:       {sys.version.split()[0]}")
    lines.append(f"robstatm_py:  {PYVER}")

    try:
        import rpy2

        rpy2_ver = getattr(rpy2, "__version__", "unknown")
    except ImportError:
        rpy2_ver = None
    lines.append(f"rpy2:         {rpy2_ver if rpy2_ver else '(missing)'}")

    try:
        rver = r().r("R.version.string")[0]
    except Exception as e:
        if verbose:
            print("\n".join(lines))
            print(f"R:            (cannot start — {e})")
        return False
    lines.append(f"R:            {rver}")

    statuses: list[_PackageStatus] = []
    for pkg in CORE_R_PACKAGES:
        statuses.append(_PackageStatus(pkg, _check_r_package(pkg), is_core=True))
    for pkg in STRETCH_R_PACKAGES:
        statuses.append(_PackageStatus(pkg, _check_r_package(pkg), is_core=False))

    # Use unicode marks when the terminal supports it; ASCII otherwise.
    # Windows cp1252 consoles crash on U+2713 (✓), U+2717 (✗), U+26A0 (⚠).
    use_unicode = _stdout_supports_unicode()
    ok_mark = "✓" if use_unicode else "[OK]"
    bad_mark = "✗" if use_unicode else "[MISSING]"
    warn_mark = "⚠" if use_unicode else "[WARN]"

    for s in statuses:
        if s.version is None:
            mark = bad_mark if s.is_core else warn_mark
            label = "(not installed)" + ("" if s.is_core else "  stretch wrappers unavailable")
            lines.append(f"  {s.name:<12}  {label:<30}  {mark}")
        else:
            lines.append(f"  {s.name:<12}  {s.version:<30}  {ok_mark}")

    missing_core = [s.name for s in statuses if s.is_core and s.version is None]
    missing_stretch = [s.name for s in statuses if not s.is_core and s.version is None]

    if missing_core:
        lines.append("")
        lines.append("Missing CORE packages — run in R:")
        lines.append(f"  install.packages(c({', '.join(repr(p) for p in missing_core)}))")
    if missing_stretch:
        lines.append("")
        lines.append("Optional stretch packages — run in R if you want them:")
        lines.append(f"  install.packages(c({', '.join(repr(p) for p in missing_stretch)}))")

    lines.append("")
    if missing_core:
        lines.append("Result: NOT READY — core packages missing.")
    elif missing_stretch:
        lines.append("Result: READY for core wrappers. STRETCH WRAPPERS UNAVAILABLE.")
    else:
        lines.append("Result: READY — all core and stretch packages installed.")

    if verbose:
        print("\n".join(lines))
    return not missing_core
