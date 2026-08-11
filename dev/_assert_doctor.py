"""Assert on ``robstattm-py doctor --json`` output. Used by CI.

Exists so the CI workflow can make a real claim about *which* R was used, in a
way that works identically on all three runner OSes (an inline heredoc does
not — the Windows runner defaults to PowerShell).

The ``--expect-source`` check is the important part. The CI job installs a
system R and never runs ``robstattm-py setup``, so discovery must land on that
system R; the provisioning job asserts the mirror image. Without pinning the
source, a bug could quietly make both jobs exercise the same path while still
reporting green.

Usage::

    python dev/_assert_doctor.py doctor.json --expect-source system
    python dev/_assert_doctor.py doctor.json --expect-source provisioned
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Validate a doctor report and return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="path to doctor --json output")
    parser.add_argument(
        "--expect-source",
        choices=("system", "provisioned", "any"),
        default="any",
        help="which discovery rung R must have come from",
    )
    parser.add_argument(
        "--allow-problems",
        action="store_true",
        help="tolerate reported problems (still requires that R was found)",
    )
    args = parser.parse_args(argv)

    try:
        # utf-8-sig, not utf-8: PowerShell's `>` redirection writes a BOM, and
        # a CI failure that turns out to be an encoding artifact wastes an hour.
        raw = args.report.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"FAIL: cannot read {args.report}: {exc}", file=sys.stderr)
        return 1

    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        # Show what was actually there. "Expecting value: line 1 column 1" is
        # indistinguishable between an empty file and one prefixed with library
        # chatter, and guessing between those cost a full CI round.
        print(f"FAIL: {args.report} is not valid JSON: {exc}", file=sys.stderr)
        if not raw.strip():
            print("  the file is empty", file=sys.stderr)
        else:
            print(f"  first 400 characters:\n{raw[:400]}", file=sys.stderr)
        return 1

    failures: list[str] = []

    r = report.get("r")
    if r is None:
        trace = report.get("discovery_trace", [])
        rendered = "\n".join(
            f"    {row['source']:<22} {row['path']}  -> {row.get('reason') or 'ok'}"
            for row in trace
        )
        failures.append("no R was found by auto-detection. Locations checked:\n" + rendered)
    else:
        source = r.get("source", "")
        is_provisioned = source == "provisioned"
        if args.expect_source == "system" and is_provisioned:
            failures.append(f"expected a system R, but discovery used {source!r}")
        elif args.expect_source == "provisioned" and not is_provisioned:
            failures.append(
                f"expected the provisioned R, but discovery used {source!r}; "
                "this run proves nothing about provisioning"
            )
        print(f"R {r.get('version')} ({r.get('arch')}) via {source}")
        print(f"  home: {r.get('home')}")

    rpy2 = report.get("rpy2") or {}
    print(f"rpy2 {rpy2.get('version')} ({rpy2.get('cffi_mode')} binding)")

    missing = [name for name, version in (report.get("r_packages") or {}).items() if not version]
    if missing:
        print(f"R packages not installed: {', '.join(missing)}")

    if not args.allow_problems:
        for problem in report.get("problems", []):
            if problem.get("severity") == "error":
                failures.append(f"[{problem.get('code')}] {problem.get('message')}")

    if failures:
        print("\nFAIL:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("doctor report OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
