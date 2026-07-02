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


class RobStatTMWarning(UserWarning):
    """A warning emitted by the underlying R code during a computation.

    R warnings (e.g. non-convergence notices, ``NaNs produced``, rank
    deficiency) are captured at the rpy2 bridge and re-emitted through
    Python's :mod:`warnings` machinery under this category, so users can

    * see them inline in a console / notebook, and
    * filter or promote them, e.g.::

          import warnings
          from robstatm_py import RobStatTMWarning

          with warnings.catch_warnings(record=True) as caught:
              warnings.simplefilter("always")
              fit = rpm.lmrobdet_mm("y ~ x", data=df)
          r_warnings = [w for w in caught
                        if issubclass(w.category, RobStatTMWarning)]

    The full list of messages from the most recent R call is also available
    via :func:`robstatm_py.last_r_warnings`.
    """
