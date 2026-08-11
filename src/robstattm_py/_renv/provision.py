"""Build the package-private R environment with micromamba.

This is what makes ``pip install robstattm-py`` enough on a machine with no R at
all. It creates a self-contained conda environment under
``<ROBSTATTM_HOME>/envs/r`` holding R plus RobStatTM and its dependencies, and
never touches any R the user already has.

A few decisions here are load-bearing:

**``r-base`` is not pinned.** conda-forge's R packages carry run-time
constraints like ``r-base >=4.5,<4.6.0a0``. Pinning a version ourselves would
force the solver to choose between an ancient ``r-robstattm`` build and failing
outright. We give a floor, let the solver pick a mutually compatible set, and
record what it chose.

**The child environment is scrubbed.** A user's ``~/.condarc``, an activated
conda environment, or a stray ``R_LIBS`` would otherwise leak into the solve.
Notably, a ``.condarc`` listing the ``defaults`` channel now trips Anaconda's
terms-of-service gate and would fail the build for reasons that have nothing to
do with us.

**Verification runs in a subprocess.** A half-built environment must not be able
to crash the CLI that is trying to report on it.

**Nothing is redistributed.** R (GPL-2) and RobStatTM (GPL-3) are downloaded
from conda-forge at setup time. This package is MIT and ships neither.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from robstattm_py._renv import micromamba, paths, state
from robstattm_py._renv.errors import EXIT_DISK, EXIT_PROVISION, RenvError
from robstattm_py._renv.probe import SOURCE_BUILD_SUBDIRS, Probe

#: Minimum R we ask the solver for. A floor, not a pin - see the module docstring.
R_FLOOR = "r-base>=4.3"

#: Packages available on conda-forge for every platform we provision on.
COMMON_SPECS: tuple[str, ...] = (
    "r-robustbase",
    "r-rrcov",
    # Not an estimator dependency: `robust` ships breslow.dat, which the glmrob
    # parity tests fit. Cheap, and keeps the provisioned env able to run the
    # full suite.
    "r-robust",
)

#: Available on conda-forge everywhere except the subdirs in
#: :data:`SOURCE_BUILD_SUBDIRS`, where they must be compiled from CRAN source.
CONDA_ONLY_SPECS: tuple[str, ...] = ("r-robstattm", "r-pyinit")

#: Toolchain added when the two packages above have to be built from source.
SOURCE_BUILD_SPECS: tuple[str, ...] = (
    "r-rcpp",
    "r-rcpparmadillo",
    "c-compiler",
    "cxx-compiler",
    "fortran-compiler",
    "make",
    "pkg-config",
)

#: R packages that must load before the environment is declared usable.
REQUIRED_R_PACKAGES: tuple[str, ...] = ("RobStatTM", "pyinit", "robustbase", "rrcov")

#: Rough disk needed, used for the preflight check.
# Measured on Windows 2026-08-10: 364 MB downloaded, 1.6 GB environment plus
# 2.0 GB package cache. Windows is the worst case because conda-forge's R
# pulls in the large mingw headers package.
REQUIRED_FREE_BYTES = 6 * 1024**3

CHANNEL = "conda-forge"


class ProvisionError(RenvError):
    """Building the private R environment failed."""

    code = "E_PROVISION"
    exit_code = EXIT_PROVISION
    default_remedy = (
        "The log above names the underlying failure. Re-run with --force to "
        "rebuild from scratch, and include the log if you report this."
    )


class DiskSpaceError(RenvError):
    """Not enough room to provision."""

    code = "E_DISK_SPACE"
    exit_code = EXIT_DISK
    default_remedy = (
        "Free some space, or set ROBSTATTM_HOME to a directory on a larger "
        "drive (for example ROBSTATTM_HOME=D:\\robstattm)."
    )


class SpaceInPathError(RenvError):
    """The install path contains a space, which R's launcher cannot handle.

    Not a stylistic objection. conda-forge ships ``bin/R`` as a shell script
    that expands ``R_HOME_DIR`` unquoted, so a space splits the path and R fails
    to start. This bit the *default* macOS location, since
    ``~/Library/Application Support`` contains one.
    """

    code = "E_SPACE_IN_PATH"
    exit_code = EXIT_PROVISION
    default_remedy = (
        "Set ROBSTATTM_HOME to a path with no spaces and try again, for example:\n"
        "    macOS/Linux:  export ROBSTATTM_HOME=\"$HOME/.robstattm-py\"\n"
        "    Windows:      $env:ROBSTATTM_HOME = 'C:\\rtm'\n"
        "  then re-run `robstattm-py setup`."
    )


class LongPathError(RenvError):
    """The install path is too long for Windows' 260-character limit.

    Not a hypothetical: conda-forge's Windows R build depends on a mingw
    headers package containing Windows SDK filenames that are themselves ~215
    characters deep inside the cache. Anything but a short root overflows, and
    micromamba reports it only as an opaque "Package cache error" after several
    minutes of downloading.
    """

    code = "E_LONG_PATH"
    exit_code = EXIT_PROVISION
    default_remedy = (
        "Set ROBSTATTM_HOME to a short path and try again, for example:\n"
        "    PowerShell:  $env:ROBSTATTM_HOME = 'C:\\rtm'\n"
        "    cmd:         set ROBSTATTM_HOME=C:\\rtm\n"
        "  then re-run `robstattm-py setup`.\n"
        "  To make it permanent: setx ROBSTATTM_HOME C:\\rtm\n"
        "  (Alternatively, enable long paths system-wide - this needs "
        "administrator rights and a reboot.)"
    )


def package_spec(subdir: str) -> list[str]:
    """Return the conda package specification for a platform.

    Three platforms are the odd ones out — ``osx-arm64``, ``linux-aarch64``
    and ``linux-ppc64le``. conda-forge has no ``r-robstattm`` or ``r-pyinit``
    build for any of them (verified 2026-08-11), so those two are compiled from
    CRAN source afterwards and a toolchain is requested instead.
    """
    specs = [R_FLOOR, *COMMON_SPECS]
    if subdir in SOURCE_BUILD_SUBDIRS:
        specs.extend(SOURCE_BUILD_SPECS)
    else:
        specs.extend(CONDA_ONLY_SPECS)
    return sorted(specs)


def build_create_argv(
    executable: Path,
    prefix: Path,
    specs: list[str],
    *,
    probe: Probe | None = None,
    channel: str = CHANNEL,
    platform: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Build the ``micromamba create`` command line."""
    argv = [
        str(executable),
        "create",
        "--yes",
        "--prefix",
        str(prefix),
        "--root-prefix",
        str(paths.mamba_root(probe)),
        # Ignore any user or system configuration; see the module docstring.
        "--no-rc",
        "--override-channels",
        "--channel",
        channel,
    ]
    if platform:
        argv += ["--platform", platform]
    if dry_run:
        argv += ["--dry-run", "--json"]
    return argv + specs


def child_env(probe: Probe | None = None) -> dict[str, str]:
    """Return a scrubbed environment for micromamba subprocesses.

    Removing the caller's conda, mamba and R variables is the main isolation
    mechanism; ``--no-rc`` is belt and braces.
    """
    probe = probe or Probe.current()
    blocked_prefixes = ("CONDA", "MAMBA", "_CE_")
    blocked_exact = {
        "CONDARC",
        "R_HOME",
        "R_LIBS",
        "R_LIBS_USER",
        "R_LIBS_SITE",
        "R_PROFILE",
        "R_PROFILE_USER",
        "R_ENVIRON",
        "R_ENVIRON_USER",
        "R_ARCH",
    }
    env = {
        key: value
        for key, value in probe.environ.items()
        if not key.startswith(blocked_prefixes) and key not in blocked_exact
    }
    env["MAMBA_ROOT_PREFIX"] = str(paths.mamba_root(probe))
    env["MAMBA_NO_BANNER"] = "1"
    # Deliberately do NOT set CONDARC here. micromamba treats "rc files are
    # disabled" (--no-rc) plus "here is an rc file" as a contradiction and
    # aborts with "Incompatible configuration". Dropping CONDARC from the
    # inherited environment, which the filter above already does, is what
    # actually provides the isolation.
    return env


def preflight(probe: Probe | None = None) -> list[str]:
    """Check we can provision here, returning any non-fatal warnings.

    Raises
    ------
    DiskSpaceError
        Too little free space to be worth starting.
    """
    probe = probe or Probe.current()
    root = paths.root(probe)
    warnings: list[str] = []

    existing = root
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    try:
        free = shutil.disk_usage(existing).free
    except OSError:  # pragma: no cover - exotic filesystem
        free = None
    if free is not None and free < REQUIRED_FREE_BYTES:
        raise DiskSpaceError(
            f"Only {free / 1024**3:.1f} GB free on the drive holding {root}; "
            f"about {REQUIRED_FREE_BYTES / 1024**3:.0f} GB is needed.",
        )

    # Fail here rather than after a multi-minute download: micromamba reports a
    # path overflow only as "Package cache error", long after the point where a
    # user could have been told what to do about it.
    text = str(root)
    if probe.is_windows and not paths.windows_long_paths_enabled():
        limit = paths.max_safe_root_length()
        if len(text) > limit:
            raise LongPathError(
                f"The install path is {len(text)} characters long, and Windows "
                f"cannot handle more than {limit} here.",
                detail=(
                    f"Path: {text}\n"
                    f"Some files inside the package cache are up to "
                    f"{paths.DEEPEST_INTERNAL_PATH} characters deep, which would "
                    f"exceed Windows' {paths.WINDOWS_MAX_PATH}-character limit.\n"
                    "Long-path support is currently disabled on this machine."
                ),
            )

    # A space is fatal, not cosmetic. conda-forge's `bin/R` is a shell script
    # that expands R_HOME_DIR unquoted, so a space splits the path and R cannot
    # start at all:
    #
    #   .../Application Support/.../bin/R: line 4:
    #     Support/robstattm-py/envs/r/lib/R: No such file or directory
    #
    # Caught here rather than after the download, which is where it surfaced
    # the first time.
    if " " in text:
        raise SpaceInPathError(
            f"The install path contains a space, which R cannot handle: {root}",
            detail=(
                "R's launcher script expands its own location without quoting, "
                "so a space in the path stops R from starting."
            ),
        )

    if any(ord(ch) > 127 for ch in text):
        warnings.append(
            f"The install path contains non-ASCII characters ({root}). Some R "
            "packages mishandle these; consider setting ROBSTATTM_HOME."
        )
    return warnings


def licence_notice() -> str:
    """Return the notice printed before anything is downloaded."""
    return (
        "This downloads R (GPL-2) and RobStatTM (GPL-3) from conda-forge into a\n"
        "private directory. robstattm-py itself is MIT licensed and redistributes\n"
        "neither; they are fetched from their upstream publisher at install time."
    )


def _stream(
    argv: list[str],
    env: dict[str, str],
    log: Path | None,
    *,
    quiet: bool = False,
    heartbeat_seconds: int = 15,
) -> int:
    """Run a command, echoing and logging output, with a silence heartbeat.

    micromamba can be quiet for minutes while solving. Without the heartbeat a
    user reasonably concludes it has hung and kills it.
    """
    handle = log.open("a", encoding="utf-8", errors="replace") if log else None
    last_output = time.monotonic()
    stop = threading.Event()

    def _tick() -> None:
        while not stop.wait(1.0):
            idle = time.monotonic() - last_output
            if idle >= heartbeat_seconds and not quiet:
                print(f"  ... still working ({int(idle)}s since last output)", flush=True)
                time.sleep(heartbeat_seconds)

    ticker = threading.Thread(target=_tick, daemon=True)
    ticker.start()
    try:
        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            env=env,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            last_output = time.monotonic()
            if handle:
                handle.write(line)
            if not quiet:
                print("  " + line.rstrip(), flush=True)
        return process.wait()
    finally:
        stop.set()
        if handle:
            handle.close()


def run_in_env(
    executable: Path,
    prefix: Path,
    r_expression: str,
    *,
    probe: Probe | None = None,
    timeout: int = 900,
) -> subprocess.CompletedProcess:
    """Run an R expression inside the provisioned environment.

    Goes through ``micromamba run`` rather than invoking ``Rscript`` directly:
    that executes the environment's activation scripts, which is what puts the
    conda compilers and their ``CONDA_BUILD_SYSROOT`` on the path for the
    Apple Silicon source build.
    """
    argv = [
        str(executable),
        "run",
        "--prefix",
        str(prefix),
        "Rscript",
        "--vanilla",
        "-e",
        r_expression,
    ]
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        argv,
        capture_output=True,
        text=True,
        errors="replace",
        env=child_env(probe),
        timeout=timeout,
        check=False,
    )


def verify_environment(
    executable: Path,
    prefix: Path,
    *,
    probe: Probe | None = None,
    packages: tuple[str, ...] = REQUIRED_R_PACKAGES,
) -> dict[str, str]:
    """Confirm R starts and each required package loads.

    Loading, not merely being installed: a package can install successfully and
    still fail to ``dyn.load`` when a runtime library is missing, which would
    otherwise surface later as a baffling error inside a user's first fit.

    Returns
    -------
    dict
        ``{package: version}`` for every package that loaded.
    """
    quoted = ", ".join(f'"{p}"' for p in packages)
    expression = (
        'cat("R_VERSION=", as.character(getRversion()), "\\n", sep="");'
        f"for (p in c({quoted})) {{"
        "  ok <- suppressWarnings(requireNamespace(p, quietly=TRUE));"
        '  cat(p, "=", if (ok) as.character(packageVersion(p)) else "MISSING", "\\n", sep="") }'
    )
    completed = run_in_env(executable, prefix, expression, probe=probe)
    if completed.returncode != 0:
        raise ProvisionError(
            "The provisioned R could not be started.",
            detail=(completed.stderr or completed.stdout or "").strip()[-2000:],
        )

    found: dict[str, str] = {}
    r_version = ""
    for line in (completed.stdout or "").splitlines():
        if line.startswith("R_VERSION="):
            r_version = line.split("=", 1)[1].strip()
        elif "=" in line:
            name, _, version = line.partition("=")
            version = version.strip()
            if version and version != "MISSING":
                found[name.strip()] = version

    missing = [p for p in packages if p not in found]
    if missing:
        raise ProvisionError(
            "The provisioned R is missing required packages: " + ", ".join(missing),
            detail=(completed.stdout or "").strip()[-2000:],
        )
    found["_R_VERSION"] = r_version
    return found


def provision(
    *,
    probe: Probe | None = None,
    force: bool = False,
    dry_run: bool = False,
    quiet: bool = False,
    channel: str = CHANNEL,
    platform: str | None = None,
    micromamba_path: Path | None = None,
    verify_checksum: bool = True,
    insecure: bool = False,
    timeout: int = 300,
    force_unlock: bool = False,
    progress: Callable[[str], None] | None = None,
) -> state.State:
    """Create (or confirm) the private R environment.

    Returns
    -------
    State
        The recorded state, with ``status == "ready"`` on success.
    """
    probe = probe or Probe.current()
    say = progress or (lambda message: None if quiet else print(message, flush=True))

    subdir = platform or probe.subdir
    specs = package_spec(subdir)
    digest = state.spec_hash(specs, subdir, micromamba.MICROMAMBA_VERSION)

    current = state.State.load(probe)
    if current.matches(digest) and not force and not dry_run:
        r_home = Path(current.r_home)
        if r_home.is_dir():
            say(f"Already provisioned: R {current.r_version} at {r_home}")
            return current

    for warning in preflight(probe):
        say(f"Warning: {warning}")

    if dry_run:
        executable = micromamba_path or paths.micromamba_exe(probe)
        argv = build_create_argv(
            executable,
            paths.env_prefix(probe),
            specs,
            probe=probe,
            channel=channel,
            platform=platform,
            dry_run=True,
        )
        say("Would run:")
        say("  " + " ".join(argv))
        return current

    with state.SetupLock(probe, force=force_unlock):
        return _provision_locked(
            probe=probe,
            specs=specs,
            digest=digest,
            subdir=subdir,
            channel=channel,
            platform=platform,
            micromamba_path=micromamba_path,
            verify_checksum=verify_checksum,
            insecure=insecure,
            timeout=timeout,
            quiet=quiet,
            say=say,
        )


def _provision_locked(
    *,
    probe: Probe,
    specs: list[str],
    digest: str,
    subdir: str,
    channel: str,
    platform: str | None,
    micromamba_path: Path | None,
    verify_checksum: bool,
    insecure: bool,
    timeout: int,
    quiet: bool,
    say: Callable[[str], None],
) -> state.State:
    """Do the work, with the setup lock held."""
    prefix = paths.env_prefix(probe)
    log_directory = paths.ensure_dir(paths.log_dir(probe))
    log = log_directory / f"setup-{time.strftime('%Y%m%d-%H%M%S')}.log"

    say("[1/4] Getting the package manager (micromamba)")
    executable = micromamba.ensure_micromamba(
        probe=probe,
        verify=verify_checksum,
        timeout=timeout,
        insecure=insecure,
        override=micromamba_path,
    )

    # Only two states are trusted: "ready and matching" (handled by the caller)
    # or "rebuild". The package cache lives outside the prefix, so this is fast.
    state.State().with_status(
        "partial", spec_hash=digest, subdir=subdir,
        micromamba_version=micromamba.MICROMAMBA_VERSION,
    ).save(probe)
    if prefix.exists():
        say("      removing the previous environment")
        shutil.rmtree(prefix, ignore_errors=True)

    say("[2/4] Installing R and RobStatTM from conda-forge")
    say("      roughly 400 MB to download; this usually takes 3-6 minutes")
    argv = build_create_argv(
        executable, prefix, specs, probe=probe, channel=channel, platform=platform
    )
    code = _stream(argv, child_env(probe), log, quiet=quiet)
    if code != 0:
        tail = _log_tail(log)
        # micromamba reports a Windows path overflow only as a cache error, so
        # translate it rather than passing the confusion on to the user.
        if _looks_like_path_overflow(tail, probe):
            raise LongPathError(
                "Provisioning failed because a file path exceeded Windows' limit.",
                detail=tail + f"\n\nFull log: {log}",
            )
        raise ProvisionError(
            f"micromamba failed with exit status {code}.",
            detail=tail + f"\n\nFull log: {log}",
            remedy=_solve_remedy(subdir),
        )

    if subdir in SOURCE_BUILD_SUBDIRS:
        say("[3/4] Building RobStatTM and pyinit from source (Apple Silicon)")
        from robstattm_py._renv import source_build

        source_build.build_missing(executable, prefix, probe=probe, log=log, say=say)
    else:
        say("[3/4] No source build needed on this platform")

    say("[4/4] Verifying")
    packages = verify_environment(executable, prefix, probe=probe)
    r_version = packages.pop("_R_VERSION", "")

    result = state.State(
        status="ready",
        spec_hash=digest,
        r_home=str(paths.provisioned_r_home(probe)),
        r_version=r_version,
        subdir=subdir,
        micromamba_version=micromamba.MICROMAMBA_VERSION,
        packages=packages,
    )
    result.save(probe)
    say("")
    say(f"R {r_version} is ready at {result.r_home}")
    return result


#: Signatures micromamba emits when extraction hit the Windows path limit.
_PATH_OVERFLOW_MARKERS = (
    "invalid package cache",
    "cannot find a valid extracted directory cache",
    "package cache error",
    "filename too long",
    "the specified path, file name, or both are too long",
)


def _looks_like_path_overflow(log_text: str, probe: Probe) -> bool:
    """True when a micromamba failure is really a Windows path-length problem."""
    if not probe.is_windows:
        return False
    lowered = log_text.lower()
    return any(marker in lowered for marker in _PATH_OVERFLOW_MARKERS)


def _log_tail(log: Path, lines: int = 30) -> str:
    """Return the last few lines of a log, for an error message."""
    try:
        content = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:  # pragma: no cover
        return "(no log available)"
    return "\n".join(content[-lines:])


def _solve_remedy(subdir: str) -> str:
    """Return advice tailored to the platform that failed to solve."""
    base = (
        "Check the log above. If the solver could not find a package, conda-forge "
        "may be mid-migration; try again later or pin an older R with --r-version."
    )
    if subdir in SOURCE_BUILD_SUBDIRS:
        return (
            base
            + "\nOn Apple Silicon, RobStatTM and pyinit have no conda-forge build and "
            "are compiled from source, which needs the Xcode command line tools: "
            "run `xcode-select --install`."
        )
    return base


def uninstall(
    *,
    probe: Probe | None = None,
    env: bool = True,
    rlibs: bool = True,
    cache: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Remove what we installed. Returns ``{path: bytes reclaimed}``.

    Every target is checked against our own root before deletion, so a
    misconfigured ``ROBSTATTM_HOME`` cannot turn this into a destructive
    command.
    """
    probe = probe or Probe.current()
    targets: list[Path] = []
    if env:
        targets.append(paths.env_prefix(probe))
    if rlibs:
        targets.append(paths.root(probe) / "rlibs")
    if cache:
        targets.extend([paths.pkgs_dir(probe), paths.bin_dir(probe), paths.log_dir(probe)])

    removed: dict[str, int] = {}
    for target in targets:
        if not paths.is_within_root(target, probe):
            raise ProvisionError(
                f"Refusing to delete {target}: it is outside the robstattm-py directory.",
            )
        if not target.exists():
            continue
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
        removed[str(target)] = size
        if not dry_run:
            shutil.rmtree(target, ignore_errors=True)

    if not dry_run and env:
        current = state.State.load(probe)
        current.with_status("absent", r_home="", packages={}).save(probe)
        if cache:
            paths.state_file(probe).unlink(missing_ok=True)
    return removed


def virtual_package_overrides(subdir: str) -> dict[str, str]:
    """Environment overrides needed to solve for a *foreign* platform.

    conda expresses host capabilities as virtual packages: ``__osx`` carries the
    macOS version, ``__glibc`` the C library version. They are detected from the
    running machine, so when solving for another platform they are simply
    absent and the solve fails with, for example::

        nothing provides __osx >=11.0 needed by r-rrcov-1.7_7-...

    That is an artefact of cross-solving, not a real packaging problem - the
    same specification resolves fine on an actual macOS machine. Declaring
    plausible values lets a single runner check every platform.

    The values are floors, chosen to match what conda-forge currently targets.
    """
    if subdir.startswith("osx"):
        # conda-forge's arm64 builds require macOS 11; Intel builds target 10.13.
        return {"CONDA_OVERRIDE_OSX": "11.0" if subdir.endswith("arm64") else "10.13"}
    if subdir.startswith("linux"):
        return {"CONDA_OVERRIDE_GLIBC": "2.17"}
    if subdir.startswith("win"):
        return {"CONDA_OVERRIDE_WIN": "0"}
    return {}


def solve_only(
    subdir: str,
    *,
    probe: Probe | None = None,
    channel: str = CHANNEL,
    timeout: int = 600,
) -> dict:
    """Ask the solver whether a platform's specification is satisfiable.

    Cheap enough to run in CI on every pull request, and it is what catches the
    two breakages most likely to hit users: conda-forge dropping a build we
    depend on, and ``osx-arm64`` gaining (or still lacking) ``r-robstattm``.
    Solving for a foreign platform works, so one Linux runner covers them all.
    """
    probe = probe or Probe.current()
    executable = micromamba.ensure_micromamba(probe=probe)
    argv = build_create_argv(
        executable,
        paths.root(probe) / "solve-check" / subdir,
        package_spec(subdir),
        probe=probe,
        channel=channel,
        platform=subdir,
        dry_run=True,
    )
    env = child_env(probe)
    # Added after child_env, which strips everything CONDA*-prefixed.
    env.update(virtual_package_overrides(subdir))
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        argv, capture_output=True, text=True, errors="replace",
        env=env, timeout=timeout, check=False,
    )
    if completed.returncode != 0:
        raise ProvisionError(
            f"Solve failed for {subdir}.",
            detail=(completed.stderr or completed.stdout or "")[-2000:],
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"raw": completed.stdout}


def _clean_environ_for_tests() -> dict[str, str]:  # pragma: no cover - helper
    """Return ``os.environ`` without conda/R leakage, for interactive debugging."""
    return child_env(Probe(system="Linux", machine="x86_64", is_64bit=True,
                           environ=dict(os.environ)))


__all__ = [
    "CHANNEL",
    "COMMON_SPECS",
    "CONDA_ONLY_SPECS",
    "REQUIRED_R_PACKAGES",
    "SOURCE_BUILD_SPECS",
    "DiskSpaceError",
    "ProvisionError",
    "build_create_argv",
    "child_env",
    "licence_notice",
    "package_spec",
    "preflight",
    "provision",
    "run_in_env",
    "solve_only",
    "uninstall",
    "verify_environment",
]
