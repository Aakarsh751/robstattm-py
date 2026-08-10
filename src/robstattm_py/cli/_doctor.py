"""``robstattm-py doctor`` — diagnose the environment.

The section that earns its keep is the discovery trace. "R not found" tells a
user nothing; a list of the nine places we looked, with the specific reason each
was rejected, usually makes the fix obvious without any support round-trip.
"""
from __future__ import annotations

import json
import sys

from robstattm_py._renv.errors import EXIT_NO_R, EXIT_OK, EXIT_R_PKG_MISSING
from robstattm_py._renv.report import (
    CORE_R_PACKAGES,
    OPTIONAL_R_PACKAGES,
    STRETCH_R_PACKAGES,
    SetupReport,
    collect_report,
)


def add_parser(subparsers) -> None:
    """Attach the ``doctor`` subcommand."""
    parser = subparsers.add_parser(
        "doctor",
        help="diagnose the R setup and explain anything that is wrong",
        description=(
            "Check every layer robstattm-py depends on - Python, rpy2, R itself, "
            "and the R packages - and report what is missing along with how to "
            "fix it."
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show the full discovery trace"
    )
    parser.add_argument(
        "--no-start-r",
        action="store_true",
        help="do not start R (skips the R package check, but is fast and inert)",
    )
    parser.set_defaults(_handler=run)


def run(args) -> int:
    """Execute ``doctor``."""
    report = collect_report(start_r=not args.no_start_r)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_text(report, verbose=args.verbose))

    if report.ok:
        return EXIT_OK
    if report.r is None:
        return EXIT_NO_R
    return EXIT_R_PKG_MISSING


def _supports_unicode() -> bool:
    """True when stdout can encode the status glyphs.

    Windows consoles default to cp1252, which raises on U+2713. Probing the
    encoding keeps the report readable instead of crashing halfway through it.
    """
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "✓✗⚠".encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def render_text(report: SetupReport, *, verbose: bool = False) -> str:
    """Render the report for a terminal."""
    unicode_ok = _supports_unicode()
    ok_mark = "✓" if unicode_ok else "[ok]"
    bad_mark = "✗" if unicode_ok else "[MISSING]"
    warn_mark = "⚠" if unicode_ok else "[warn]"

    out: list[str] = ["robstattm-py doctor", "=" * 19, ""]

    out.append("Python")
    out.append(f"  version        {report.python_version} ({report.python_arch})")
    out.append(f"  executable     {report.executable}")
    out.append(f"  virtualenv     {'yes' if report.in_venv else 'no'}")
    out.append(f"  platform       {report.platform_subdir}")
    out.append(f"  robstattm-py   {report.package_version}")
    out.append("")

    out.append("rpy2")
    if report.rpy2_version is None:
        out.append(f"  {bad_mark} not installed")
    else:
        out.append(f"  version        {report.rpy2_version}")
        if report.rpy2_cffi_mode:
            out.append(f"  binding        {report.rpy2_cffi_mode}")
    out.append("")

    out.append("R")
    if report.r is None:
        out.append(f"  {bad_mark} not found")
    else:
        out.append(f"  home           {report.r.path}")
        out.append(f"  version        {report.r_version_string or report.r.version_string}")
        out.append(f"  architecture   {report.r.arch}")
        out.append(f"  found via      {report.r.source}")
        if report.r.conda_prefix:
            out.append(f"  conda prefix   {report.r.conda_prefix}")
    out.append("")

    if report.r is None or verbose:
        out.append("Where we looked")
        trace = "\n".join(row.describe() for row in report.trace)
        out.append(trace or "  (nothing to check)")
        out.append("")

    if report.r_packages:
        out.append("R packages")
        for group, names in (
            ("required", CORE_R_PACKAGES),
            ("optional (pense / gse / tsgs)", STRETCH_R_PACKAGES),
            ("optional (example scripts)", OPTIONAL_R_PACKAGES),
        ):
            present = [n for n in names if n in report.r_packages]
            if not present:
                continue
            out.append(f"  {group}:")
            for name in present:
                version = report.r_packages[name]
                if version:
                    out.append(f"    {ok_mark} {name:<16} {version}")
                else:
                    mark = bad_mark if names is CORE_R_PACKAGES else warn_mark
                    out.append(f"    {mark} {name:<16} not installed")
        out.append("")

    if report.problems:
        out.append("Problems")
        for problem in report.problems:
            mark = bad_mark if problem.is_error else warn_mark
            out.append(f"  {mark} [{problem.code}] {problem.message}")
            for line in problem.remedy.splitlines():
                out.append(f"      {line}")
            out.append("")

    out.append("Result: " + ("READY" if report.ok else "NOT READY"))
    return "\n".join(out)


__all__ = ["add_parser", "render_text", "run"]
