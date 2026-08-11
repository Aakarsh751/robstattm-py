"""Regression: the first thing you do in a session must not fail.

RobStatTM's ``KurtSDNew``/``initPP`` saves and restores the RNG state with an
unguarded read (``R/KurtSDNew.R:42``)::

    oldSeed <- get(".Random.seed", mode="numeric", envir=globalenv())

R does not create ``.Random.seed`` until the RNG is first used, so in a pristine
session that call raises. ``covRob`` and ``covRobRocke`` both route through it
(``R/Multirobu.R:123,359``), which made ``rpm.cov_rob(...)`` fail whenever it was
the first thing a user ran — including the example in our own README.

Interactive R users seldom notice, because something has usually drawn a random
number already. An embedded rpy2 session is pristine, so *every* user hit it.

``robstattm_py._r._ensure_random_seed_exists`` runs ``set.seed(NULL)`` at
startup when the variable is absent, which initialises the generator from the
clock without pinning it.

Each test runs in a subprocess: once R has started in the parent, the session is
no longer pristine and the bug cannot be observed.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from .conftest import child_preamble, needs_r, require_working_child_interpreter


def _fresh(code: str) -> subprocess.CompletedProcess:
    """Run ``code`` in a brand-new interpreter, and hence a brand-new R."""
    require_working_child_interpreter()
    return subprocess.run(
        [sys.executable, "-c", child_preamble() + textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


@needs_r
def test_random_seed_exists_once_r_starts():
    proc = _fresh(
        """
        from robstattm_py._r import r
        exists = r().r('exists(".Random.seed", envir = globalenv())')[0]
        print('EXISTS', bool(exists))
        """
    )
    assert proc.returncode == 0, proc.stderr
    assert "EXISTS True" in proc.stdout


@needs_r
@pytest.mark.parametrize(
    ("call", "label"),
    [
        ("rpm.cov_rob(rpm.datasets.wine())", "cov_rob"),
        ("rpm.cov_rob_rocke(rpm.datasets.wine())", "cov_rob_rocke"),
        ("rpm.kurt_sd_new(rpm.datasets.wine().to_numpy())", "kurt_sd_new"),
    ],
)
def test_stochastic_estimator_works_as_the_very_first_call(call, label):
    """No `set_seed` first — exactly how a new user follows the quickstart."""
    proc = _fresh(
        f"""
        import robstattm_py as rpm
        result = {call}
        print('OK {label}')
        """
    )
    assert proc.returncode == 0, f"{label} failed on a fresh session:\n{proc.stderr}"
    assert f"OK {label}" in proc.stdout


@needs_r
def test_startup_seeding_does_not_fix_the_rng():
    """`set.seed(NULL)` must leave results random, not pin them.

    If startup pinned a constant seed, two fresh processes would return
    identical draws — which would silently make every stochastic estimator
    deterministic and mask genuine reproducibility bugs.
    """
    code = """
        from robstattm_py._r import r
        print(r().r('runif(1)')[0])
        """
    first = _fresh(code)
    second = _fresh(code)
    assert first.returncode == 0 and second.returncode == 0
    assert first.stdout.strip() != second.stdout.strip(), (
        "two fresh sessions produced the same random draw — startup is pinning the seed"
    )


@needs_r
def test_set_seed_still_fully_determines_results():
    """Startup seeding must not weaken `set_seed`'s reproducibility guarantee."""
    code = """
        import robstattm_py as rpm
        rpm.set_seed(42)
        cov = rpm.cov_rob(rpm.datasets.wine())
        print(repr(float(cov.cov[0, 0])))
        """
    first = _fresh(code)
    second = _fresh(code)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout.strip() == second.stdout.strip()
