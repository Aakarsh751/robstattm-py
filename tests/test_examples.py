"""Every script in ``examples/`` must run.

An example that does not execute is worse than no example: it is documentation
that lies, and it lies most convincingly to the person least able to tell. So
each one is run end to end in a subprocess here, and a non-zero exit is a test
failure.

Subprocess rather than import, for three reasons: the scripts are meant to be
run as scripts and that is the path worth testing; rpy2 binds to one R per
process and several examples reseed R's RNG, so sharing a process would let one
example's state reach another; and a script that hangs or segfaults takes only
itself down.

Exit status 77 means the script announced a missing optional R package and
stopped — reported as a skip naming the package, not as a pass. See
``examples/_common.py``.

Set ``RPM_SKIP_EXAMPLES=1`` to skip the whole module during a fast unit loop.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

#: `_common.py` and `_ts.py` are shared helpers, not examples.
EXAMPLE_SCRIPTS = sorted(
    p for p in EXAMPLES_DIR.glob("*.py") if not p.name.startswith("_")
)

EXIT_SKIPPED = 77

#: Chapter 6/8 fits are genuinely slow — the autism variance-components fit and
#: the arima.rob searches run for minutes, not seconds.
TIMEOUT_SECONDS = 900

pytestmark = pytest.mark.skipif(
    os.environ.get("RPM_SKIP_EXAMPLES") == "1",
    reason="RPM_SKIP_EXAMPLES=1",
)


def test_every_r_script_has_a_python_port():
    """The README's map must stay complete as scripts are added or renamed."""
    readme = (EXAMPLES_DIR / "README.md").read_text(encoding="utf-8")
    missing = [p.name for p in EXAMPLE_SCRIPTS if p.name not in readme]
    assert not missing, f"examples/README.md does not mention: {missing}"


def test_scripts_were_discovered():
    """Guard against the glob silently matching nothing."""
    assert len(EXAMPLE_SCRIPTS) >= 25, (
        f"expected at least 25 example scripts, found {len(EXAMPLE_SCRIPTS)}"
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    "script", EXAMPLE_SCRIPTS, ids=[p.stem for p in EXAMPLE_SCRIPTS]
)
def test_example_runs(script: Path, tmp_path: Path):
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    # Never let an example provision R: that is a several-minute network
    # operation and has its own tests.
    env["ROBSTATTM_NO_PROVISION"] = "1"
    # UTF-8 so a Windows cp1252 pipe cannot fail a script for its output rather
    # than its statistics. The console-encodability of user-facing strings is
    # tested directly in tests/datasets/test_printable.py.
    env["PYTHONIOENCODING"] = "utf-8"

    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
        env=env,
        cwd=str(tmp_path),  # prove the script does not depend on the cwd
    )

    if completed.returncode == EXIT_SKIPPED:
        reason = _skip_reason(completed.stdout)
        pytest.skip(f"{script.name}: {reason}")

    assert completed.returncode == 0, (
        f"{script.name} exited {completed.returncode}\n"
        f"--- stdout ---\n{completed.stdout[-4000:]}\n"
        f"--- stderr ---\n{completed.stderr[-4000:]}"
    )
    assert completed.stdout.strip(), f"{script.name} printed nothing"


def _skip_reason(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("SKIPPED:"):
            return line.removeprefix("SKIPPED:").strip()
    return "optional dependency missing"
