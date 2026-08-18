"""The command-line interface.

Mostly R-free: ``info`` never starts R, and ``doctor --no-start-r`` stops before
it would. The point of these tests is that the CLI stays *usable when things are
broken*, that is the only time anyone runs it.
"""
from __future__ import annotations

import json

import pytest

from robstattm_py._renv.errors import EXIT_NO_R, EXIT_OK, EXIT_USAGE
from robstattm_py.cli._main import build_parser, main


def _run(capsys, argv):
    """Run the CLI and return ``(exit_code, stdout, stderr)``."""
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def test_bare_invocation_prints_help_and_succeeds(capsys):
    code, out, _ = _run(capsys, [])
    assert code == EXIT_OK
    assert "doctor" in out and "info" in out


def test_version_flag(capsys):
    from robstattm_py import __version__

    code, out, _ = _run(capsys, ["--version"])
    assert code == EXIT_OK
    assert __version__ in out


def test_unknown_command_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["no-such-command"])
    assert excinfo.value.code == EXIT_USAGE


@pytest.mark.parametrize("command", ["doctor", "info"])
def test_every_subcommand_has_help(capsys, command):
    with pytest.raises(SystemExit) as excinfo:
        main([command, "--help"])
    assert excinfo.value.code == EXIT_OK
    out = capsys.readouterr().out
    assert out.strip()


def test_help_documents_the_exit_code_contract(capsys):
    """Users script against these; they must be discoverable, not folklore."""
    from robstattm_py._renv.errors import EXIT_CODE_MEANINGS

    parser = build_parser()
    epilog = parser.epilog or ""
    for code in EXIT_CODE_MEANINGS:
        assert str(code) in epilog


def test_help_documents_the_environment_variables():
    parser = build_parser()
    epilog = parser.epilog or ""
    for name in ("ROBSTATTM_HOME", "ROBSTATTM_R_HOME", "ROBSTATTM_R_MODE"):
        assert name in epilog


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


def test_info_creates_nothing_and_always_succeeds(capsys, tmp_path, monkeypatch):
    root = tmp_path / "rtm-home"
    monkeypatch.setenv("ROBSTATTM_HOME", str(root))

    code, out, _ = _run(capsys, ["info"])

    assert code == EXIT_OK
    assert str(root) in out
    assert not root.exists(), "`info` must not create its own directories"


def test_info_json_is_parseable_and_complete(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    code, out, _ = _run(capsys, ["info", "--json"])

    assert code == EXIT_OK
    data = json.loads(out)
    assert {"version", "platform_subdir", "paths", "disk", "environment"} <= set(data)
    assert data["paths"]["root"] == str(tmp_path / "rtm-home")


def test_info_reports_the_active_home_override(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "elsewhere"))
    _, out, _ = _run(capsys, ["info"])
    assert str(tmp_path / "elsewhere") in out


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def test_doctor_without_starting_r_is_inert(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    code, out, _ = _run(capsys, ["doctor", "--no-start-r"])

    assert "robstattm-py doctor" in out
    assert "Python" in out
    assert code in (EXIT_OK, EXIT_NO_R)


def test_doctor_json_shape(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    _, out, _ = _run(capsys, ["doctor", "--no-start-r", "--json"])

    data = json.loads(out)
    assert {"ok", "python", "rpy2", "r", "discovery_trace", "problems"} <= set(data)
    assert isinstance(data["discovery_trace"], list)


def test_doctor_reports_no_r_with_the_trace_and_the_right_exit_code(
    capsys, tmp_path, monkeypatch
):
    """The failing case is the one that matters: it must explain itself."""
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    monkeypatch.setenv("ROBSTATTM_R_MODE", "provisioned")  # nothing provisioned here

    code, out, _ = _run(capsys, ["doctor", "--no-start-r"])

    assert code == EXIT_NO_R
    assert "not found" in out
    assert "Where we looked" in out
    assert "robstattm-py setup" in out
    assert "NOT READY" in out


def test_doctor_json_exposes_the_discovery_source(capsys, tmp_path, monkeypatch):
    """CI asserts on this to prove a clean-machine run really used our R."""
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    _, out, _ = _run(capsys, ["doctor", "--no-start-r", "--json"])

    data = json.loads(out)
    if data["r"] is not None:
        assert data["r"]["source"]
        assert data["r"]["home"]


def test_doctor_json_stays_parseable_when_something_prints(
    capsys, tmp_path, monkeypatch
):
    """Regression: rpy2's binding-fallback message corrupted `--json`.

    Starting R can print to stdout without asking. rpy2 announces an API-to-ABI
    fallback whenever it was built against a different R than the one found,
    which is routine on macOS:

        Error importing in API mode: ImportError(...)
        Trying to import in ABI mode.

    That landed in front of the JSON and made `doctor --json` unparseable for
    anything consuming it, which is how CI found it.
    """
    import robstattm_py.cli._doctor as doctor_module

    real_collect = doctor_module.collect_report

    def _noisy_collect(**kwargs):
        print("Error importing in API mode: ImportError(...)")
        print("Trying to import in ABI mode.")
        return real_collect(**kwargs)

    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    monkeypatch.setattr(doctor_module, "collect_report", _noisy_collect)

    _, out, err = _run(capsys, ["doctor", "--no-start-r", "--json"])

    json.loads(out)  # must parse; the assertion is that this does not raise
    assert "API mode" in err, "the message must be preserved, just moved"


def test_doctor_verbose_always_shows_the_trace(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    _, out, _ = _run(capsys, ["doctor", "--no-start-r", "-v"])
    assert "Where we looked" in out


# ---------------------------------------------------------------------------
# install hints
# ---------------------------------------------------------------------------


def test_install_hint_prefers_the_cli_for_a_provisioned_r(tmp_path):
    """A user with a provisioned R has no R console to type into."""
    from robstattm_py._renv.report import install_hint
    from robstattm_py._renv.validate import validate_r_home

    from .conftest import make_probe, make_r_home

    home = make_r_home(tmp_path, system="Linux")
    info = validate_r_home(
        home, probe=make_probe(system="Linux", machine="x86_64"), source="provisioned"
    )

    hint = install_hint(["pense"], info)
    assert "robstattm-py install-r-packages pense" in hint
    assert "install.packages" not in hint


def test_install_hint_offers_both_routes_for_a_system_r(tmp_path):
    from robstattm_py._renv.report import install_hint
    from robstattm_py._renv.validate import validate_r_home

    from .conftest import make_probe, make_r_home

    home = make_r_home(tmp_path, system="Linux")
    info = validate_r_home(
        home, probe=make_probe(system="Linux", machine="x86_64"), source="path:R"
    )

    hint = install_hint(["pense", "GSE"], info)
    assert "robstattm-py install-r-packages pense GSE" in hint
    assert "install.packages" in hint


def test_install_hint_without_any_r():
    from robstattm_py._renv.report import install_hint

    assert "install-r-packages" in install_hint(["RobStatTM"], None)


def test_every_command_named_in_a_hint_actually_exists():
    """Guard against telling users to run a command we never implemented.

    The "package X is not installed" errors point at
    `robstattm-py install-r-packages`; if that subcommand were removed or
    renamed, the advice would silently become a dead end.
    """
    from robstattm_py._renv.report import install_hint

    hint = install_hint(["RobStatTM"], None)
    parser = build_parser()
    subcommands = {
        name
        for action in parser._subparsers._group_actions  # noqa: SLF001 - argparse has no public API
        for name in action.choices
    }
    referenced = {
        word
        for line in hint.splitlines()
        if "robstattm-py " in line
        for word in [line.split("robstattm-py ", 1)[1].split()[0]]
    }
    assert referenced, "hint mentions no command"
    assert referenced <= subcommands, f"hint references unknown command(s): {referenced - subcommands}"


# ---------------------------------------------------------------------------
# install-r-packages
# ---------------------------------------------------------------------------


def test_install_r_packages_dry_run_changes_nothing(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))

    code, out, _ = _run(capsys, ["install-r-packages", "RobStatTM", "--dry-run"])

    if "no R was found" in out:
        pytest.skip("no R available on this machine")
    assert code == EXIT_OK
    assert "Would run:" in out
    assert "install.packages" in out
    assert not (tmp_path / "rtm-home").exists()


def test_install_r_packages_always_pins_a_repository():
    """An unset `repos` makes R prompt for a mirror, which hangs a subprocess."""
    from robstattm_py.cli._install_pkgs import DEFAULT_REPOS, _r_expression

    expr = _r_expression(["RobStatTM"], DEFAULT_REPOS, None)
    assert 'repos = "https://' in expr


def test_install_r_packages_quotes_windows_paths_for_r(tmp_path):
    """R treats a backslash as an escape, so library paths must use forward slashes."""
    from robstattm_py.cli._install_pkgs import _r_expression

    expr = _r_expression(["pense"], "https://cloud.r-project.org", tmp_path / "lib")
    assert "\\" not in expr.split('lib = "', 1)[1].split('"', 1)[0]


def test_install_r_packages_reports_no_r_clearly(capsys, tmp_path, monkeypatch):
    """The CLI reports failures as an exit code plus a message; it never raises.

    A traceback escaping to the terminal would be a bug in its own right: this
    command exists to help people whose setup is already broken.
    """
    monkeypatch.setenv("ROBSTATTM_HOME", str(tmp_path / "rtm-home"))
    monkeypatch.setenv("ROBSTATTM_R_MODE", "provisioned")  # nothing provisioned

    code, _, err = _run(capsys, ["install-r-packages", "RobStatTM"])

    assert code == EXIT_NO_R
    assert "no R was found" in err
    assert "What to do:" in err
    assert "Traceback" not in err


def test_cli_never_lets_an_exception_escape(capsys, monkeypatch):
    """Any unexpected error must still become an exit code, not a crash."""
    import robstattm_py.cli._info as info_module

    def _boom(*_args, **_kwargs):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(info_module, "collect", _boom)

    from robstattm_py._renv.errors import EXIT_INTERNAL

    code, _, err = _run(capsys, ["info"])
    assert code == EXIT_INTERNAL
    assert "unexpected error" in err
