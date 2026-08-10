"""The ``robstattm-py`` command-line interface.

Kept out of the package's import path on purpose: nothing in ``robstattm_py``
imports this, so the CLI's argparse machinery costs an ordinary user nothing.
"""
from __future__ import annotations

from robstattm_py.cli._main import build_parser, main

__all__ = ["build_parser", "main"]
