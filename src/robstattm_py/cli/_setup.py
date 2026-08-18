"""``robstattm-py setup``, install a private R so the user never has to.

This is the command that makes the package usable by someone who has never
installed R and does not want to. It downloads R and RobStatTM from conda-forge
into a directory this package owns, and leaves any existing R alone.
"""
from __future__ import annotations

import sys
from pathlib import Path

from robstattm_py._renv import discover_only, paths, provision, state
from robstattm_py._renv.errors import EXIT_CONFIRM_REQUIRED, EXIT_OK, RenvError


def add_parser(subparsers) -> None:
    """Attach the ``setup`` subcommand."""
    parser = subparsers.add_parser(
        "setup",
        help="download a private R so you do not have to install one",
        description=(
            "Create a self-contained R environment for robstattm-py, including "
            "RobStatTM and its dependencies. Downloads roughly 400 MB and uses "
            "about 4 GB on disk on Windows (less on Linux and macOS). Any R "
            "you already have is left untouched."
        ),
    )
    parser.add_argument("--force", action="store_true", help="rebuild even if already set up")
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would happen, change nothing"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="do not ask for confirmation"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="less output")
    parser.add_argument(
        "--use-system-r",
        action="store_true",
        help="do not download anything; pin the R already installed on this machine",
    )
    parser.add_argument("--channel", default=provision.CHANNEL, help="conda channel")
    parser.add_argument(
        "--platform", help="target platform (for testing a foreign solve, e.g. osx-arm64)"
    )
    parser.add_argument("--micromamba-path", type=Path, help="use this micromamba binary")
    parser.add_argument(
        "--no-verify-checksum",
        action="store_true",
        help="skip the micromamba checksum check (not recommended)",
    )
    parser.add_argument(
        "--insecure", action="store_true", help="skip TLS verification (not recommended)"
    )
    parser.add_argument("--timeout", type=int, default=300, help="download timeout, seconds")
    parser.add_argument(
        "--force-unlock", action="store_true", help="ignore a stale setup lock"
    )
    parser.set_defaults(_handler=run)


def _confirm(args) -> bool:
    """Ask before downloading, unless told not to.

    Refuses to assume consent on a non-interactive stdin. Silently pulling
    several hundred megabytes inside a CI job, or a Dockerfile that merely ran
    the wrong command, is exactly the surprise this guards against.
    """
    if args.yes or args.dry_run:
        return True
    if not sys.stdin.isatty():
        print(
            "Refusing to download without confirmation because this is not an "
            "interactive terminal.\nRe-run with --yes to proceed.",
            file=sys.stderr,
        )
        return False
    answer = input("Download R and RobStatTM now? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _use_system_r(args) -> int:
    """Pin an already-installed R instead of downloading one."""
    result = discover_only()
    info = result.info
    if info is None:
        raise RenvError(
            "No R was found on this machine, so there is nothing to pin.",
            detail="Locations checked:\n" + result.render_trace(),
            remedy="Run `robstattm-py setup` without --use-system-r to download one.",
        )

    state.State(
        status="ready",
        spec_hash="system",
        r_home=str(info.path),
        r_version=info.version_string,
        subdir="system",
    ).save()
    print(f"Pinned the existing R at {info.path} (version {info.version_string}).")
    print("robstattm-py will use this R from now on.")
    print("\nRun `robstattm-py doctor` to check the R packages are present.")
    return EXIT_OK


def run(args) -> int:
    """Execute ``setup``."""
    if args.use_system_r:
        return _use_system_r(args)

    print(f"robstattm-py setup   ->   {paths.root()}")
    print()
    print(provision.licence_notice())
    print()

    if not _confirm(args):
        return EXIT_CONFIRM_REQUIRED

    result = provision.provision(
        force=args.force,
        dry_run=args.dry_run,
        quiet=args.quiet,
        channel=args.channel,
        platform=args.platform,
        micromamba_path=args.micromamba_path,
        verify_checksum=not args.no_verify_checksum,
        insecure=args.insecure,
        timeout=args.timeout,
        force_unlock=args.force_unlock,
    )

    if args.dry_run:
        return EXIT_OK

    if result.is_ready:
        print()
        print("Try it:")
        print("  python -c \"import robstattm_py as rpm; print(rpm.check_setup())\"")
    return EXIT_OK


__all__ = ["add_parser", "run"]
