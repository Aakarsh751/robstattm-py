"""Allow ``python -m robstattm_py.cli`` as well as the ``robstattm-py`` script.

Useful when the console script is not on ``PATH``, a common situation on
Windows, and exactly the kind of thing someone hits while trying to diagnose a
broken install.
"""
from __future__ import annotations

import sys

from robstattm_py.cli._main import main

if __name__ == "__main__":
    sys.exit(main())
