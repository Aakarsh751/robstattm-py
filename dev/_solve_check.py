"""Check that our conda specification is satisfiable on a given platform.

micromamba can solve for a platform other than the one it is running on, so a
single Linux runner can verify all six targets for the cost of one small
download. That makes this the cheapest useful signal we have, and it covers the
two failures most likely to reach users:

* conda-forge drops or migrates a build we depend on (``r-base`` moves, and
  ``r-robstattm`` has not been rebuilt against it yet), and
* ``osx-arm64`` still has no ``r-robstattm`` / ``r-pyinit``, which decides
  whether Apple Silicon needs the source-build path at all.

Usage::

    python dev/_solve_check.py osx-arm64
"""
from __future__ import annotations

import argparse
import sys

from robstattm_py._renv import provision
from robstattm_py._renv.probe import SOURCE_BUILD_SUBDIRS, SUPPORTED_SUBDIRS


def main(argv: list[str] | None = None) -> int:
    """Solve for one platform and report what the solver chose."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subdir", choices=sorted(SUPPORTED_SUBDIRS))
    args = parser.parse_args(argv)

    specs = provision.package_spec(args.subdir)
    print(f"platform: {args.subdir}")
    print(f"spec:     {' '.join(specs)}")
    if args.subdir in SOURCE_BUILD_SUBDIRS:
        print(
            "note:     conda-forge has no r-robstattm/r-pyinit build here, so "
            "the spec\n"
            "          requests a compiler toolchain and they are built from "
            "CRAN source."
        )
    print()

    try:
        result = provision.solve_only(args.subdir)
    except provision.ProvisionError as exc:
        print(f"SOLVE FAILED for {args.subdir}\n", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    fetched = (result.get("actions") or {}).get("FETCH") or []
    if fetched:
        print(f"solver resolved {len(fetched)} packages, including:")
        interesting = ("r-base", "r-robstattm", "r-pyinit", "r-rrcov", "r-robustbase")
        for package in sorted(fetched, key=lambda p: p.get("name", "")):
            if package.get("name") in interesting:
                print(f"  {package.get('name'):<16} {package.get('version')}")
    else:
        print("solver reported no packages to fetch (already satisfied or dry-run only)")

    print(f"\nSOLVE OK for {args.subdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
