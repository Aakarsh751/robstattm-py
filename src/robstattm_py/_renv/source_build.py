"""Build RobStatTM and pyinit from source, for platforms conda-forge misses.

Only ``osx-arm64`` needs this today: conda-forge has ``r-base``,
``r-robustbase`` and ``r-rrcov`` for Apple Silicon, but **not** ``r-robstattm``
or ``r-pyinit`` (verified against the conda-forge API on 2026-08-10). Everything
else provisions from prebuilt packages.

This is the most fragile code in the package and is treated as such: it is
attempted, verified by actually loading the result, and reported honestly if it
fails, with a working alternative offered. It is not silently assumed to have
worked.

**The real fix is upstream.** Adding ``osx-arm64`` to the
``r-robstattm`` and ``r-pyinit`` feedstocks would delete this module entirely.
Every dependency already has an arm64 build, so it is likely just a rerender.

Why building against a *conda* R works at all: conda-forge's ``r-base`` records
the compiler it was built with in ``<R_HOME>/etc/Makeconf``. Installing
``c-compiler``/``cxx-compiler``/``fortran-compiler`` into the same prefix puts
exactly those binaries on ``PATH``, so ``R CMD INSTALL`` finds them without any
``Makevars`` intervention. Running through ``micromamba run`` is what executes
the activation scripts that set ``CC``, ``FC`` and ``CONDA_BUILD_SYSROOT``.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from robstattm_py._renv import paths
from robstattm_py._renv.errors import EXIT_ARM64_BUILD, RenvError
from robstattm_py._renv.probe import Probe

#: Packages compiled from CRAN source, in dependency order: RobStatTM imports
#: pyinit, so pyinit must exist first.
SOURCE_PACKAGES: tuple[str, ...] = ("pyinit", "RobStatTM")

CRAN = "https://cloud.r-project.org"


class SDKMissingError(RenvError):
    """macOS command line tools are not installed."""

    code = "E_NO_SDK"
    exit_code = EXIT_ARM64_BUILD
    default_remedy = (
        "Run `xcode-select --install` (a ~700 MB download from Apple), then re-run "
        "`robstattm-py setup`."
    )


class SourceBuildError(RenvError):
    """Compiling an R package from source failed."""

    code = "E_ARM64_BUILD_FAILED"
    exit_code = EXIT_ARM64_BUILD
    default_remedy = (
        "If you already have R with RobStatTM installed, run "
        "`robstattm-py setup --use-system-r` to use that instead. Otherwise open an "
        "issue with the compiler output above."
    )


def macos_sdk_available() -> bool:
    """True when a macOS SDK the conda compilers can target is present.

    Checked *before* building rather than after: conda's clang activation
    script needs ``CONDA_BUILD_SYSROOT``, and without an SDK the failure
    surfaces deep in a compiler log instead of as "install Xcode tools".
    """
    try:
        completed = subprocess.run(  # noqa: S603,S607 - fixed argv
            ["xcrun", "--show-sdk-path"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None

    if completed is not None and completed.returncode == 0 and completed.stdout.strip():
        if Path(completed.stdout.strip()).is_dir():
            return True

    return any(
        Path(candidate).is_dir()
        for candidate in (
            "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk",
            "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform"
            "/Developer/SDKs/MacOSX.sdk",
        )
    )


def _installed(executable: Path, prefix: Path, package: str, probe: Probe) -> bool:
    """True when ``package`` can actually be loaded inside the environment."""
    from robstattm_py._renv.provision import run_in_env

    completed = run_in_env(
        executable,
        prefix,
        f'cat(isTRUE(suppressWarnings(requireNamespace("{package}", quietly=TRUE))))',
        probe=probe,
        timeout=300,
    )
    return "TRUE" in (completed.stdout or "")


def _install_expression(package: str, library: Path, kind: str) -> str:
    """Build the ``install.packages`` call for one package."""
    lib = str(library).replace("\\", "/")
    return (
        f'install.packages("{package}", lib="{lib}", repos="{CRAN}", '
        f'type="{kind}", Ncpus=max(1L, parallel::detectCores() - 1L))'
    )


def build_missing(
    executable: Path,
    prefix: Path,
    *,
    probe: Probe | None = None,
    log: Path | None = None,
    say: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """Install :data:`SOURCE_PACKAGES` into the provisioned environment.

    Tries a prebuilt CRAN binary first because it costs seconds, but never
    trusts it: CRAN's arm64 builds link against CRAN's own gfortran runtime,
    which a conda R does not have, so a package can install and then fail to
    load. Only a successful ``requireNamespace`` counts, and a failed attempt is
    rolled back before falling through to a source build.

    Returns
    -------
    dict
        ``{package: "binary" | "source"}`` describing how each was obtained.
    """
    from robstattm_py._renv.provision import run_in_env

    probe = probe or Probe.current()
    emit = say or (lambda _message: None)

    if probe.is_macos and not macos_sdk_available():
        raise SDKMissingError(
            "The macOS command line tools are required to build RobStatTM from "
            "source on Apple Silicon, and were not found.",
        )

    library = prefix / "lib" / "R" / "library"
    outcomes: dict[str, str] = {}

    for package in SOURCE_PACKAGES:
        if _installed(executable, prefix, package, probe):
            outcomes[package] = "already present"
            continue

        for kind in ("binary", "source"):
            emit(f"      {package}: trying {kind}")
            completed = run_in_env(
                executable,
                prefix,
                _install_expression(package, library, kind),
                probe=probe,
                timeout=3600,
            )
            if log is not None:
                _append_log(log, package, kind, completed)

            if _installed(executable, prefix, package, probe):
                outcomes[package] = kind
                emit(f"      {package}: {kind} build OK")
                break

            # Remove a package that installed but cannot load, so the next
            # attempt starts clean and `requireNamespace` stays meaningful.
            run_in_env(
                executable,
                prefix,
                f'try(remove.packages("{package}", lib="{str(library).replace(chr(92), "/")}"),'
                " silent=TRUE)",
                probe=probe,
                timeout=300,
            )
        else:
            raise SourceBuildError(
                f"Could not build {package} for the provisioned R.",
                detail=_tail(completed) + (f"\n\nFull log: {log}" if log else ""),
            )

    return outcomes


def _append_log(log: Path, package: str, kind: str, completed) -> None:
    """Append a build attempt's output to the setup log."""
    paths.ensure_dir(log.parent)
    with log.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n=== {package} ({kind}) ===\n")
        handle.write(completed.stdout or "")
        handle.write(completed.stderr or "")


def _tail(completed, lines: int = 40) -> str:
    """Return the last lines of a build attempt, for an error message."""
    text = ((completed.stdout or "") + (completed.stderr or "")).splitlines()
    return "\n".join(text[-lines:]) or "(no output captured)"


__all__ = [
    "CRAN",
    "SOURCE_PACKAGES",
    "SDKMissingError",
    "SourceBuildError",
    "build_missing",
    "macos_sdk_available",
]
