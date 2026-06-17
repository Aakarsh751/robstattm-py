"""Exception hierarchy.

See ``docs/architecture.md §3.2`` and ``docs/user_interface.md §7``.
"""
from __future__ import annotations


class RobStatTMError(RuntimeError):
    """Base class for all robstatm_py errors."""


class RobStatTMSetupError(RobStatTMError):
    """R, rpy2, or a required CRAN package is unavailable.

    Carries the missing-package list in ``.missing``.
    """

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing: list[str] = missing or []


class RobStatTMRError(RobStatTMError):
    """The underlying R call raised an error.

    The R traceback (if available) is attached as ``.r_traceback``.
    A curated remediation hint may be attached as ``.hint``.
    """

    def __init__(
        self,
        message: str,
        *,
        r_traceback: str | None = None,
        hint: str | None = None,
    ) -> None:
        full = message
        if hint:
            full = f"{full}\n\nHint: {hint}"
        if r_traceback:
            full = f"{full}\n\nR traceback:\n{r_traceback}"
        super().__init__(full)
        self.r_traceback: str | None = r_traceback
        self.hint: str | None = hint
