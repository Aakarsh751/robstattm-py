"""Strings meant for the console must survive a cp1252 console.

On Windows, ``sys.stdout.encoding`` is cp1252 whenever stdout is a pipe — which
is what happens under ``|``, under CI log capture, and under most tooling. A
character outside cp1252 does not print as a question mark there; it raises
``UnicodeEncodeError`` and takes the program with it.

``datasets.info()`` returned a string containing ``≈``, so
``print(rpm.datasets.info("mineral"))`` crashed on a stock Windows console. The
status glyphs in ``check_setup`` and ``doctor`` already guard themselves by
probing ``stdout.encoding``; these tests hold the line for the strings that do
not have such a guard, because they have no business needing one.
"""
from __future__ import annotations

import pytest

from robstattm_py import datasets

#: Every encoding a user-facing string is realistically asked to survive.
CONSOLE_ENCODINGS = ("cp1252", "ascii", "utf-8")


def _encodable(text: str, encoding: str) -> bool:
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


@pytest.mark.parametrize("name", datasets.available())
def test_info_is_printable_everywhere(name):
    text = datasets.info(name)
    for encoding in CONSOLE_ENCODINGS:
        assert _encodable(text, encoding), (
            f"datasets.info({name!r}) cannot be printed to a {encoding} console: "
            f"{text!r}"
        )


def test_available_names_are_printable():
    for name in datasets.available():
        assert _encodable(name, "ascii")


def test_info_still_says_something_useful():
    """The ASCII constraint must not have hollowed the message out."""
    text = datasets.info("mineral")
    assert "mineral" in text
    assert "53" in text and "2" in text  # the shape
    assert "Ch.5" in text


def test_unknown_dataset_message_is_printable():
    with pytest.raises(KeyError) as excinfo:
        datasets.info("no_such_dataset")
    assert _encodable(str(excinfo.value), "cp1252")
    assert "available()" in str(excinfo.value)
