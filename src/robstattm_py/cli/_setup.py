"""``robstattm-py setup``, install a private R so the user never has to.

This is the command that makes the package usable by someone who has never
installed R and does not want to. It downloads R and RobStatTM from conda-forge
into a directory this package owns, and leaves any existing R alone.
"""
from __future__ import annotations

import sys
from pathlib import Path

from robstattm_py._renv import discover_only, paths, provision, state, validate_r_home
from robstattm_py._renv.errors import EXIT_CONFIRM_REQUIRED, EXIT_OK, RenvError
from robstattm_py._renv.probe import Probe


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


def _can_prompt(args) -> bool:
    """Whether to show the interactive menu rather than the scripted flow.

    Only when we can genuinely ask: a real terminal, and no flag that already
    states the intent (``--yes``, ``--dry-run``, ``--force``). Scripts, CI, and
    Dockerfiles fall through to the unchanged non-interactive path, so their
    behaviour does not change.
    """
    return sys.stdin.isatty() and not (args.yes or args.dry_run or args.force)


def _prompt_choice(options: list[str], default: int) -> int:
    """Show a numbered menu and return the chosen 1-based index."""
    for i, text in enumerate(options, 1):
        marker = "   (default)" if i == default else ""
        print(f"  [{i}] {text}{marker}")
    print()
    while True:
        raw = input(f"Enter a number [1-{len(options)}, default {default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        print(f"Please enter a number between 1 and {len(options)}.")


def _cancelled() -> int:
    print("Cancelled. Nothing was changed.")
    return EXIT_OK


def _pin_r_at_path() -> int:
    """Ask for a path to an existing R and pin it."""
    raw = input(
        "Path to your R installation root (the folder with library/ and etc/): "
    ).strip()
    if not raw:
        return _cancelled()
    info = validate_r_home(Path(raw).expanduser(), probe=Probe.current(), source="user")
    state.State(
        status="ready",
        spec_hash="system",
        r_home=str(info.path),
        r_version=info.version_string,
        subdir="system",
    ).save()
    print(f"Pinned the R at {info.path} (version {info.version_string}).")
    print("robstattm-py will use this R from now on.")
    print("\nRun `robstattm-py doctor` to check the R packages are present.")
    return EXIT_OK


def _interactive_setup(args) -> int:
    """Act on the professor's guidance: prefer an existing R, otherwise ask.

    If R is already installed we recommend using it (a private download is
    heavy and pointless then); if it is not, we ask whether to download one or
    point at an R the user has elsewhere.
    """
    existing = discover_only().info
    print(f"robstattm-py setup   ->   {paths.root()}")
    print()

    if existing is not None:
        print("An R installation is already available on this machine:")
        print(f"    {existing.path}   (version {existing.version_string})")
        print()
        print("What would you like to do?")
        choice = _prompt_choice(
            [
                "Use this R (recommended; nothing to download)",
                "Download a separate private R (~400 MB) anyway",
                "Cancel",
            ],
            default=1,
        )
        if choice == 1:
            return _use_system_r(args)
        if choice == 2:
            return _provision_flow(args, already_confirmed=True)
        return _cancelled()

    print("No R installation was found on this machine.")
    print()
    print("What would you like to do?")
    choice = _prompt_choice(
        [
            "Download a private R now (~400 MB; recommended if you have no R)",
            "Use an R you already have elsewhere (enter its path)",
            "Cancel",
        ],
        default=1,
    )
    if choice == 1:
        return _provision_flow(args, already_confirmed=True)
    if choice == 2:
        return _pin_r_at_path()
    return _cancelled()


def _provision_flow(args, *, already_confirmed: bool = False) -> int:
    """Download and provision a private R (the original, unchanged behaviour)."""
    print(f"robstattm-py setup   ->   {paths.root()}")
    print()
    print(provision.licence_notice())
    print()

    if not (already_confirmed or _confirm(args)):
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


def run(args) -> int:
    """Execute ``setup``."""
    if args.use_system_r:
        return _use_system_r(args)
    if _can_prompt(args):
        return _interactive_setup(args)
    return _provision_flow(args)


__all__ = ["add_parser", "run"]
