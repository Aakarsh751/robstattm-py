"""Shared input validation for covariance wrappers."""
from __future__ import annotations

import numpy as np
import pandas as pd


def validate_2d_numeric(
    X, *, name: str = "X", allow_nan: bool = False
) -> tuple[np.ndarray, tuple[str, ...] | None]:
    """Coerce to 2-D float64 array; return (array, column_names_or_None).

    Parameters
    ----------
    allow_nan : bool, default False
        If True, NaN entries are permitted (e.g. for GSE/TSGS missing-data
        estimators). Inf is always rejected.
    """
    col_names: tuple[str, ...] | None = None
    if isinstance(X, pd.DataFrame):
        col_names = tuple(X.columns.astype(str))
        # Preserve R names if datasets module attached them
        r_cols = X.attrs.get("r_columns") if hasattr(X, "attrs") else None
        if r_cols is not None and len(r_cols) == X.shape[1]:
            col_names = tuple(str(c) for c in r_cols)
        try:
            arr = X.to_numpy(dtype=np.float64)
        except (TypeError, ValueError) as e:
            raise TypeError(f"{name} contains non-numeric columns") from e
    else:
        try:
            arr = np.asarray(X, dtype=np.float64)
        except (TypeError, ValueError) as e:
            raise TypeError(f"{name} must be numeric and 2-D") from e
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D; got shape {arr.shape}")
    n, p = arr.shape
    if n == 0 or p == 0:
        raise ValueError(f"{name} must be non-empty; got shape {arr.shape}")
    if allow_nan:
        if np.isinf(arr).any():
            raise ValueError(f"{name} contains Inf values")
    else:
        if not np.isfinite(arr).all():
            raise ValueError(f"{name} contains NaN/Inf values")
    return arr, col_names
