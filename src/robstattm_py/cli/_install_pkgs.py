"""``robstattm-py install-r-packages``, install R packages without an R console.

This is the command every "package X is not installed" message points at. It
matters most for users who never installed R themselves and so have no R prompt
to type ``install.packages()`` into.

Two deliberate choices:

**It runs in a subprocess.** ``Rscript`` is invoked rather than the embedded
interpreter, so a compiler crash or a package that calls ``q()`` cannot take
down the Python process, and it works even when the embedded session is in a
bad state, which is exactly when you need it.

**It installs into a private library by default.** Writing into the user's own R
library would be a surprising side effect on a machine where R is shared with
other work, and on Linux the system library usually is not writable anyway. The
private directory is keyed by R minor version and platform, because compiled R
packages are not ABI-compatible across R releases.
"""
from __future__ import annotations

import subprocess

from robstattm_py._renv import discover_only, paths
from robstattm_py._renv.errors import (
    EXIT_OK,
    EXIT_R_PKG_MISSING,
    NoRFoundError,
)
from robstattm_py._renv.probe import Probe

DEFAULT_REPOS = "https://cloud.r-project.org"


def add_parser(subparsers) -> None:
    """Attach the ``install-r-packages`` subcommand."""
    parser = subparsers.add_parser(
        "install-r-packages",
        help="install R packages that robstattm-py needs",
        description=(
            "Install one or more R packages using the R that robstattm-py has "
            "found, without needing an R console. By default they go into a "
            "private library owned by robstattm-py, leaving your own R "
            "installation untouched."
        ),
    )
    parser.add_argument("names", nargs="+", metavar="NAME", help="R package name(s)")
    parser.add_argument(
        "--lib",
        default="private",
        help=(
            "where to install: 'private' (default, robstattm-py's own directory), "
            "'default' (R's normal library), or an explicit path"
        ),
    )
    parser.add_argument(
        "--repos", default=DEFAULT_REPOS, help=f"CRAN mirror (default: {DEFAULT_REPOS})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print what would run, change nothing"
    )
    parser.set_defaults(_handler=run)


def _rscript_path(r_home) -> str:
    """Return the ``Rscript`` executable belonging to a specific R_HOME."""
    import sys

    exe = "Rscript.exe" if sys.platform == "win32" else "Rscript"
    for relative in ("bin", ""):
        candidate = (r_home / relative / exe) if relative else (r_home / exe)
        if candidate.is_file():
            return str(candidate)
    # Fall back to the name and let the OS resolve it; the caller reports
    # failures either way.
    return exe


def _resolve_lib(choice: str, info, probe: Probe):
    """Return the target library directory, or ``None`` for R's default."""
    if choice == "default":
        return None
    if choice == "private":
        subdir = probe.subdir if probe.subdir != "unknown" else "generic"
        return paths.rlib_dir(info.minor, subdir, probe)
    from pathlib import Path

    return Path(choice).expanduser().absolute()


def _r_expression(names: list[str], repos: str, library) -> str:
    """Build the ``install.packages`` call.

    ``repos`` is always explicit so R never stops to ask for a mirror, an
    interactive prompt in a subprocess would simply hang.
    """
    quoted = ", ".join(f'"{n}"' for n in names)
    if library is None:
        lib_arg = ""
    else:
        escaped = str(library).replace("\\", "/")
        lib_arg = f', lib = "{escaped}"'
    return (
        f'install.packages(c({quoted}), repos = "{repos}"{lib_arg}, '
        "Ncpus = max(1L, parallel::detectCores() - 1L))"
    )


def _verify_expression(names: list[str], library) -> str:
    """Build an expression that loads each package and reports the outcome.

    Installation succeeding is not the same as the package working: a package
    can install and still fail to ``dyn.load`` when a runtime library is
    missing. Only a successful ``library()`` counts.
    """
    quoted = ", ".join(f'"{n}"' for n in names)
    if library is None:
        set_lib = ""
    else:
        escaped = str(library).replace("\\", "/")
        set_lib = f'.libPaths(c("{escaped}", .libPaths())); '
    return (
        f"{set_lib}"
        f"for (p in c({quoted})) {{ "
        "ok <- suppressWarnings(requireNamespace(p, quietly = TRUE)); "
        'cat(if (ok) "OK " else "FAIL ", p, "\\n", sep = "") }'
    )


def run(args) -> int:
    """Execute ``install-r-packages``."""
    probe = Probe.current()
    result = discover_only(probe)
    if result.info is None:
        raise NoRFoundError(
            "Cannot install R packages because no R was found.",
            detail="Locations checked:\n" + result.render_trace(),
        )

    info = result.info
    library = _resolve_lib(args.lib, info, probe)
    rscript = _rscript_path(info.path)
    install_expr = _r_expression(args.names, args.repos, library)

    print(f"R          {info.version_string} at {info.path}")
    print(f"library    {library if library else '(R default)'}")
    print(f"packages   {' '.join(args.names)}")
    print()

    if args.dry_run:
        print("Would run:")
        print(f"  {rscript} -e '{install_expr}'")
        return EXIT_OK

    if library is not None:
        paths.ensure_dir(library)

    print("Installing (this compiles C/Fortran code and can take a few minutes)...")
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [rscript, "--vanilla", "-e", install_expr],
        check=False,
    )
    if completed.returncode != 0:
        print(f"\nRscript exited with status {completed.returncode}.")

    verify = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [rscript, "--vanilla", "-e", _verify_expression(args.names, library)],
        capture_output=True,
        text=True,
        check=False,
    )
    failed = [
        line.split(" ", 1)[1].strip()
        for line in (verify.stdout or "").splitlines()
        if line.startswith("FAIL ")
    ]

    print()
    if failed:
        print(f"Not installed: {', '.join(failed)}")
        print(
            "\nIf the build failed, the log above names the missing tool. "
            "Common causes:\n"
            "  Linux   sudo apt-get install r-base-dev build-essential gfortran\n"
            "  macOS   xcode-select --install\n"
            "  Windows install Rtools from https://cran.r-project.org/bin/windows/Rtools/"
        )
        return EXIT_R_PKG_MISSING

    print(f"Installed: {', '.join(args.names)}")
    if library is not None:
        print("\nrobstattm-py will pick these up automatically next time you import it.")
    return EXIT_OK


__all__ = ["add_parser", "run"]
