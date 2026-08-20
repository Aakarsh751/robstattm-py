"""``compare()`` -- R's ``fit.models`` side-by-side view, from RobStatTM-Py.

Doug Martin: "there is a nice little fit.models package ... for comparing robust
versus classical model fits, which I find quite useful." This is the bridge to
it. Given two or more already-fitted RobStatTM-Py results on the same data,
:func:`compare` lines them up into R's ``lmfm`` object so its
``summary()``/``plot()`` show the coefficient tables and diagnostics next to each
other -- exactly the "easily see if lmrobdetMM produces a different result than
lm" comparison Doug asked for::

    ls  = rpm.lm("zinc ~ copper", data=df)
    rob = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    cmp = rpm.compare(LeastSquares=ls, Robust=rob)
    print(cmp.summary())     # R's summary.lmfm, both fits side by side
    cmp.plot(which=1)        # overlaid diagnostics

The heavy lifting (holding live R fits with their S3 class intact, calling
``fit.models``) lives in the published sibling package **fitmodels-py**, so this
is a thin delegation rather than a re-implementation. fitmodels-py is an optional
dependency; :func:`compare` raises a clear install hint if it is absent.
"""
from __future__ import annotations

from typing import Any

from robstattm_py._errors import RobStatTMSetupError
from robstattm_py.regression._formula import df_with_r_names

# RobStatTM-Py result class name -> the R estimator fit.models should call.
_ESTIMATOR_NAME: dict[str, str] = {
    "LmResult": "lm",
    "GlmResult": "glm",
    "RlmResult": "rlm",
    "LtsResult": "ltsReg",
    "LmrobResult": "lmrob",
    "LmrobdetMMResult": "lmrobdetMM",
    "LmrobMResult": "lmrobM",
    "LmrobdetDCMLResult": "lmrobdetDCML",
}

# Non-fit.models-default regression S3 *classes* to register with the ``lmfm``
# comparison class. Note the class differs from the function name: ``ltsReg()``
# returns an object of class ``lts``. fit.models already knows ``lm``/``rlm``;
# register_robstattm() handles the RobStatTM ones.
_EXTRA_LMFM_CLASSES = ("rlm", "lmrob", "lts")

# Covariance result class name -> whether it is the classical or a robust
# estimator. fit.models compares them in a ``covfm`` container.
_COV_KIND: dict[str, str] = {
    "CovClassicResult": "classic",
    "CovRobResult": "rob",
    "CovRobMMResult": "rob",
    "CovRobRockeResult": "rob",
}


class Comparison:
    """A ``fit.models`` comparison of two or more fits (an R ``lmfm``/``glmfm``).

    Thin proxy over the fitmodels-py result. The methods you will use most are
    :meth:`summary` (R's side-by-side coefficient tables), :meth:`plot`
    (overlaid diagnostics), ``str(cmp)`` / :meth:`to_string` (R's printed
    comparison), and indexing (``cmp["Robust"]``). Anything else is forwarded to
    the underlying fitmodels-py object.
    """

    def __init__(self, fm: Any) -> None:
        self._fm = fm

    def summary(self, *args: Any, **kwargs: Any) -> Any:
        """R's ``summary.lmfm`` -- the fits' coefficient tables side by side."""
        return self._fm.summary(*args, **kwargs)

    def plot(self, *args: Any, **kwargs: Any) -> Any:
        """R's ``plot.lmfm`` -- overlaid model diagnostics."""
        return self._fm.plot(*args, **kwargs)

    def to_string(self) -> str:
        """R's printed comparison, as text."""
        return self._fm.to_string()

    def __getitem__(self, key: Any) -> Any:
        return self._fm[key]

    def __str__(self) -> str:
        return self._fm.to_string()

    def __repr__(self) -> str:
        return f"<Comparison of {len(self._fm.models)} fits>"

    def _repr_html_(self) -> str:
        return self._fm._repr_html_()

    @property
    def result(self) -> Any:
        """The underlying fitmodels-py result object."""
        return self._fm

    def __getattr__(self, name: str) -> Any:
        # Forward anything not defined here to the fitmodels-py result.
        return getattr(self._fm, name)


def _import_fitmodels():
    try:
        import fitmodels_py as fpm
    except ImportError as exc:
        raise RobStatTMSetupError(
            "compare() needs the sibling package fitmodels-py (the fit.models "
            "wrapper). Install it with:\n"
            "    pip install fitmodels-py\n"
            "Each model's own .summary() works without it; compare() is only "
            "for the fit.models side-by-side view."
        ) from exc
    return fpm


def _register_all(fpm) -> None:
    """Register RobStatTM + robustbase/MASS regression classes with fit.models."""
    fpm.estimators.register_robstattm()
    try:
        from fitmodels_py.core.registration import fmclass_add_class
    except ImportError:  # pragma: no cover - older fitmodels-py layout
        fmclass_add_class = getattr(fpm, "fmclass_add_class", None)
    if fmclass_add_class is not None:
        for cls in _EXTRA_LMFM_CLASSES:
            fmclass_add_class("lmfm", cls, warn=False)


def _combine_mode_fits(fpm, models: dict[str, Any]) -> dict[str, Any] | None:
    """Refit each model as a live R object via fitmodels-py's estimators.

    This path records **clean calls** (``lm(formula = zinc ~ copper, data =
    data)``) instead of deparsing the whole data frame into the summary, so it
    is preferred whenever every model has a matching estimator. Returns ``None``
    if any model is one fitmodels-py cannot fit (``ltsReg``/``lmrob``/DCML),
    in which case the caller falls back to fit-from-names.
    """
    est = fpm.estimators
    builders = {
        "LmResult": lambda r, dn: est.lm(r.formula, r._data, data_name=dn),
        "GlmResult": lambda r, dn: est.glm(
            r.formula, r._data, family=r.family, data_name=dn
        ),
        "RlmResult": lambda r, dn: est.rlm(r.formula, r._data, data_name=dn),
        "LmrobdetMMResult": lambda r, dn: est.lmrobdet_mm(
            r.formula, r._data, data_name=dn
        ),
        "LmrobMResult": lambda r, dn: est.lmrobm(r.formula, r._data, data_name=dn),
    }
    live: dict[str, Any] = {}
    for label, res in models.items():
        builder = builders.get(type(res).__name__)
        if builder is None:
            return None
        live[label] = builder(res, "data")
    return live


def _compare_cov(models: dict[str, Any]) -> Comparison:
    """Build a ``covfm`` comparing classical and robust covariance estimates.

    Refits each cov result as a live R fit via fitmodels-py's estimators (so it
    keeps its S3 class), then bundles them. fit.models already knows
    ``covClassic``/``covRob``, so no extra registration is needed.
    """
    fpm = _import_fitmodels()
    est = fpm.estimators
    live: dict[str, Any] = {}
    for label, res in models.items():
        data = getattr(res, "_data", None)
        if data is None:
            raise ValueError(
                f"{type(res).__name__} for {label!r} did not keep its input "
                "data, so it cannot be refit for comparison. Rebuild it with "
                "cov_classic(X) / cov_rob(X)."
            )
        if _COV_KIND[type(res).__name__] == "classic":
            live[label] = est.cov_classic(data, data_name="data")
        else:
            live[label] = est.cov_rob(data, data_name="data")
    return Comparison(fpm.fit_models(**live))


def compare(**models: Any) -> Comparison:
    """Line up two or more RobStatTM-Py fits with R's ``fit.models``.

    Parameters
    ----------
    **models:
        Named results from the regression wrappers, all fitted on the **same
        formula and data**, e.g. ``compare(LeastSquares=ls, Robust=rob)``.
        Supported: :class:`~robstattm_py.LmResult`, ``GlmResult``, ``RlmResult``,
        ``LtsResult``, ``LmrobResult``, and the RobStatTM regression results
        (``lmrobdet_mm``, ``lmrobM``, ``lmrobdet_dcml``).

    Returns
    -------
    Comparison

    Raises
    ------
    robstattm_py.RobStatTMSetupError
        If fitmodels-py is not installed.
    ValueError
        If fewer than one model is given, or the models were not fit on the same
        formula/data.
    NotImplementedError
        For covariance results: compare ``cov_classic`` and ``cov_rob`` via their
        own ``.summary()`` for now.

    Notes
    -----
    The models are refit with each estimator's **defaults** inside fit.models, so
    a custom control on the original fit is not carried into the comparison.
    """
    if not models:
        raise ValueError("compare() needs at least one named model")

    # Covariance comparison (covfm) is a separate fit.models family from the
    # regression one (lmfm/glmfm); route to it when every model is a cov result.
    if all(type(r).__name__ in _COV_KIND for r in models.values()):
        return _compare_cov(models)
    if any(type(r).__name__ in _COV_KIND for r in models.values()):
        raise ValueError(
            "cannot mix covariance and regression models in one compare(); "
            "fit.models compares covfm and lmfm separately"
        )

    mapping: dict[str, str] = {}
    formula: str | None = None
    data = None
    family: str | None = None
    for label, res in models.items():
        cls = type(res).__name__
        if cls not in _ESTIMATOR_NAME:
            raise NotImplementedError(
                f"compare() does not support {cls}. Supported: regression "
                "results (lm/glm/rlm/lts_reg/lmrob, lmrobdet_mm/lmrobM/"
                "lmrobdet_dcml) and covariance results (cov_classic/cov_rob). "
                "For anything else, use each result's own .summary()."
            )
        mapping[label] = _ESTIMATOR_NAME[cls]
        f = getattr(res, "formula", None)
        d = getattr(res, "_data", None)
        if f is None or d is None:
            raise ValueError(
                f"{cls} for {label!r} is missing formula/data; refit it with a "
                "formula and DataFrame so it can be compared."
            )
        if formula is None:
            formula, data = f, d
        elif f != formula:
            raise ValueError(
                "all models must share the same formula to be compared; "
                f"got {formula!r} and {f!r}"
            )
        if cls == "GlmResult":
            family = res.family

    fpm = _import_fitmodels()
    _register_all(fpm)

    # Preferred path: refit via estimators for clean, readable calls in the
    # summary. Falls back to fit-from-names for models fitmodels-py cannot fit
    # (ltsReg / lmrob / lmrobdetDCML), which deparses the frame into the call.
    live = _combine_mode_fits(fpm, models)
    if live is not None:
        return Comparison(fpm.fit_models(**live))

    extra: dict[str, Any] = {}
    # fit-from-names passes the same extra args to every estimator, so a family
    # is only meaningful when every model is a glm.
    if family is not None and all(v == "glm" for v in mapping.values()):
        from robstattm_py._r import r
        extra["family"] = r().r(family)

    fm = fpm.fit_models(mapping, formula, data=df_with_r_names(data), **extra)
    return Comparison(fm)
