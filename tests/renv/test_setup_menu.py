"""The interactive ``setup`` menu.

R-free: every branch is driven by stubbing discovery, ``input``, and the
provisioning call, so nothing here starts R or downloads anything.

The behaviour under test is the professor's guidance: if R already exists,
``setup`` should offer to *use* it (and default to that); if R does not exist,
it should *ask* rather than silently downloading. The non-interactive path
(scripts, CI) must keep provisioning exactly as before.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import robstattm_py.cli._setup as setup_mod
from robstattm_py._renv.errors import EXIT_CONFIRM_REQUIRED, EXIT_OK


def _args(**overrides):
    """A parsed-args stand-in with the defaults ``setup`` reads."""
    base = dict(
        use_system_r=False, yes=False, dry_run=False, force=False, quiet=False,
        channel="c", platform=None, micromamba_path=None, no_verify_checksum=False,
        insecure=False, timeout=300, force_unlock=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _fake_r(path="/opt/R", version="R version 4.5.2"):
    return SimpleNamespace(path=path, version_string=version)


@pytest.fixture
def answers(monkeypatch):
    """Feed a queue of answers to every ``input`` call."""
    queue: list[str] = []
    monkeypatch.setattr("builtins.input", lambda *_: queue.pop(0))
    return queue


@pytest.fixture(autouse=True)
def a_tty(monkeypatch):
    """Pretend stdin is a terminal so the menu path is taken."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)


# ---------------------------------------------------------------------------
# _can_prompt: only a real terminal with no intent-declaring flag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "over,expected",
    [
        ({}, True),
        ({"yes": True}, False),
        ({"dry_run": True}, False),
        ({"force": True}, False),
    ],
)
def test_can_prompt(over, expected):
    assert setup_mod._can_prompt(_args(**over)) is expected


def test_can_prompt_false_without_a_tty(monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert setup_mod._can_prompt(_args()) is False


# ---------------------------------------------------------------------------
# Existing R: default is to use it, download only on explicit choice
# ---------------------------------------------------------------------------


def test_existing_r_default_uses_it(monkeypatch, answers, capsys):
    monkeypatch.setattr(setup_mod, "discover_only",
                        lambda: SimpleNamespace(info=_fake_r()))
    called = {}
    monkeypatch.setattr(setup_mod, "_use_system_r",
                        lambda a: called.__setitem__("used", True) or EXIT_OK)
    monkeypatch.setattr(setup_mod, "_provision_flow",
                        lambda *a, **k: called.__setitem__("downloaded", True) or EXIT_OK)
    answers.append("")  # accept the default (option 1)

    assert setup_mod.run(_args()) == EXIT_OK
    assert called == {"used": True}, "an existing R must be used, not downloaded"
    assert "already available" in capsys.readouterr().out


def test_existing_r_can_still_choose_download(monkeypatch, answers):
    monkeypatch.setattr(setup_mod, "discover_only",
                        lambda: SimpleNamespace(info=_fake_r()))
    called = {}
    monkeypatch.setattr(setup_mod, "_use_system_r",
                        lambda a: called.__setitem__("used", True) or EXIT_OK)
    monkeypatch.setattr(setup_mod, "_provision_flow",
                        lambda *a, **k: called.__setitem__("downloaded", True) or EXIT_OK)
    answers.append("2")  # download anyway

    assert setup_mod.run(_args()) == EXIT_OK
    assert called == {"downloaded": True}


# ---------------------------------------------------------------------------
# No R: ask; do not silently download
# ---------------------------------------------------------------------------


def test_no_r_offers_download_and_path(monkeypatch, answers):
    monkeypatch.setattr(setup_mod, "discover_only",
                        lambda: SimpleNamespace(info=None))
    called = {}
    monkeypatch.setattr(setup_mod, "_provision_flow",
                        lambda *a, **k: called.__setitem__("downloaded", True) or EXIT_OK)
    answers.append("1")  # download

    assert setup_mod.run(_args()) == EXIT_OK
    assert called == {"downloaded": True}


def test_no_r_choose_existing_path(monkeypatch, answers, tmp_path):
    monkeypatch.setattr(setup_mod, "discover_only",
                        lambda: SimpleNamespace(info=None))
    pinned = {}
    monkeypatch.setattr(setup_mod, "validate_r_home",
                        lambda p, **k: _fake_r(path=str(p)))
    monkeypatch.setattr(setup_mod.state, "State",
                        lambda **kw: SimpleNamespace(save=lambda: pinned.update(kw)))
    answers.extend(["2", str(tmp_path / "R")])  # pick "enter a path", then the path

    assert setup_mod.run(_args()) == EXIT_OK
    assert pinned.get("spec_hash") == "system"
    assert str(tmp_path / "R") in pinned.get("r_home", "")


def test_cancel_changes_nothing(monkeypatch, answers, capsys):
    monkeypatch.setattr(setup_mod, "discover_only",
                        lambda: SimpleNamespace(info=None))
    monkeypatch.setattr(setup_mod, "_provision_flow",
                        lambda *a, **k: pytest.fail("must not provision on cancel"))
    answers.append("3")  # cancel

    assert setup_mod.run(_args()) == EXIT_OK
    assert "Cancelled" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Non-interactive path is unchanged
# ---------------------------------------------------------------------------


def test_non_interactive_still_provisions(monkeypatch):
    """--yes (or no TTY) must go straight to the provisioning flow, as before."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    called = {}
    monkeypatch.setattr(setup_mod, "_provision_flow",
                        lambda *a, **k: called.__setitem__("flow", True) or EXIT_OK)
    # discover_only must NOT be consulted on this path.
    monkeypatch.setattr(setup_mod, "discover_only",
                        lambda: pytest.fail("non-interactive path should not discover"))

    assert setup_mod.run(_args(yes=True)) == EXIT_OK
    assert called == {"flow": True}


def test_non_interactive_no_r_refuses_silent_download(monkeypatch, capsys):
    """Without a TTY and without --yes, the confirm guard still refuses."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(setup_mod.provision, "licence_notice", lambda: "(licence)")
    monkeypatch.setattr(setup_mod.provision, "provision",
                        lambda **k: pytest.fail("must not download without consent"))

    assert setup_mod.run(_args()) == EXIT_CONFIRM_REQUIRED
    assert "Refusing to download" in capsys.readouterr().err
