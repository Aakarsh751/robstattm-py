"""Cross-language seeding.

Per ``docs/architecture.md §4`` and ``docs/validation_strategy.md §2``,
``set_seed`` is the only allowed way to seed randomness in tests and example
notebooks; it sets both NumPy and R Mersenne-Twister states in one call.
"""
from __future__ import annotations

import numpy as np

from robstattm_py._r import r


def set_seed(value: int) -> None:
    """Seed NumPy and R with the same integer.

    Parameters
    ----------
    value : int
        Non-negative integer seed.

    Notes
    -----
    Calls ``np.random.seed(value)`` and ``R("set.seed(<value>)")``. The two
    Mersenne-Twister streams are independent: this function does not make them
    identical, only individually reproducible.

    Examples
    --------
    >>> from robstattm_py import set_seed
    >>> set_seed(20260601)
    """
    # ``bool`` is a subclass of ``int`` — reject it explicitly so ``set_seed(True)``
    # doesn't silently seed with 1.
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 0:
        raise ValueError(f"seed must be a non-negative integer; got {value!r}")
    # R's ``set.seed`` takes a 32-bit signed integer; a larger value becomes ``NA``
    # (with only a warning), silently breaking reproducibility. Catch it here.
    if int(value) >= 2**31:
        raise ValueError(
            f"seed must be < 2**31 ({2**31}) to fit R's 32-bit integer seed; "
            f"got {value!r}"
        )
    np.random.seed(int(value))
    r().r(f"set.seed({int(value)}L)")
