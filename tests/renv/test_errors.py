"""The error contract.

These are reflection tests. They exist so that adding a new failure mode cannot
silently produce a bare traceback or an undocumented exit status — the classic
way a CLI's error handling rots as features are added.
"""
from __future__ import annotations

import pytest

from robstattm_py._errors import RobStatTMSetupError
from robstattm_py._renv import errors


def _renv_error_subclasses() -> list[type[errors.RenvError]]:
    found: list[type[errors.RenvError]] = []
    stack = [errors.RenvError]
    while stack:
        cls = stack.pop()
        for sub in cls.__subclasses__():
            if sub not in found:
                found.append(sub)
                stack.append(sub)
    return found


def test_there_are_error_classes_to_check():
    assert _renv_error_subclasses(), "reflection found nothing — did the module move?"


@pytest.mark.parametrize("cls", _renv_error_subclasses(), ids=lambda c: c.__name__)
def test_every_error_has_a_stable_code(cls):
    assert cls.code.startswith("E_")
    assert cls.code != errors.RenvError.code, f"{cls.__name__} inherits the base code"


@pytest.mark.parametrize("cls", _renv_error_subclasses(), ids=lambda c: c.__name__)
def test_every_error_has_a_documented_exit_code(cls):
    assert cls.exit_code in errors.EXIT_CODE_MEANINGS, (
        f"{cls.__name__}.exit_code={cls.exit_code} is not in EXIT_CODE_MEANINGS"
    )


@pytest.mark.parametrize("cls", _renv_error_subclasses(), ids=lambda c: c.__name__)
def test_every_error_offers_a_concrete_remedy(cls):
    """A message that does not say what to do next is an unfinished message."""
    remedy = cls.default_remedy
    assert remedy and remedy.strip()
    assert len(remedy) > 25, f"{cls.__name__} remedy is too vague: {remedy!r}"


def test_error_codes_are_unique():
    codes = [c.code for c in _renv_error_subclasses()]
    assert len(codes) == len(set(codes)), f"duplicate codes: {codes}"


def test_exit_codes_are_all_documented():
    for value in errors.EXIT_CODE_MEANINGS.values():
        assert value.strip()


def test_renv_errors_are_catchable_as_the_existing_setup_error():
    """Existing `except RobStatTMSetupError` call sites must keep working."""
    for cls in _renv_error_subclasses():
        assert issubclass(cls, RobStatTMSetupError)


def test_message_layout_puts_the_remedy_last():
    exc = errors.NoRFoundError("Nothing found.", detail="Checked: nowhere")
    text = str(exc)
    assert text.index("Nothing found.") < text.index("Checked: nowhere")
    assert text.index("Checked: nowhere") < text.index("What to do:")


def test_custom_remedy_overrides_the_default():
    exc = errors.NoRFoundError("boom", remedy="do the specific thing")
    assert "do the specific thing" in str(exc)
    assert exc.remedy == "do the specific thing"


def test_short_message_excludes_the_decoration():
    """The trace shows short messages; they must stay one line."""
    exc = errors.InvalidRHomeError("bad path", detail="lots\nof\ndetail")
    assert exc.short_message == "bad path"
    assert "\n" not in exc.short_message


def test_missing_packages_are_carried_through():
    exc = errors.RPackagesMissingError("missing", missing=["RobStatTM", "pyinit"])
    assert exc.missing == ["RobStatTM", "pyinit"]
