"""Data-ingress pipelines, alternate sources + pandas preprocessing, parity vs R.

These tests model how a *real* Python user gets data into a wrapper: read a CSV,
pull a scikit-learn dataset, load a dataset from another R package, or wrangle a
messy frame with pandas (rename / dropna / filter / astype / merge). In every
case the **fully preprocessed** frame is pushed to R and the wrapper's output is
asserted bit-identical (``atol=0, rtol=0``) to a direct R call on that same frame
, so "data that arrived via path X behaves exactly like native R".

Test matrix
-----------
| Ingress path                              | Preprocessing                          | Wrapper        | R fields compared            |
|-------------------------------------------|----------------------------------------|----------------|------------------------------|
| pandas → CSV → pd.read_csv → astype       | dtype cast                             | lmrobdet_mm    | coef, scale, fitted          |
| sklearn.datasets.load_diabetes            | DataFrame slice + outliers             | lmrobdet_mm    | coef, scale                  |
| sklearn.datasets.load_iris                | feature matrix                         | cov_rob_mm     | center, cov                  |
| sklearn make_classification               | binary y from frame columns            | wby_logreg     | coef, fitted.values          |
| rpm.datasets.load("robustbase","coleman") | dot-free R names, "Y ~ ."              | lmrobdet_mm    | coef, scale, residuals       |
| messy frame: rename/dropna/filter/astype  | full pandas clean                      | lmrobdet_mm    | coef, scale                  |
| two frames → pandas merge(on=key)         | join then fit                          | lmrob_m        | coef, scale                  |

Run::

    pytest exploration/test_data_ingress.py -v
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm

sys.path.insert(0, os.path.dirname(__file__))
from _synth import make_regression_df, push_to_r, reval, rm_r  # noqa: E402

from tests.conftest import (  # noqa: E402
    assert_array_equal,
    assert_scalar_equal,
    needs_r,
)

# ===========================================================================
# 1. CSV round-trip ingress
# ===========================================================================


@needs_r
def test_csv_roundtrip_regression_vs_r(tmp_path):
    """Synthesize → write CSV → read_csv → cast → fit; identical to R on the
    read-back frame. Validates the most common real-world ingress path."""
    df0 = make_regression_df(n=75, p=3, seed=301, outlier_frac=0.12)
    csv = tmp_path / "synth.csv"
    df0.to_csv(csv, index=False)

    # Ingest as a user would, then make dtypes explicit.
    df = pd.read_csv(csv)
    df = df.astype({c: "float64" for c in df.columns})

    push_to_r("ing_df", df)
    try:
        rpm.set_seed(44)
        py = rpm.lmrobdet_mm("y ~ x1 + x2 + x3", data=df)
        reval("set.seed(44L); ing_fit <- RobStatTM::lmrobdetMM(y ~ x1 + x2 + x3, data=ing_df)")
        assert_array_equal(py.coefficients, reval("as.numeric(coef(ing_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("ing_fit$scale"), where="scale")
        assert_array_equal(
            py.fitted_values, reval("as.numeric(ing_fit$fitted.values)"), where="fitted"
        )
    finally:
        rm_r("ing_df", "ing_fit")


# ===========================================================================
# 2. scikit-learn ingress
# ===========================================================================


@needs_r
def test_sklearn_diabetes_regression_vs_r():
    sk = pytest.importorskip("sklearn.datasets")
    data = sk.load_diabetes()
    # Use three features; build a tidy frame with dot-free names.
    cols = ["age", "bmi", "bp"]
    idx = [list(data.feature_names).index(c) for c in cols]
    df = pd.DataFrame(data.data[:, idx], columns=["age", "bmi", "bp"])
    df.insert(0, "y", data.target.astype(float))
    # Inject a few gross outliers so the robust fit has work to do.
    rng = np.random.default_rng(0)
    bad = rng.choice(len(df), size=8, replace=False)
    df.loc[bad, "y"] += 300.0

    push_to_r("ing_df", df)
    try:
        rpm.set_seed(12)
        py = rpm.lmrobdet_mm("y ~ age + bmi + bp", data=df)
        reval("set.seed(12L); ing_fit <- RobStatTM::lmrobdetMM(y ~ age + bmi + bp, data=ing_df)")
        assert_array_equal(py.coefficients, reval("as.numeric(coef(ing_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("ing_fit$scale"), where="scale")
    finally:
        rm_r("ing_df", "ing_fit")


@needs_r
def test_sklearn_iris_covariance_vs_r():
    sk = pytest.importorskip("sklearn.datasets")
    iris = sk.load_iris()
    X = np.asarray(iris.data, dtype=np.float64)  # 150 x 4
    push_to_r("ing_X", X)
    try:
        rpm.set_seed(6)
        py = rpm.cov_rob_mm(X)
        reval("set.seed(6L); ing_cov <- RobStatTM::covRobMM(ing_X)")
        assert_array_equal(py.center, reval("ing_cov$center"), where="center")
        assert_array_equal(py.cov, reval("ing_cov$cov"), where="cov")
    finally:
        rm_r("ing_X", "ing_cov")


@needs_r
def test_sklearn_classification_glm_vs_r():
    sk = pytest.importorskip("sklearn.datasets")
    X_raw, y_raw = sk.make_classification(
        n_samples=160, n_features=3, n_informative=3, n_redundant=0,
        n_clusters_per_class=1, random_state=7,
    )
    # Assemble a frame, then pull X/y back out of it (DataFrame → arrays path).
    df = pd.DataFrame(X_raw, columns=["f1", "f2", "f3"]).astype("float64")
    df["label"] = y_raw.astype(float)
    X = df[["f1", "f2", "f3"]].to_numpy(dtype=float)
    y = df["label"].to_numpy(dtype=float)

    push_to_r("ing_X", X)
    push_to_r("ing_y", y)
    try:
        rpm.set_seed(2)
        py = rpm.wby_logreg(X, y)
        reval(
            "set.seed(2L); ing_glm <- RobStatTM::WBYlogreg(ing_X, "
            "matrix(ing_y, ncol=1), intercept=1)"
        )
        assert_array_equal(
            py.coefficients, reval("as.numeric(ing_glm$coefficients)"), where="coef"
        )
        assert_array_equal(
            py.fitted_values, reval("as.numeric(ing_glm$fitted.values)"), where="fitted"
        )
    finally:
        rm_r("ing_X", "ing_y", "ing_glm")


# ===========================================================================
# 3. Cross-package R dataset ingress
# ===========================================================================


@needs_r
def test_cross_package_coleman_regression_vs_r():
    """rpm.datasets.load() pulls a dataset from another R package; fitting it
    must match a direct R fit on the same frame."""
    coleman = rpm.datasets.load("robustbase", "coleman")
    assert coleman.shape == (20, 6)
    push_to_r("ing_df", coleman)
    try:
        rpm.set_seed(101)
        py = rpm.lmrobdet_mm("Y ~ .", data=coleman)
        reval("set.seed(101L); ing_fit <- RobStatTM::lmrobdetMM(Y ~ ., data=ing_df)")
        assert_array_equal(py.coefficients, reval("as.numeric(coef(ing_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("ing_fit$scale"), where="scale")
        assert_array_equal(
            py.residuals, reval("as.numeric(ing_fit$residuals)"), where="residuals"
        )
    finally:
        rm_r("ing_df", "ing_fit")


# ===========================================================================
# 4. pandas wrangling pipelines (rename / dropna / filter / astype / merge)
# ===========================================================================


@needs_r
def test_messy_pandas_clean_pipeline_vs_r():
    """A deliberately messy frame cleaned with the usual pandas verbs, then fit.
    The cleaned frame is what both Python and R see."""
    base = make_regression_df(n=90, p=2, seed=302, outlier_frac=0.10)
    messy = base.rename(columns={"x1": "Pred One", "x2": "pred.two", "y": "Response"})
    # add a junk column + some missing rows + an out-of-range filter target
    rng = np.random.default_rng(1)
    messy["junk"] = rng.normal(size=len(messy))
    nan_rows = rng.choice(len(messy), size=6, replace=False)
    messy.loc[nan_rows, "Pred One"] = np.nan
    messy["flag"] = (messy["junk"] > -2.0)

    # Pipeline: rename to clean ids → drop junk → dropna → filter rows → cast.
    clean = (
        messy.rename(columns={"Pred One": "x1", "pred.two": "x2", "Response": "y"})
        .drop(columns=["junk"])
        .dropna(subset=["x1", "x2", "y"])
        .query("flag")
        .drop(columns=["flag"])
        .astype("float64")
        .reset_index(drop=True)
    )
    assert len(clean) < len(messy)  # rows actually removed

    push_to_r("ing_df", clean)
    try:
        rpm.set_seed(55)
        py = rpm.lmrobdet_mm("y ~ x1 + x2", data=clean)
        reval("set.seed(55L); ing_fit <- RobStatTM::lmrobdetMM(y ~ x1 + x2, data=ing_df)")
        assert_array_equal(py.coefficients, reval("as.numeric(coef(ing_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("ing_fit$scale"), where="scale")
    finally:
        rm_r("ing_df", "ing_fit")


@needs_r
def test_pandas_merge_then_fit_vs_r():
    """Two frames joined on a key column, then fit, a common ETL shape."""
    n = 70
    rng = np.random.default_rng(303)
    keys = np.arange(n)
    left = pd.DataFrame({"id": keys, "x1": rng.normal(size=n), "x2": rng.normal(size=n)})
    beta = np.array([1.3, -0.8])
    y = 2.0 + left[["x1", "x2"]].to_numpy() @ beta + rng.normal(scale=0.4, size=n)
    # add outliers
    bad = rng.choice(n, size=7, replace=False)
    y[bad] += 10.0
    right = pd.DataFrame({"id": keys, "y": y})

    merged = left.merge(right, on="id").drop(columns=["id"]).astype("float64")
    push_to_r("ing_df", merged)
    try:
        rpm.set_seed(77)
        py = rpm.lmrob_m("y ~ x1 + x2", data=merged)
        reval("set.seed(77L); ing_fit <- RobStatTM::lmrobM(y ~ x1 + x2, data=ing_df)")
        assert_array_equal(py.coefficients, reval("as.numeric(coef(ing_fit))"), where="coef")
        assert_scalar_equal(py.scale, reval("ing_fit$scale"), where="scale")
    finally:
        rm_r("ing_df", "ing_fit")
