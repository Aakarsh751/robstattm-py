"""Isolate why a provisioned R fails to start, by varying only the PATH.

Run after `robstattm-py setup` has created an environment (even a failed one —
the environment exists; it is the *verify* step that failed).

    python dev/_diagnose_r_startup.py

The Windows "Mingw-w64 runtime failure: 32 bit pseudo relocation … out of
range" almost always means a mingw-built DLL was loaded from outside the
environment, so the loaded set spans more than 2 GB of address space. The usual
sources on a machine that already does R work are Rtools, MSYS2, Git's bundled
mingw, another conda environment, or a CRAN R.

Each scenario below launches the environment's own Rscript with a different
PATH and reports whether R prints its version. Whichever scenario first
succeeds names the culprit.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from robstattm_py._renv import paths
from robstattm_py._renv.probe import Probe

EXPR = 'cat("R_OK ", as.character(getRversion()), "\\n", sep="")'

#: PATH entries that ship a mingw runtime and can shadow the environment's.
HOSTILE = ("rtools", "msys", "mingw", r"\git\\", "/git/", "anaconda", "miniconda")


def scenarios(probe: Probe, prefix: Path) -> dict[str, str]:
    original = probe.environ.get("PATH", "")
    entries = [e for e in original.split(os.pathsep) if e]

    env_dirs = [
        prefix / "Library" / "bin",
        prefix / "Library" / "mingw-w64" / "bin",
        prefix / "Library" / "usr" / "bin",
        prefix / "Scripts",
        prefix / "bin",
        prefix,
    ]
    env_path = os.pathsep.join(str(d) for d in env_dirs if d.is_dir())

    def without_hostile(items: list[str]) -> list[str]:
        return [e for e in items if not any(h in e.lower() for h in HOSTILE)]

    def without_other_r(items: list[str]) -> list[str]:
        return [
            e for e in items
            if "\\r\\r-" not in e.lower() and "/r/r-" not in e.lower().replace("\\", "/")
        ]

    windows_only = [
        e for e in entries
        if e.lower().startswith(os.environ.get("SystemRoot", "C:\\Windows").lower())
    ]

    return {
        "inherited PATH (what setup does today)": original,
        "env dirs prepended to inherited PATH": env_path + os.pathsep + original,
        "inherited minus rtools/msys/mingw/git/conda": os.pathsep.join(
            without_hostile(entries)
        ),
        "inherited minus other R installations": os.pathsep.join(without_other_r(entries)),
        "env dirs + Windows system dirs only": os.pathsep.join(
            [env_path, *windows_only]
        ),
        "env dirs only": env_path,
    }


def main() -> int:
    probe = Probe.current()
    prefix = paths.env_prefix(probe)
    if not prefix.is_dir():
        print(f"no provisioned environment at {prefix}", file=sys.stderr)
        return 1

    rscript = next(
        (p for p in (
            prefix / "Scripts" / "Rscript.exe",
            prefix / "bin" / "Rscript.exe",
            prefix / "lib" / "R" / "bin" / "Rscript.exe",
            prefix / "bin" / "Rscript",
        ) if p.exists()),
        None,
    )
    if rscript is None:
        print(f"no Rscript found under {prefix}", file=sys.stderr)
        return 1

    print(f"prefix : {prefix}")
    print(f"Rscript: {rscript}\n")

    for label, path_value in scenarios(probe, prefix).items():
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CONDA", "MAMBA"))}
        env.pop("R_HOME", None)
        env.pop("R_LIBS", None)
        env.pop("R_LIBS_USER", None)
        env["PATH"] = path_value
        try:
            done = subprocess.run(
                [str(rscript), "--vanilla", "-e", EXPR],
                capture_output=True, text=True, errors="replace",
                env=env, timeout=180, check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT  {label}")
            continue

        combined = (done.stdout or "") + (done.stderr or "")
        if "R_OK" in combined:
            print(f"  OK       {label}")
        else:
            first = next(
                (ln for ln in combined.splitlines() if ln.strip()), f"exit {done.returncode}"
            )
            print(f"  FAIL     {label}\n             {first[:110]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
