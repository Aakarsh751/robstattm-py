"""``import robstattm_py`` must be inert.

Run in a subprocess with a scrubbed environment, because the checks are about
what happens at interpreter start — by the time an in-process test runs, the
package has already been imported by the collector.

Why this is worth a dedicated test: the package can download and install a
multi-gigabyte R environment. The line between "a library you imported" and "a
program that reconfigures your machine" is exactly this, and it is easy to
cross by accident with a well-meaning convenience default.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from ..conftest import child_env, child_preamble, require_working_child_interpreter


def _run(code: str, env_overrides: dict[str, str], tmp_path) -> subprocess.CompletedProcess:
    """Run ``code`` in a fresh interpreter with every R setting scrubbed."""
    require_working_child_interpreter()
    env = child_env(ROBSTATTM_HOME=str(tmp_path / "rtm-home"), **env_overrides)
    source = child_preamble() + textwrap.dedent(code)
    return subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        check=False,
    )


def test_import_does_not_start_r_or_load_rpy2(tmp_path):
    proc = _run(
        """
        import sys
        import robstattm_py
        assert 'rpy2.rinterface_lib.openrlib' not in sys.modules, 'rpy2 loaded R at import'
        assert 'rpy2.robjects' not in sys.modules, 'rpy2.robjects imported at import'
        assert robstattm_py.r_started() is False
        print('OK')
        """,
        {},
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_import_creates_no_directories(tmp_path):
    root = tmp_path / "rtm-home"
    proc = _run(
        """
        import os, pathlib
        import robstattm_py
        root = pathlib.Path(os.environ['ROBSTATTM_HOME'])
        assert not root.exists(), f'import created {root}'
        print('OK')
        """,
        {},
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout
    assert not root.exists()


def test_import_makes_no_network_calls(tmp_path):
    """Block the socket module outright; any connection attempt fails loudly."""
    proc = _run(
        """
        import socket

        class Blocked(Exception):
            pass

        def _forbidden(*a, **k):
            raise Blocked('network access during import')

        socket.socket = _forbidden
        socket.create_connection = _forbidden

        import robstattm_py  # noqa: F401
        print('OK')
        """,
        {},
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_import_succeeds_with_no_r_available(tmp_path):
    """A machine with no R must still import cleanly; only *use* should fail."""
    proc = _run(
        """
        import robstattm_py
        print('imported', robstattm_py.__version__)
        """,
        {"PATH": str(tmp_path), "ROBSTATTM_R_MODE": "provisioned"},
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert "imported" in proc.stdout


def test_missing_r_error_names_every_location_checked(tmp_path):
    """The failure must be a diagnosis, not just 'R not found'."""
    proc = _run(
        """
        import robstattm_py as rpm
        try:
            rpm.datasets.mineral()
        except rpm.RobStatTMSetupError as exc:
            text = str(exc)
            assert 'Locations checked' in text, text
            assert 'What to do' in text, text
            assert 'robstattm-py setup' in text, text
            print('DIAGNOSED')
        else:
            print('UNEXPECTED-SUCCESS')
        """,
        {"ROBSTATTM_R_MODE": "provisioned", "ROBSTATTM_NO_PROVISION": "1"},
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    if "UNEXPECTED-SUCCESS" in proc.stdout:
        pytest.skip("a provisioned R exists on this machine")
    assert "DIAGNOSED" in proc.stdout
