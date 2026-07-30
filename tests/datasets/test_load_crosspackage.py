"""Tests for ``rpm.datasets.load(package, name)`` — cross-package loader."""
from __future__ import annotations

import pandas as pd
import pytest

import robstattm_py as rpm


def test_load_coleman_from_robustbase():
    df = rpm.datasets.load("robustbase", "coleman")
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (20, 6)
    assert set(df.columns) == {
        "salaryP", "fatherWc", "sstatus", "teacherSc", "motherLev", "Y",
    }


def test_load_preserves_r_metadata():
    df = rpm.datasets.load("robustbase", "coleman")
    assert df.attrs.get("r_package") == "robustbase"
    assert df.attrs.get("r_name") == "coleman"
    assert "r_columns" in df.attrs


def test_load_dot_renaming_to_underscore():
    """R columns with dots should become Python-safe with underscores.

    ``datasets::airquality`` has ``Solar.R`` and ``Temp`` columns —
    perfect for verifying the dot → underscore rename.  Uses base R's
    ``datasets`` package which is always available and never needs to
    be attached.
    """
    df = rpm.datasets.load("datasets", "airquality")
    assert all("." not in c for c in df.columns)
    assert "Solar_R" in df.columns
    # Original R column name must be preserved in attrs
    assert "Solar.R" in df.attrs["r_columns"]


def test_load_unknown_dataset_raises():
    with pytest.raises(rpm.RobStatTMRError):
        rpm.datasets.load("robustbase", "this_dataset_does_not_exist")


def test_load_in_module_dunder_all():
    assert "load" in rpm.datasets.__all__
