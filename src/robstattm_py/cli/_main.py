"""The ``robstattm-py`` command-line entry point.

Deliberately small: each subcommand lives in its own module and exposes
``add_parser`` / ``run``. The only logic here is argument wiring and the
translation of exceptions into the documented exit codes, so that a new failure
mode cannot reach the user as a bare traceback.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from robstattm_py._renv.errors import (
    EXIT_CODE_MEANINGS,
    EXIT_INTERNAL,
    EXIT_OK,
    RenvError,
)

PROG = "robstattm-py"


def _epilog() -> str:
    """Document the exit-code contract in ``--help`` itself."""
    rows = "\n".join(
        f"  {code:<4} {meaning}" for code, meaning in sorted(EXIT_CODE_MEANINGS.items())
    )
    return (
        "exit codes:\n"
        f"{rows}\n\n"
        "environment:\n"
        "  ROBSTATTM_HOME     where the private R environment lives\n"
        "  ROBSTATTM_R_HOME   use this exact R, skipping auto-detection\n"
        "  ROBSTATTM_R_MODE   auto (default) | provisioned | system\n\n"
        f"docs: https://aakarsh751.github.io/{PROG}/"
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level parser with every subcommand attached."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Manage the R installation that robstattm-py uses. "
            "Start with `robstattm-py doctor` if something is not working."
        ),
        epilog=_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the robstattm-py version and exit",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    from robstattm_py.cli import _doctor, _info, _install_pkgs, _setup, _uninstall

    for module in (_setup, _doctor, _info, _install_pkgs, _uninstall):
        module.add_parser(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code.

    Never raises: every exception becomes an exit code plus a message on stderr.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        from robstattm_py import __version__

        print(f"{PROG} {__version__}")
        return EXIT_OK

    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return EXIT_OK

    try:
        return handler(args)
    except RenvError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - genuine bugs only
        import traceback

        traceback.print_exc()
        print(
            f"\n{PROG}: unexpected error: {exc}\n"
            f"Please report this at https://github.com/Aakarsh751/{PROG}/issues "
            "and include the traceback above.",
            file=sys.stderr,
        )
        return EXIT_INTERNAL


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
