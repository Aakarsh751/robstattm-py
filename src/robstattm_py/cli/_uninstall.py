"""``robstattm-py uninstall``, remove everything the package installed.

Deliberately conservative. It only ever deletes paths inside the directory this
package owns, and by default it keeps the downloaded package cache so that
setting up again takes seconds rather than minutes.
"""
from __future__ import annotations

import sys

from robstattm_py._renv import paths, provision
from robstattm_py._renv.errors import EXIT_CONFIRM_REQUIRED, EXIT_OK


def add_parser(subparsers) -> None:
    """Attach the ``uninstall`` subcommand."""
    parser = subparsers.add_parser(
        "uninstall",
        help="remove the private R environment",
        description=(
            "Delete the R environment and private R library that robstattm-py "
            "created. Never touches an R you installed yourself. With no "
            "selector, removes the environment and the private R library but "
            "keeps the download cache."
        ),
    )
    parser.add_argument("--env", action="store_true", help="remove the R environment")
    parser.add_argument("--rlibs", action="store_true", help="remove the private R library")
    parser.add_argument("--cache", action="store_true", help="remove downloads and logs")
    parser.add_argument("--all", action="store_true", help="remove everything")
    parser.add_argument("--yes", "-y", action="store_true", help="do not ask")
    parser.add_argument("--dry-run", action="store_true", help="show what would be removed")
    parser.set_defaults(_handler=run)


def _human(size: int) -> str:
    """Format a byte count."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"  # pragma: no cover


def run(args) -> int:
    """Execute ``uninstall``."""
    selected = args.env or args.rlibs or args.cache or args.all
    env = args.all or args.env or not selected
    rlibs = args.all or args.rlibs or not selected
    cache = args.all or args.cache

    planned = provision.uninstall(env=env, rlibs=rlibs, cache=cache, dry_run=True)
    if not planned:
        print(f"Nothing to remove under {paths.root()}.")
        return EXIT_OK

    total = sum(planned.values())
    print("Would remove:" if args.dry_run else "Removing:")
    for path, size in sorted(planned.items()):
        print(f"  {path}  ({_human(size)})")
    print(f"  total: {_human(total)}")

    if args.dry_run:
        return EXIT_OK

    if not args.yes:
        if not sys.stdin.isatty():
            print("\nRe-run with --yes to confirm.", file=sys.stderr)
            return EXIT_CONFIRM_REQUIRED
        if input("\nProceed? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled.")
            return EXIT_OK

    removed = provision.uninstall(env=env, rlibs=rlibs, cache=cache)
    print(f"\nReclaimed {_human(sum(removed.values()))}.")
    if not cache:
        print("Kept the download cache, so `robstattm-py setup` will be fast next time.")
    return EXIT_OK


__all__ = ["add_parser", "run"]
