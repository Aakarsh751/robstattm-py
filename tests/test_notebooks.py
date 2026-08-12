"""Execute every notebook end-to-end and assert no cell errors.

This is the D1 deliverable of ``docs/notebook_plan.md`` (policy D-019): a
notebook is "done" only when it executes clean in the same run as the unit
suite. Each notebook already carries a Windows ``R_HOME``/PATH bootstrap cell,
so no extra environment setup is needed here beyond what the unit tests use.

The notebooks need the R bridge (``@needs_r``) and are slow (each spins up R
and, for the gallery notebooks, several robust fits), so they are marked
``slow``. Set ``RPM_SKIP_NOTEBOOKS=1`` to skip the whole module during the
fast unit loop::

    RPM_SKIP_NOTEBOOKS=1 python -m pytest tests/ -q
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.conftest import needs_r

_REPO_ROOT = Path(__file__).resolve().parent.parent
_NB_DIR = _REPO_ROOT / "notebooks"


#: Notebooks that must never run here, with the reason.
#:
#: `colab_smoke_test` is written to be run *by a person, on Google Colab*: it
#: clones the repository, pip-installs it, and calls `robstattm-py setup`, which
#: downloads roughly 400 MB. Running that inside the unit suite would take
#: minutes, hit the network, and provision an R on top of whatever the machine
#: already has. Its purpose is to test an environment CI does not resemble,
#: which is exactly why CI must not be the thing that runs it.
_NOT_FOR_CI = {"colab_smoke_test.ipynb"}


def _discover_notebooks() -> list[Path]:
    if not _NB_DIR.is_dir():
        return []
    # Skip checkpoint copies Jupyter leaves behind, and empty/placeholder
    # notebooks (a 0-byte scratch file can't be valid JSON and would fail the
    # executor with an opaque NotJSONError).
    return sorted(
        p
        for p in _NB_DIR.rglob("*.ipynb")
        if ".ipynb_checkpoints" not in p.parts
        and p.stat().st_size > 0
        and p.name not in _NOT_FOR_CI
    )


_NOTEBOOKS = _discover_notebooks()

_SKIP_ALL = os.environ.get("RPM_SKIP_NOTEBOOKS") == "1"


def _nb_id(p: Path) -> str:
    return str(p.relative_to(_NB_DIR)).replace(os.sep, "/")


@needs_r
@pytest.mark.slow
@pytest.mark.skipif(_SKIP_ALL, reason="RPM_SKIP_NOTEBOOKS=1 set")
@pytest.mark.skipif(not _NOTEBOOKS, reason="no notebooks found")
@pytest.mark.parametrize("nb_path", _NOTEBOOKS, ids=[_nb_id(p) for p in _NOTEBOOKS])
def test_notebook_executes_clean(nb_path: Path):
    """Run the notebook via nbclient; fail on any CellExecutionError."""
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")

    nb = nbformat.read(str(nb_path), as_version=4)
    client = nbclient.NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        # Execute relative to the notebook's own directory so that its
        # `figures/` writes and any relative loads resolve the same way they
        # do when a user runs it interactively.
        resources={"metadata": {"path": str(nb_path.parent)}},
    )
    client.execute()
