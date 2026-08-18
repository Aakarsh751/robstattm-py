"""Loaders for the 20 RobStatTM datasets.

Each loader returns a ``pandas.DataFrame`` whose values match R bit-for-bit
(verified by ``tests/datasets/test_datasets.py``). One exception: ``resex`` is
a numeric vector in R; loaded as a one-column DataFrame named ``resex``.

R dots in column names become Python underscores (e.g. ``copper.ppm`` ->
``copper_ppm``); the original R name is recoverable via ``df.attrs['r_columns']``.
"""
from __future__ import annotations

import functools
from collections.abc import Callable

import pandas as pd

from robstattm_py._r import r, r_pkg

# (R name, Python loader name, expected shape, source chapter, short description)
_DATASETS: tuple[tuple[str, str, tuple[int, int], int | None, str], ...] = (
    ("alcohol",     "alcohol",     (44, 7),  2,    "Alcohol solubility study"),
    ("algae",       "algae",       (90, 12), 5,    "Algae blooms - regression"),
    ("biochem",     "biochem",     (12, 2),  4,    "Biochem oxygen demand"),
    ("breslow.dat", "breslow_dat", (59, 12), 7,    "Breslow epilepsy GLM data"),
    ("bus",         "bus",         (218, 18),6,    "Bus rapid-transit images - PCA"),
    ("flour",       "flour",       (24, 1),  4,    "Flour aphlatoxin"),
    ("glass",       "glass",       (76, 7),  6,    "Glass composition - multivariate"),
    ("hearing",     "hearing",     (7, 7),   5,    "Hearing test"),
    ("image",       "image",       (1573, 6),6,    "Satellite image segmentation"),
    ("leuk.dat",    "leuk_dat",    (33, 3),  7,    "Leukemia survival GLM"),
    ("mineral",     "mineral",     (53, 2),  5,    "Mineral content - flagship regression"),
    ("neuralgia",   "neuralgia",   (18, 5),  7,    "Neuralgia clinical trial"),
    ("oats",        "oats",        (40, 4),  4,    "Oat yield agricultural trial"),
    ("resex",       "resex",       (89, 1),  2,    "Residence-time exit (numeric vector)"),
    ("shock",       "shock",       (16, 2),  5,    "Shock data"),
    ("skin",        "skin",        (39, 3),  7,    "Skin test - GLM"),
    ("stackloss",   "stackloss",   (21, 5),  4,    "Stackloss - Brownlee's classic dataset"),
    ("vehicle",     "vehicle",     (217, 18),6,    "Vehicle silhouettes"),
    ("waste",       "waste",       (40, 6),  5,    "Waste-management regression"),
    ("wine",        "wine",        (59, 13), 6,    "Italian wine cultivars - flagship multivariate"),
)


def _rcol_to_py(name: str) -> str:
    """R column name -> Python-safe (dots -> underscores)."""
    return name.replace(".", "_").replace(" ", "_")


#: R stores integer ``NA`` as ``INT_MIN``. rpy2's pandas conversion maps an
#: integer column to numpy ``int32``, which has no missing value, so the
#: sentinel survives as an ordinary number.
_R_INT_NA = -2147483648


def _restore_integer_na(df: pd.DataFrame) -> pd.DataFrame:
    """Turn R's integer-NA sentinel back into a real missing value.

    Without this, an integer column containing ``NA`` silently arrives as
    ``-2147483648``. Nothing raises, nothing warns, and every downstream number
    is wrong, ``mean()``, ``dropna()``, ``min()`` and any fit that touches the
    column. It was found via ``WWGbook::autism``, where two missing ``vsae``
    scores made a 41-child subset come out as 42 and left the estimator
    complaining about mismatched lengths rather than about the data.

    Converted to pandas' nullable ``Int64`` rather than to float, so the column
    stays integral and ``isna()`` answers correctly.

    Float columns need no handling: R's numeric ``NA`` is an NaN payload and
    already crosses as ``NaN``.
    """
    for column in df.columns:
        series = df[column]
        if series.dtype.kind not in "iu":
            continue
        mask = series == _R_INT_NA
        if mask.any():
            df[column] = series.astype("Int64").mask(mask)
    return df


@functools.lru_cache(maxsize=64)
def _load(r_name: str) -> pd.DataFrame:
    """Load a RobStatTM dataset into a DataFrame. Cached after first call."""
    # Ensure RobStatTM is attached so data() finds it
    r_pkg("RobStatTM")
    rr = r().r
    rr(f'data({r_name}, package="RobStatTM")')
    try:
        obj = rr(r_name)

        # Pull names then coerce to DataFrame
        if r_name == "resex":
            # numeric vector
            import numpy as np

            arr = np.asarray(obj, dtype=float)
            df = pd.DataFrame({"resex": arr})
        else:
            # rpy2 auto-converts data.frames to pandas under the active converter;
            # if conversion didn't apply, fall back to explicit conversion.
            if isinstance(obj, pd.DataFrame):
                df = obj.copy()
            else:
                from rpy2.robjects import pandas2ri

                df = pandas2ri.rpy2py(obj).copy()
    finally:
        # ``data()`` binds the dataset in globalenv; drop it so repeated loads
        # don't accumulate stray variables (conversion above is eager).
        rr(f'if (exists("{r_name}")) rm(list="{r_name}")')

    df = _restore_integer_na(df)

    # Preserve the original R column names as an attribute
    original_cols = list(df.columns)
    df.attrs["r_columns"] = tuple(original_cols)
    df.columns = [_rcol_to_py(c) for c in original_cols]
    df.attrs["r_name"] = r_name
    return df


def _make_loader(r_name: str, py_name: str, chapter: int | None, desc: str) -> Callable[[], pd.DataFrame]:
    def loader() -> pd.DataFrame:
        return _load(r_name).copy()  # defensive: callers shouldn't mutate the cache

    loader.__name__ = py_name
    loader.__qualname__ = f"datasets.{py_name}"
    chapter_str = f"Chapter {chapter}" if chapter else "-"
    loader.__doc__ = (
        f"{desc}.\n\n"
        f"From RobStatTM (R name: ``{r_name}``). {chapter_str} of Maronna et al. (2019).\n\n"
        f"Returns\n-------\n"
        f"pandas.DataFrame\n"
        f"    Column names with R dots converted to underscores. The original\n"
        f"    R column names are available via ``df.attrs['r_columns']``.\n"
    )
    return loader


def available() -> list[str]:
    """Return the Python loader names for all 20 RobStatTM datasets.

    Examples
    --------
    >>> from robstattm_py import datasets
    >>> "mineral" in datasets.available()
    True
    """
    return [py for _, py, _, _, _ in _DATASETS]


def load(package: str, name: str) -> pd.DataFrame:
    """Load a dataset from any installed R package.

    Convenience entry point that mirrors R's
    ``data(<name>, package="<package>")`` and returns the result as a
    pandas DataFrame.  Use this for datasets the textbook references
    that live in *other* packages (``robustbase``, ``MASS``, ``boot``,
    ...), the 20 RobStatTM-native datasets have their own named
    loaders (``datasets.mineral()``, etc.) and should be preferred
    when applicable because they cache and carry R-name metadata.

    Parameters
    ----------
    package : str
        R package name, e.g. ``"robustbase"``.
    name : str
        Dataset name within that package, e.g. ``"coleman"``.

    Returns
    -------
    pandas.DataFrame
        DataFrame whose columns mirror the R data.frame.  The original
        R column names are preserved in ``df.attrs['r_columns']`` so
        downstream wrappers can restore them when needed.  Column
        names are made Python-safe (dots → underscores).

    Raises
    ------
    robstattm_py.RobStatTMRError
        If R cannot find the dataset or the package is not installed.

    Examples
    --------
    >>> from robstattm_py import datasets
    >>> coleman = datasets.load("robustbase", "coleman")
    >>> coleman.shape
    (20, 6)
    """
    # NOTE: we deliberately do NOT attach the package with library(...).
    # ``data(name, package="pkg")`` loads the dataset into the current
    # environment without modifying the search path, which is critical:
    # attaching MASS, for example, masks ``RobStatTM::huber`` with
    # ``MASS::huber`` and silently breaks downstream psi-tuning code.
    rr = r().r
    try:
        rr(f'data({name}, package="{package}")')
        obj = rr(name)
    except Exception as e:
        from robstattm_py._errors import RobStatTMRError

        raise RobStatTMRError(
            f"R could not load dataset {name!r} from package {package!r}: {e}"
        ) from e

    try:
        if isinstance(obj, pd.DataFrame):
            df = obj.copy()
        else:
            try:
                from rpy2.robjects import pandas2ri

                df = pandas2ri.rpy2py(obj).copy()
                if not isinstance(df, pd.DataFrame):
                    df = pd.DataFrame(df)
            except Exception:
                df = pd.DataFrame({name: list(obj)})
    finally:
        # Drop the dataset binding ``data()`` left in globalenv (eager copy above).
        rr(f'if (exists("{name}")) rm(list="{name}")')

    df = _restore_integer_na(df)

    original_cols = list(df.columns)
    df.attrs["r_columns"] = tuple(original_cols)
    df.columns = [_rcol_to_py(c) for c in original_cols]
    df.attrs["r_name"] = name
    df.attrs["r_package"] = package
    return df


def info(name: str) -> str:
    """Return a one-line description of a dataset.

    Deliberately plain ASCII. This string's whole purpose is to be printed, and
    a Windows console defaults to cp1252 when stdout is a pipe, the ``~=`` used
    to be ``≈``, which is outside cp1252, so ``print(datasets.info("mineral"))``
    raised ``UnicodeEncodeError`` rather than telling anyone about the dataset.
    See ``tests/datasets/test_printable.py``.
    """
    for _r, py, shape, chap, desc in _DATASETS:
        if name in (_r, py):
            ch = f"Ch.{chap}" if chap else "-"
            return f"{py} ({_r}): {desc}. shape ~= {shape[0]}x{shape[1]}. {ch}"
    raise KeyError(f"unknown dataset {name!r}; see datasets.available()")


# Bind each loader as a module-level attribute (e.g. datasets.mineral)
for _r_name, _py_name, _shape, _chap, _desc in _DATASETS:
    globals()[_py_name] = _make_loader(_r_name, _py_name, _chap, _desc)


__all__ = ["available", "info", "load"] + [py for _, py, _, _, _ in _DATASETS]
