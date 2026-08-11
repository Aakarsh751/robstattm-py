"""Strict-tier tests: every RobStatTM dataset loads correctly and matches R."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r

# (Python loader name, R name, expected shape, has-numeric-only-check)
ALL_DATASETS = [
    ("alcohol",     "alcohol",     (44, 7)),
    ("algae",       "algae",       (90, 12)),
    ("biochem",     "biochem",     (12, 2)),
    ("breslow_dat", "breslow.dat", (59, 12)),
    ("bus",         "bus",         (218, 18)),
    ("flour",       "flour",       (24, 1)),
    ("glass",       "glass",       (76, 7)),
    ("hearing",     "hearing",     (7, 7)),
    ("image",       "image",       (1573, 6)),
    ("leuk_dat",    "leuk.dat",    (33, 3)),
    ("mineral",     "mineral",     (53, 2)),
    ("neuralgia",   "neuralgia",   (18, 5)),
    ("oats",        "oats",        (40, 4)),
    ("resex",       "resex",       (89, 1)),
    ("shock",       "shock",       (16, 2)),
    ("skin",        "skin",        (39, 3)),
    ("stackloss",   "stackloss",   (21, 5)),
    ("vehicle",     "vehicle",     (217, 18)),
    ("waste",       "waste",       (40, 6)),
    ("wine",        "wine",        (59, 13)),
]


def test_available_returns_all_20():
    names = rpm.datasets.available()
    assert len(names) == 20
    expected = {py for py, _r, _s in ALL_DATASETS}
    assert set(names) == expected


def test_info_returns_string():
    assert "mineral" in rpm.datasets.info("mineral")


def test_info_raises_on_unknown():
    with pytest.raises(KeyError):
        rpm.datasets.info("does_not_exist")


@needs_r
@pytest.mark.parametrize("py_name,r_name,expected_shape", ALL_DATASETS)
def test_shape_matches_r(py_name, r_name, expected_shape):
    loader = getattr(rpm.datasets, py_name)
    df = loader()
    assert isinstance(df, pd.DataFrame)
    assert df.shape == expected_shape, f"{py_name}: got {df.shape}, expected {expected_shape}"


@needs_r
@pytest.mark.parametrize("py_name,r_name,expected_shape", ALL_DATASETS)
def test_values_match_r(py_name, r_name, expected_shape):
    """Numeric columns of every dataset must match R bit-for-bit."""
    from robstattm_py._r import r

    ro = r()
    ro.r(f'data({r_name}, package="RobStatTM")')

    loader = getattr(rpm.datasets, py_name)
    df = loader()

    # Pull R numeric columns
    if py_name == "resex":
        r_vec = np.asarray(ro.r(r_name), dtype=float)
        np.testing.assert_array_equal(df["resex"].to_numpy(), r_vec)
        return

    # strict=True: a Python/R column-count mismatch is exactly the drift this
    # test exists to catch, so it must fail rather than compare only a prefix.
    for py_col, r_col in zip(df.columns, df.attrs["r_columns"], strict=True):
        # Determine if R column is numeric
        is_num = bool(ro.r(f'is.numeric({r_name}[["{r_col}"]])')[0])
        if not is_num:
            # Skip factor/character columns at this tier — those need
            # categorical-aware comparison (TODO Phase 2)
            continue
        r_col_vals = np.asarray(ro.r(f'as.numeric({r_name}[["{r_col}"]])'), dtype=float)
        py_col_vals = df[py_col].to_numpy(dtype=float)
        np.testing.assert_array_equal(
            py_col_vals,
            r_col_vals,
            err_msg=f"{py_name}.{py_col} (R: {r_col})",
        )


@needs_r
def test_r_columns_preserved():
    df = rpm.datasets.breslow_dat()
    assert "r_columns" in df.attrs
    # any dotted R names should remain in the attrs tuple
    assert all(isinstance(c, str) for c in df.attrs["r_columns"])


@needs_r
def test_cache_is_defensive_copy():
    """Mutating a returned DataFrame must not affect subsequent loads."""
    df1 = rpm.datasets.mineral()
    original_first = df1.iloc[0, 0]
    df1.iloc[0, 0] = -999.0
    df2 = rpm.datasets.mineral()
    assert df2.iloc[0, 0] == original_first
