"""Never say "rpy2 is not installed" when rpy2 is installed.

Reported from Google Colab. `robstattm-py doctor` printed, in one report:

    rpy2
      version        3.6.7
    ...
    Problems
      x [E_R_START_FAILED] R was found at ... but could not be started:
        rpy2 is not installed. Install with `pip install rpy2>=3.6`.

Both statements cannot be true. `from rpy2.robjects import ...` does two
unrelated things — imports a Python package, and *loads R* — and both raise
ImportError. The handler assumed the first, reported it as fact, and discarded
the message that said what had actually gone wrong.

The usual real cause is rpy2's compiled binding having been built against a
different R than the one being loaded, which is the normal state of affairs
wherever rpy2 arrives prebuilt (Colab, a distro package) and the R is one we
provisioned. rpy2 ships an ABI binding that resolves symbols at run time and is
immune, so one automatic retry is worth making before giving up.

These tests are R-free: they drive the error paths directly.
"""
from __future__ import annotations

import sys

import pytest

from robstattm_py import _r
from robstattm_py._errors import RobStatTMSetupError


@pytest.fixture(autouse=True)
def _no_ambient_abi(monkeypatch):
    monkeypatch.delenv("RPY2_CFFI_MODE", raising=False)


class TestRpy2GenuinelyMissing:
    def test_says_so_when_rpy2_really_is_absent(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: False)
        with pytest.raises(RobStatTMSetupError) as excinfo:
            _r._retry_in_abi_mode_or_raise(ImportError("No module named 'rpy2'"))
        assert "rpy2 is not installed" in str(excinfo.value)
        assert "pip install rpy2" in str(excinfo.value)


class TestRpy2PresentButRWillNotLoad:
    """The Colab case."""

    def test_it_does_not_claim_rpy2_is_missing(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        monkeypatch.setattr(_r, "_purge_rpy2_modules", lambda: None)

        def explode(*_a, **_k):
            raise ImportError("libR.so: cannot open shared object file")

        monkeypatch.setitem(sys.modules, "rpy2.robjects", None)
        monkeypatch.setattr(_r, "_quiet_rpy2_probe", _raising_cm(explode))

        with pytest.raises(RobStatTMSetupError) as excinfo:
            _r._retry_in_abi_mode_or_raise(ImportError("undefined symbol: R_tryCatch"))

        text = str(excinfo.value)
        assert "rpy2 is not installed" not in text
        assert "rpy2 is installed, but it could not load R" in text

    def test_it_quotes_the_real_error(self, monkeypatch):
        """The message that names the cause must survive to the user."""
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        monkeypatch.setattr(_r, "_purge_rpy2_modules", lambda: None)
        monkeypatch.setattr(
            _r, "_quiet_rpy2_probe",
            _raising_cm(lambda: (_ for _ in ()).throw(ImportError("second failure"))),
        )

        with pytest.raises(RobStatTMSetupError) as excinfo:
            _r._retry_in_abi_mode_or_raise(ImportError("undefined symbol: R_tryCatch"))

        text = str(excinfo.value)
        assert "undefined symbol: R_tryCatch" in text
        assert "second failure" in text

    def test_it_offers_the_remedies_that_apply(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        monkeypatch.setattr(_r, "_purge_rpy2_modules", lambda: None)
        monkeypatch.setattr(
            _r, "_quiet_rpy2_probe",
            _raising_cm(lambda: (_ for _ in ()).throw(ImportError("nope"))),
        )
        with pytest.raises(RobStatTMSetupError) as excinfo:
            _r._retry_in_abi_mode_or_raise(ImportError("undefined symbol"))

        text = str(excinfo.value)
        assert "RPY2_CFFI_MODE=ABI" in text
        assert "--force-reinstall" in text
        assert "--use-system-r" in text

    def test_the_environment_is_left_clean_after_a_failed_retry(self, monkeypatch):
        """A failed ABI attempt must not leave RPY2_CFFI_MODE set for later code."""
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        monkeypatch.setattr(_r, "_purge_rpy2_modules", lambda: None)
        monkeypatch.setattr(
            _r, "_quiet_rpy2_probe",
            _raising_cm(lambda: (_ for _ in ()).throw(ImportError("nope"))),
        )
        import os

        with pytest.raises(RobStatTMSetupError):
            _r._retry_in_abi_mode_or_raise(ImportError("x"))
        assert "RPY2_CFFI_MODE" not in os.environ

    def test_it_does_not_retry_when_already_in_abi_mode(self, monkeypatch):
        """Retrying the identical configuration would just fail again, slower."""
        monkeypatch.setenv("RPY2_CFFI_MODE", "ABI")
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        called = []
        monkeypatch.setattr(_r, "_purge_rpy2_modules", lambda: called.append(1))

        with pytest.raises(RobStatTMSetupError):
            _r._retry_in_abi_mode_or_raise(ImportError("undefined symbol"))
        assert called == [], "should not have attempted a retry"


class TestPurge:
    """Against an isolated mapping, never the live ``sys.modules``.

    The first version of this test called ``_purge_rpy2_modules()`` with no
    argument. ``monkeypatch.setitem`` restores the keys *it* set, but the purge
    also removed the genuinely-loaded rpy2 modules it had not set — so the rest
    of the session ran against a half-unloaded rpy2, and 27 tests in other files
    failed with ``module 'rpy2.rinterface_lib' has no attribute 'openrlib'``.
    That is why the function takes a mapping.
    """

    def test_it_removes_partially_imported_rpy2_modules(self):
        modules = {
            "rpy2": object(),
            "rpy2.robjects": object(),
            "rpy2.rinterface_lib.openrlib": object(),
            "rpy2_something_else": object(),
            "numpy": object(),
        }
        _r._purge_rpy2_modules(modules)

        assert "rpy2" not in modules
        assert "rpy2.robjects" not in modules
        assert "rpy2.rinterface_lib.openrlib" not in modules
        # A module that merely starts with the same letters is not ours to drop.
        assert "rpy2_something_else" in modules
        assert "numpy" in modules

    def test_this_file_leaves_the_live_module_table_intact(self):
        """Guard the guard: rpy2 must still be importable after the above."""
        assert _r._rpy2_is_installed()
        assert "rpy2" in sys.modules or _r._rpy2_is_installed()


def _raising_cm(fn):
    """Return a context manager factory whose __enter__ calls ``fn``."""
    import contextlib

    @contextlib.contextmanager
    def cm(*_a, **_k):
        fn()
        yield

    return cm
