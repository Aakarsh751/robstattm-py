"""Choose rpy2's binding before importing it, and never misreport the failure.

Two bugs, both found on Google Colab.

**The diagnosis was wrong.** One `doctor` run printed, a few lines apart:

    rpy2
      version        3.6.7
    Problems
      x ... could not be started: rpy2 is not installed.

Both cannot be true. `from rpy2.robjects import ...` imports a package *and*
starts R, and both raise ImportError; the handler assumed the first and threw
away the message that said what had actually failed.

**The first fix was worse than the bug.** It caught the ImportError, purged
`sys.modules` of `rpy2.*`, set `RPY2_CFFI_MODE=ABI`, and re-imported. On Colab
that reported success and then failed on the very next line with

    cannot import name 'default_converter' from 'rpy2.robjects' (unknown location)

`(unknown location)` is a module with no `__file__` — a half-initialised import.
rpy2 embeds R as a **process-global singleton**, so once an import has tried to
load R the attempt cannot be undone; clearing `sys.modules` clears Python's view
and not the C state.

So the binding is now chosen *before* the first import, from what we know about
the R we are about to load, and the error path merely explains rather than
attempts a recovery that cannot work.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from robstattm_py import _r


class _Info:
    """Stand-in for RHomeInfo; only `conda_prefix` and `path` are consulted."""

    def __init__(self, conda_prefix=None, path=Path("/opt/R")):
        self.conda_prefix = conda_prefix
        self.path = path


@pytest.fixture(autouse=True)
def _clean_env():
    """Snapshot and restore RPY2_CFFI_MODE around every test in this file.

    Done by hand rather than with `monkeypatch.delenv`, because the code under
    test *sets* the variable itself. monkeypatch only restores what it changed,
    so a value written by `_select_cffi_mode` would survive into the rest of the
    session — and a stray `RPY2_CFFI_MODE=ABI` silently changes which rpy2
    binding every later test uses.
    """
    import os

    missing = object()
    saved = os.environ.get("RPY2_CFFI_MODE", missing)
    os.environ.pop("RPY2_CFFI_MODE", None)
    try:
        yield
    finally:
        os.environ.pop("RPY2_CFFI_MODE", None)
        if saved is not missing:
            os.environ["RPY2_CFFI_MODE"] = saved


class TestSelectCffiMode:
    def test_provisioned_r_gets_abi(self):
        """rpy2 was almost certainly not built against an R we downloaded."""
        import os

        _r._select_cffi_mode(_Info(conda_prefix=Path("/opt/conda/envs/r")), modules={})
        assert os.environ["RPY2_CFFI_MODE"] == "ABI"

    def test_system_r_is_left_alone(self):
        """A system R is plausibly the one rpy2 was compiled against; keep the
        faster compiled binding. On Colab/Kaggle `pip` rebuilds rpy2 against the
        system R, so forcing ABI there broke a working path — hence this stays a
        no-op for a system R, and a broader hosted-notebook rule was reverted."""
        import os

        _r._select_cffi_mode(_Info(conda_prefix=None), modules={})
        assert "RPY2_CFFI_MODE" not in os.environ

    def test_an_explicit_setting_always_wins(self, monkeypatch):
        monkeypatch.setenv("RPY2_CFFI_MODE", "API")
        _r._select_cffi_mode(_Info(conda_prefix=Path("/opt/conda/envs/r")), modules={})
        import os

        assert os.environ["RPY2_CFFI_MODE"] == "API"

    def test_it_does_nothing_once_r_is_already_bound(self):
        """After openrlib is imported the choice is fixed; setting it would only
        mislead the next reader into thinking it had taken effect."""
        import os

        _r._select_cffi_mode(
            _Info(conda_prefix=Path("/opt/conda/envs/r")),
            modules={"rpy2.rinterface_lib.openrlib": object()},
        )
        assert "RPY2_CFFI_MODE" not in os.environ


class TestImportErrorMessage:
    def test_says_not_installed_only_when_it_really_is_not(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: False)
        err = _r._rpy2_import_error(ImportError("No module named 'rpy2'"))
        assert "rpy2 is not installed" in str(err)

    def test_it_does_not_claim_rpy2_is_missing_when_present(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        err = _r._rpy2_import_error(ImportError("undefined symbol: R_tryCatch"))
        text = str(err)
        assert "rpy2 is not installed" not in text
        assert "rpy2 is installed, but it could not load R" in text

    def test_it_quotes_the_real_error(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        err = _r._rpy2_import_error(ImportError("undefined symbol: R_tryCatch"))
        assert "undefined symbol: R_tryCatch" in str(err)

    def test_it_reports_the_mode_actually_in_effect(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        monkeypatch.setenv("RPY2_CFFI_MODE", "ABI")
        assert "ABI" in str(_r._rpy2_import_error(ImportError("boom")))

    def test_it_offers_the_remedies_that_apply(self, monkeypatch):
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        text = str(_r._rpy2_import_error(ImportError("boom")))
        assert "RPY2_CFFI_MODE=ABI" in text
        assert "--force-reinstall" in text
        assert "--use-system-r" in text

    def test_it_says_a_restart_is_required(self, monkeypatch):
        """The one thing a reader must know: it cannot be fixed in-process."""
        monkeypatch.setattr(_r, "_rpy2_is_installed", lambda: True)
        text = str(_r._rpy2_import_error(ImportError("boom")))
        assert "restart" in text.lower()
        assert "BEFORE Python starts" in text or "before any import" in text.lower()


def test_no_in_process_retry_remains():
    """Guard against reintroducing the retry.

    It looked like it worked — the fallback warning printed — and then the next
    import failed with "(unknown location)". Anyone tempted to add it back
    should read `_select_cffi_mode`'s docstring first.
    """
    assert not hasattr(_r, "_retry_in_abi_mode_or_raise")
    assert not hasattr(_r, "_purge_rpy2_modules")
