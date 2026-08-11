"""Prove the *shipped wheel* works, not just the source checkout.

Run this with the interpreter of a virtual environment that has the built wheel
installed, so it exercises what a user actually receives::

    python -m venv /tmp/check
    /tmp/check/bin/pip install dist/robstattm_py-*.whl
    /tmp/check/bin/python dev/_verify_wheel_install.py

Removes R from ``PATH`` and unsets ``R_HOME`` first, so the discovery chain has
to find R the hard way — the situation a user with a default CRAN install on
Windows is in.
"""
from __future__ import annotations

import os
import shutil
import sys

EXPECTED = (15.20121743027, 0.01256149584777)


def scrub_r_from_path() -> None:
    """Remove any R directory from ``PATH`` and drop ``R_HOME``."""
    os.environ.pop("R_HOME", None)
    separator = os.sep
    marker = f"{separator}R{separator}"
    kept = [
        entry
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and "R-4." not in entry and marker not in entry
    ]
    os.environ["PATH"] = os.pathsep.join(kept)


def main() -> int:
    """Check the installed wheel imports, finds R, and computes correctly."""
    scrub_r_from_path()
    print(f"  R on PATH        : {shutil.which('R')}")
    print(f"  R_HOME           : {os.environ.get('R_HOME')}")

    import robstattm_py as rpm
    from robstattm_py._renv import r_home_info

    print(f"  package version  : {rpm.__version__}")
    print(f"  installed from   : {rpm.__file__}")

    fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
    info = r_home_info()
    print(f"  resolved R via   : {info.source}")
    print(f"  R version        : {info.version_string}")
    print(f"  coefficients     : {fit.coefficients}")

    problems = []
    if rpm.__version__ != "0.1.0":
        problems.append(f"version is {rpm.__version__}, expected 0.1.0")
    for index, expected in enumerate(EXPECTED):
        actual = float(fit.coefficients[index])
        if abs(actual - expected) > 1e-9:
            problems.append(f"coefficient[{index}] = {actual!r}, expected ~{expected}")

    if problems:
        print("\n  FAILED:")
        for problem in problems:
            print(f"    - {problem}")
        return 1

    print("\n  WHEEL END-TO-END: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
