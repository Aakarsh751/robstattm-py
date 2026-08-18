"""Verify that R discovery finds a usable R in every supported situation.

Runs the same fit three ways, with ``R_HOME`` set, with only ``PATH``, and with
R removed from ``PATH`` entirely so only the Windows registry or the per-OS
install locations can find it, and asserts all three produce bit-identical
coefficients.

Each scenario runs in its own process, because rpy2 binds to an R when it is
first imported and the choice cannot be changed afterwards.

Usage::

    python dev/_verify_discovery_scenarios.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CHILD = """
import os, sys

if os.environ.pop("SCRUB_R_FROM_PATH", None):
    parts = os.environ.get("PATH", "").split(os.pathsep)
    keep = [p for p in parts if p and "R-4.5" not in p and not p.rstrip("\\\\").endswith("bin\\\\x64")]
    keep = [p for p in keep if os.sep + "R" + os.sep not in p]
    os.environ["PATH"] = os.pathsep.join(keep)

import robstattm_py as rpm
from robstattm_py._renv import r_home_info

fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
info = r_home_info()
print("RESULT|%s|%.12f|%.14f" % (info.source, fit.coefficients[0], fit.coefficients[1]))
"""


def main() -> int:
    """Run each scenario and compare the results."""
    r_home = os.environ.get("R_HOME") or r"C:\Program Files\R\R-4.5.2"
    scenarios: list[tuple[str, dict[str, str]]] = [
        ("R_HOME set explicitly", {"R_HOME": r_home}),
        ("no R_HOME (PATH only)", {}),
        ("no R_HOME, R off PATH", {"SCRUB_R_FROM_PATH": "1"}),
    ]

    # Start from an environment with no R or robstattm settings, so each
    # scenario is defined only by what it adds back.
    base = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("R_", "ROBSTATTM_"))
    }

    results: list[tuple[str, str]] = []
    failures = 0
    for name, extra in scenarios:
        env = dict(base)
        env.update(extra)
        completed = subprocess.run(  # noqa: S603 - fixed argv
            [sys.executable, "-c", CHILD],
            capture_output=True,
            text=True,
            env=env,
            timeout=900,
            check=False,
        )
        line = next(
            (ln for ln in completed.stdout.splitlines() if ln.startswith("RESULT|")), None
        )
        if line is None:
            failures += 1
            tail = (completed.stderr or "").strip().splitlines()[-3:]
            print(f"  {name:<24} FAILED\n      " + "\n      ".join(tail))
            continue
        _, source, c0, c1 = line.split("|")
        results.append((c0, c1))
        print(f"  {name:<24} via {source:<14} coef=[{c0}, {c1}]")

    if failures:
        print(f"\n{failures} scenario(s) failed")
        return 1
    if len(set(results)) != 1:
        print(f"\nResults differ across scenarios: {results}")
        return 1
    print("\nAll scenarios found R and agree bit-for-bit.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.exit(main())
