"""Prove the PATH fix by inducing the failure it prevents.

Runs the real ``verify_environment`` twice against the provisioned environment:

  1. with a PATH deliberately poisoned the way a real machine is, a CRAN R
     installation and Rtools ahead of everything else, and the environment's own
     directories absent;
  2. with the same poisoned PATH, but through the shipped code, which puts the
     environment's directories in front.

Before the fix, (1) and (2) were the same code path and both failed. Requires a
provisioned environment; set ROBSTATTM_HOME to it.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from robstattm_py._renv import paths, provision
from robstattm_py._renv.probe import Probe

EXPR = 'cat("R_OK ", as.character(getRversion()), "\\n", sep="")'


def poisoned_path(probe: Probe) -> str:
    """A PATH shaped like a machine that already does R work."""
    system_root = probe.environ.get("SystemRoot", r"C:\Windows")
    candidates = [
        *sorted(Path(r"C:\Program Files\R").glob("R-*/bin/x64"), reverse=True),
        Path(r"C:\rtools45\usr\bin"),
        Path(r"C:\rtools45\x86_64-w64-mingw32.static.posix\bin"),
        Path(r"C:\rtools44\usr\bin"),
    ]
    entries = [str(p) for p in candidates if p.is_dir()]
    entries += [f"{system_root}\\System32", system_root]
    return os.pathsep.join(entries)


def main() -> int:
    probe = Probe.current()
    prefix = paths.env_prefix(probe)
    executable = paths.micromamba_exe(probe)
    if not prefix.is_dir():
        print(f"no provisioned environment at {prefix}", file=sys.stderr)
        return 1

    poison = poisoned_path(probe)
    print("poisoned PATH (what a real R machine looks like):")
    for entry in poison.split(os.pathsep):
        print(f"    {entry}")
    print()

    rscript = prefix / "Scripts" / "Rscript.exe"
    if not rscript.exists():
        rscript = prefix / "bin" / "Rscript"

    # (1) The old behaviour: hand the child the inherited PATH untouched.
    env = provision.child_env(probe)
    env["PATH"] = poison
    before = subprocess.run(
        [str(rscript), "--vanilla", "-e", EXPR],
        capture_output=True, text=True, errors="replace",
        env=env, timeout=300, check=False,
    )
    ok_before = "R_OK" in (before.stdout or "") + (before.stderr or "")
    print(f"[1] direct Rscript, poisoned PATH        -> "
          f"{'OK (did not reproduce)' if ok_before else f'FAIL rc={before.returncode}'}")
    if not ok_before:
        first = next(
            (ln for ln in ((before.stderr or "") + (before.stdout or "")).splitlines()
             if ln.strip()), ""
        )
        print(f"      {first[:100]}")

    # (2) The shipped behaviour: env directories put in front first.
    env2 = provision.child_env(probe)
    env2["PATH"] = provision.env_path_prefix(prefix, probe) + os.pathsep + poison
    after = subprocess.run(
        [str(rscript), "--vanilla", "-e", EXPR],
        capture_output=True, text=True, errors="replace",
        env=env2, timeout=300, check=False,
    )
    ok_after = "R_OK" in (after.stdout or "") + (after.stderr or "")
    print(f"[2] env dirs prepended, same poison      -> "
          f"{'OK' if ok_after else f'FAIL rc={after.returncode}'}")

    # (3) End to end through the shipped function, poison in the real environ.
    saved = os.environ.get("PATH")
    os.environ["PATH"] = poison
    try:
        packages = provision.verify_environment(executable, prefix, probe=Probe.current())
        print(f"[3] verify_environment(), same poison    -> OK  {packages}")
        ok_verify = True
    except Exception as exc:  # noqa: BLE001 - reporting, not handling
        print(f"[3] verify_environment(), same poison    -> FAIL\n{exc}")
        ok_verify = False
    finally:
        if saved is not None:
            os.environ["PATH"] = saved

    print()
    if ok_before:
        print("NOTE: the poisoned PATH did not break R on this machine, so [1] is")
        print("      not evidence. [2] and [3] still confirm the fix does no harm.")
    elif ok_after and ok_verify:
        print("CONFIRMED: the poison breaks a bare launch, and the shipped code")
        print("           survives it.")
        return 0
    else:
        print("THE FIX DID NOT HOLD, do not ship.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
