"""Cross-language conversion primitives.

Pulling a value out of an R object is never quite one operation: the active
rpy2 conversion context may hand back an rpy2 vector, a 0-d numpy array, a
length-1 array, or an already-native scalar, depending on the call path. These
helpers absorb that variation so wrappers can state the type they want.

The R-field-name map for any given wrapper lives next to that wrapper, not
here — this module only provides the primitives.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def extract_scalar(rval: Any) -> Any:
    """Pull a 0-d / length-1 R vector into a native Python scalar.

    ``rval`` may be an rpy2 vector or an already-converted numpy scalar / array.
    """
    if rval is None:
        return None
    if isinstance(rval, np.ndarray):
        if rval.shape == ():
            return rval.item()
        if rval.size == 1:
            return rval.ravel()[0].item()
        return rval
    if hasattr(rval, "__len__") and len(rval) == 1:
        try:
            return rval[0]
        except Exception:
            pass
    return rval


def extract_array(rval: Any) -> np.ndarray:
    """Pull an R numeric vector / matrix into a numpy array."""
    arr = np.asarray(rval)
    return arr


def extract_int(rval: Any) -> int:
    """Pull a length-1 R integer into a Python int."""
    s = extract_scalar(rval)
    return int(s)


def extract_float(rval: Any) -> float:
    """Pull a length-1 R numeric into a Python float."""
    s = extract_scalar(rval)
    return float(s)


def extract_bool(rval: Any) -> bool:
    """Pull a length-1 R logical into a Python bool."""
    s = extract_scalar(rval)
    return bool(s)


def validate_1d_numeric(x: Any, name: str = "x") -> np.ndarray:
    """Coerce to a 1-D float64 numpy array; raise with a clear message otherwise."""
    try:
        arr = np.asarray(x, dtype=np.float64)
    except (TypeError, ValueError) as e:
        raise TypeError(
            f"{name} must be numeric and convertible to a float array; got {type(x).__name__}"
        ) from e
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-D; got shape {arr.shape}")
    if arr.size == 0:
        raise ValueError(f"{name} must be non-empty")
    return arr
