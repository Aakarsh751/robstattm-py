"""Shared fixtures for exploration tests, delegates to the main test harness."""
from __future__ import annotations

# Re-export so exploration tests can `from exploration.conftest import needs_r`
# or rely on pytest discovering this conftest when running `pytest exploration/`.
from tests.conftest import (  # noqa: F401
    R,
    assert_array_equal,
    assert_r_equal_dataclass,
    assert_scalar_equal,
    needs_r,
)
