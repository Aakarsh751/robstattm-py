"""Shared helpers for formula-based regression wrappers."""
from __future__ import annotations

import re

import pandas as pd

from robstattm_py._r import r


def r_name_map(data: pd.DataFrame) -> dict[str, str]:
    """Return ``{python column name: R column name}`` for names that differ.

    Populated only for frames carrying ``attrs['r_columns']`` — i.e. the ones
    our dataset loaders produce, where ``copper.ppm`` became ``copper_ppm``.
    Empty for a frame the user built themselves, whose column names are already
    the only spelling there is.
    """
    r_cols = getattr(data, "attrs", {}).get("r_columns") if hasattr(data, "attrs") else None
    if r_cols is None or len(r_cols) != data.shape[1]:
        return {}
    return {
        str(py): str(rr)
        for py, rr in zip(data.columns, r_cols, strict=True)
        if str(py) != str(rr)
    }


def formula_to_r_names(formula: str, data: pd.DataFrame) -> str:
    """Rewrite Python-safe column names in ``formula`` to their R spellings.

    The frame is pushed to R under its original R column names (see
    :func:`df_with_r_names`), so a formula must ultimately speak R's spelling.
    But the frame the *caller* is holding shows the Python spelling — running
    ``rpm.datasets.shock()`` yields a column called ``n_shocks``, and writing
    ``"time ~ n_shocks"`` is the only reasonable thing to do with that. Before
    this rewrite it failed with R's ``object 'n_shocks' not found``, which
    points at nothing the caller can see.

    Both spellings now work. Substitution is on whole identifiers only, and the
    substitution table holds nothing but this frame's own columns, so a
    same-named function or variable elsewhere in the formula is untouched.
    """
    mapping = r_name_map(data)
    if not mapping:
        return formula
    # Longest first, so a name that is a prefix of another cannot shadow it.
    alternation = "|".join(
        re.escape(name) for name in sorted(mapping, key=len, reverse=True)
    )
    return re.sub(rf"\b(?:{alternation})\b", lambda m: mapping[m.group(0)], formula)


def df_with_r_names(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``data`` with original R column names restored.

    If ``data.attrs['r_columns']`` is populated (as for our dataset loaders),
    the returned frame uses those names so R-style formulas containing dots
    (``"y.var ~ x.var"``) resolve correctly when the frame is pushed to R.
    """
    r_cols = getattr(data, "attrs", {}).get("r_columns") if hasattr(data, "attrs") else None
    if r_cols is not None and len(r_cols) == data.shape[1]:
        out = data.copy()
        out.columns = list(r_cols)
        return out
    return data


def coef_names_for(
    formula: str, *, data_var: str = "rpm_data"
) -> tuple[str, ...]:
    """Return the coefficient names R will produce for ``formula``.

    Runs ``colnames(model.matrix(<formula>, data=<data_var>))`` against
    a data frame that **must already be present in R globalenv**
    under ``data_var``.  This produces the correct, fully-expanded
    coefficient names for every formula form:

    - explicit formulas:   ``"zinc ~ copper"``      → ``("(Intercept)", "copper")``
    - dot formulas:        ``"Y ~ ."``               → all predictors in ``data``
    - factor expansions:   ``"y ~ gender"``          → ``("(Intercept)", "genderM")``
    - interactions:        ``"y ~ a*b"``             → main effects + ``a:b``
    - no-intercept models: ``"y ~ -1 + x"``          → ``("x",)``

    Replaces ``coef_names_from_formula`` which called ``terms()``
    without a ``data=`` argument and crashed on dot formulas.
    """
    ro = r()
    expr = f'colnames(model.matrix({formula}, data={data_var}))'
    return tuple(str(n) for n in ro.r(expr))


# Back-compat alias — keep the public name stable for any callers.
def coef_names_from_fit(r_fit, *, formula: str | None = None,
                        data_var: str = "rpm_data") -> tuple[str, ...]:
    """Compatibility shim — prefers the formula+data approach."""
    if formula is not None:
        return coef_names_for(formula, data_var=data_var)
    # Last-ditch fallback: try reading off the converted fit (often empty).
    from robstattm_py._r import rx2
    coef_vec = rx2(r_fit, "coefficients")
    raw_names = getattr(coef_vec, "names", None)
    if raw_names is None or len(raw_names) == 0:
        raise RuntimeError(
            "coef_names_from_fit called without a formula and rpy2 stripped "
            "the names attribute from the fit's coefficients vector. Pass "
            "formula= and ensure the data is in R globalenv as 'rpm_data'."
        )
    return tuple(str(n) for n in raw_names)


def coef_names_from_formula(*args, **kwargs):  # pragma: no cover
    raise NotImplementedError(
        "coef_names_from_formula has been removed because it failed on "
        "dot formulas (`Y ~ .`).  Use coef_names_for(formula) instead."
    )


def push_df_to_r(data: pd.DataFrame, *, var_name: str = "rpm_data") -> None:
    """Push a DataFrame to R global env under ``var_name`` (no leading underscore)."""
    ro = r()
    ro.globalenv[var_name] = df_with_r_names(data)


def cleanup_r_var(var_name: str) -> None:
    ro = r()
    ro.r(f"if (exists('{var_name}')) rm({var_name})")


def resolve_formula_args(
    formula=None, data=None, *, X=None, y=None, y_name: str = "y"
):
    """Normalize the (formula, data) vs (X, y) invocation styles.

    Returns ``(formula_str, dataframe)``. Raises ``TypeError`` if the
    caller mixes the two forms or passes neither.
    """
    import pandas as pd

    formula_given = formula is not None or data is not None
    xy_given = X is not None or y is not None

    if formula_given and xy_given:
        raise TypeError(
            "Pass either (formula, data) OR (X, y), not both."
        )
    if formula_given:
        if formula is None or data is None:
            raise TypeError("Both `formula` and `data` are required.")
        if not isinstance(formula, str):
            raise TypeError(
                f"formula must be a str; got {type(formula).__name__}"
            )
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas.DataFrame")
        if data.empty:
            raise ValueError("data is empty")
        # Accept the column names the caller can actually see on their frame,
        # not only R's original spelling.
        return formula_to_r_names(formula, data), data
    if xy_given:
        if X is None or y is None:
            raise TypeError("Both `X` and `y` are required for the array form.")
        return xy_to_formula_and_data(X, y, y_name=y_name)
    raise TypeError(
        "Provide either (formula, data) or (X, y)."
    )


def xy_to_formula_and_data(
    X, y, *, y_name: str = "y"
) -> tuple[str, pd.DataFrame]:
    """Convert (X, y) array form to (formula_str, DataFrame).

    Supports the ``X, y`` invocation style promised by
    ``docs/user_interface.md §3``. Builds a frame whose columns are the
    response (``y_name``) followed by the predictors, then returns the
    formula ``"<y_name> ~ x1 + x2 + ..."``.

    Parameters
    ----------
    X : array-like or DataFrame, shape (n, p)
        Predictors. If a DataFrame, its column names are used; otherwise
        columns are named ``x0, x1, ...``.
    y : array-like, shape (n,)
        Response. If a ``pd.Series`` with a ``.name`` set, that name is
        used; otherwise ``y_name`` (default ``"y"``).
    y_name : str, default "y"
        Fallback response column name.

    Returns
    -------
    formula : str
    data : pandas.DataFrame
    """
    import numpy as np
    import pandas as pd

    # Resolve response column + name
    if isinstance(y, pd.Series):
        y_col = y_name if y.name is None else str(y.name)
        y_vals = y.to_numpy()
    else:
        y_col = y_name
        y_vals = np.asarray(y).ravel()

    if isinstance(X, pd.DataFrame):
        x_cols = [str(c) for c in X.columns]
        x_arr = X.to_numpy()
    else:
        x_arr = np.asarray(X)
        if x_arr.ndim == 1:
            x_arr = x_arr[:, None]
        x_cols = [f"x{i}" for i in range(x_arr.shape[1])]

    if x_arr.shape[0] != y_vals.shape[0]:
        raise ValueError(
            f"X has {x_arr.shape[0]} rows but y has length {y_vals.shape[0]}"
        )
    if y_col in x_cols:
        raise ValueError(
            f"Response column name {y_col!r} collides with a predictor "
            f"column. Pass ``y_name=`` or rename the predictor."
        )

    data = pd.DataFrame(x_arr, columns=x_cols)
    data.insert(0, y_col, y_vals)
    formula = f"{y_col} ~ " + " + ".join(x_cols)
    return formula, data
