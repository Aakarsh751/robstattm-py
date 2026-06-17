"""Combinatorial / cross-product tests — permutations beyond unit tests.

These tests deliberately **multiply** dimensions the main ``tests/`` suite
covers one-at-a-time:

* regression dataset × ψ-family × API style (formula vs ``X``/``y``)
* covariance estimator × dataset × ``corr`` flag
* fit-method chains on every major result type
* seed reproducibility (same call twice must match)
* stretch wrappers (``pense``, ``gse``, ``tsgs``) when CRAN packages exist

Run::

    pytest exploration/test_combinatorial_matrix.py -v

Or as part of the full exploration folder::

    pytest exploration/ -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstatm_py as rpm
from tests.conftest import assert_scalar_equal, needs_r


# ---------------------------------------------------------------------------
# Regression: dataset × family × estimator
# ---------------------------------------------------------------------------

REGRESSION_GRID = [
    # loader, formula, estimator, family, efficiency
    ("mineral", "zinc ~ copper", "lmrobdet_mm", "mopt", 0.95),
    ("mineral", "zinc ~ copper", "lmrobdet_mm", "bisquare", 0.85),
    ("mineral", "zinc ~ copper", "lmrobdet_dcml", "mopt", 0.95),
    ("mineral", "zinc ~ copper", "lmrob_m", "bisquare", 0.85),
    ("stackloss", "stack.loss ~ Air.Flow + Water.Temp", "lmrobdet_mm", "mopt", 0.95),
    ("stackloss", "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", "lmrobdet_mm", "bisquare", 0.85),
    ("shock", "time ~ n.shocks", "lmrob_m", "bisquare", 0.85),
    ("shock", "time ~ n.shocks", "lmrobdet_mm", "mopt", 0.95),
    ("algae", "V12 ~ .", "lmrobdet_mm", "bisquare", 0.85),
    ("oats", "response1 ~ variety + block", "lmrob_m", "bisquare", 0.85),
    ("waste", None, "lmrobdet_mm", "mopt", 0.95),  # formula built from last col
]


def _regression_case(loader, formula, estimator, family, efficiency):
    df = getattr(rpm.datasets, loader)()
    if formula is None:
        y = df.attrs["r_columns"][-1]
        formula = f"{y} ~ ."
    fn = getattr(rpm, estimator)
    if estimator == "lmrob_m":
        ctrl = rpm.lmrobm_control(family=family, efficiency=efficiency, bb=0.5)
        return fn(formula, data=df, control=ctrl)
    ctrl = rpm.lmrobdet_control(family=family, efficiency=efficiency, bb=0.5)
    if estimator == "lmrobdet_dcml":
        return fn(formula, data=df, control=ctrl)
    return fn(formula, data=df, control=ctrl)


@needs_r
@pytest.mark.parametrize(
    "loader,formula,estimator,family,efficiency",
    REGRESSION_GRID,
    ids=[f"{e}-{l}-{f}" for l, _, e, f, _ in REGRESSION_GRID],
)
def test_regression_grid_converges(loader, formula, estimator, family, efficiency):
    rpm.set_seed(42)
    fit = _regression_case(loader, formula, estimator, family, efficiency)
    assert fit.converged
    assert np.isfinite(fit.scale) and fit.scale > 0
    assert len(fit.residuals) > 0


_R_PARITY_GRID = [
    g for g in REGRESSION_GRID
    if g[2] == "lmrobdet_mm" and g[0] in ("mineral", "stackloss", "shock")
]


@needs_r
@pytest.mark.parametrize(
    "loader,formula,estimator,family,efficiency",
    _R_PARITY_GRID,
    ids=[f"r-{g[0]}-{g[3]}" for g in _R_PARITY_GRID],
)
def test_regression_grid_scale_vs_r(loader, formula, estimator, family, efficiency, R):
    rpm.set_seed(42)
    df = getattr(rpm.datasets, loader)()
    if formula is None:
        y = df.attrs["r_columns"][-1]
        formula = f"{y} ~ ."
    py = _regression_case(loader, formula, estimator, family, efficiency)

    r_name = df.attrs.get("r_name", loader)
    R(
        f"library(RobStatTM); data({r_name}); "
        f"ctrl <- lmrobdet.control(family='{family}', efficiency={efficiency}, bb=0.5); "
        f"r_fit <- lmrobdetMM({formula!r}, data={r_name}, control=ctrl)"
    )
    assert_scalar_equal(py.scale, R("r_fit$scale"), where=f"{loader}/{family}")


# ---------------------------------------------------------------------------
# Formula API vs X/y matrix API
# ---------------------------------------------------------------------------

MATRIX_ESTIMATORS = ["lmrobdet_mm", "lmrobdet_dcml", "lmrob_m"]


@needs_r
@pytest.mark.parametrize("estimator", MATRIX_ESTIMATORS)
def test_formula_vs_matrix_api(estimator, R):
    df = rpm.datasets.mineral()
    X = df[["copper"]].to_numpy(dtype=float)
    y = df["zinc"].to_numpy(dtype=float)

    fn = getattr(rpm, estimator)
    if estimator == "lmrob_m":
        kw = {"control": rpm.lmrobm_control()}
    else:
        kw = {}
    fit_formula = fn("zinc ~ copper", data=df, **kw)
    fit_matrix = fn(X=X, y=y, **kw)

    np.testing.assert_allclose(
        fit_formula.coefficients, fit_matrix.coefficients, rtol=0, atol=0
    )
    assert fit_formula.scale == fit_matrix.scale
    assert fit_formula.converged == fit_matrix.converged


# ---------------------------------------------------------------------------
# Covariance: estimator × dataset
# ---------------------------------------------------------------------------

COV_GRID = [
    ("cov_rob_mm", "wine", False),
    ("cov_rob_mm", "wine", True),
    ("cov_rob_mm", "biochem", False),
    ("cov_rob_rocke", "vehicle", False),
    ("cov_rob_rocke", "image", False),
    ("cov_rob", "glass", False),   # auto → MM (p=7)
    ("cov_rob", "vehicle", False),  # auto → Rocke (p=18)
    ("cov_classic", "wine", False),
    ("fastmve", "biochem", False),
]


@needs_r
@pytest.mark.parametrize("fn_name,loader,corr", COV_GRID, ids=[f"{a}-{b}" for a, b, _ in COV_GRID])
def test_covariance_grid(fn_name, loader, corr):
    rpm.set_seed(7)
    X = getattr(rpm.datasets, loader)().to_numpy()
    fn = getattr(rpm, fn_name)
    if fn_name == "cov_rob_mm":
        result = fn(X, corr=corr)
    elif fn_name == "cov_rob":
        result = fn(X, corr=corr)
    elif fn_name == "fastmve":
        result = fn(X)
    else:
        result = fn(X)
    assert result.center.shape[0] == X.shape[1]
    assert result.cov.shape == (X.shape[1], X.shape[1])
    assert np.all(np.isfinite(result.center))


@needs_r
@pytest.mark.parametrize("fn_name,loader,corr", COV_GRID[:4], ids=[f"r-{a}-{b}" for a, b, _ in COV_GRID[:4]])
def test_covariance_grid_vs_r(fn_name, loader, corr, R):
    rpm.set_seed(7)
    X = getattr(rpm.datasets, loader)().to_numpy()
    r_fn = {"cov_rob_mm": "covRobMM", "cov_rob_rocke": "covRobRocke"}[fn_name]
    py = getattr(rpm, fn_name)(X, corr=corr) if corr else getattr(rpm, fn_name)(X)
    R(f"library(RobStatTM); data({loader}); set.seed(7); "
      f"X <- as.matrix(get('{loader}')); "
      f"r_fit <- {r_fn}(X{', corr=TRUE' if corr else ''})")
    np.testing.assert_allclose(
        py.center, np.asarray(R("r_fit$center"), dtype=float), rtol=0, atol=0
    )


# ---------------------------------------------------------------------------
# Fit-method chains (S3 ports)
# ---------------------------------------------------------------------------

@needs_r
class TestMethodChains:
    @pytest.fixture(scope="class")
    def mm_fit(self):
        return rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())

    @pytest.fixture(scope="class")
    def cov_fit(self):
        rpm.set_seed(1)
        return rpm.cov_rob_mm(rpm.datasets.wine().to_numpy())

    @pytest.fixture(scope="class")
    def pca_fit(self):
        rpm.set_seed(1)
        return rpm.prcomp_rob(rpm.datasets.bus().to_numpy(), rank=4)

    def test_mm_summary_predict_hatvalues_rfpe(self, mm_fit):
        summ = mm_fit.summary()
        assert len(summ.coefficients_table) == len(mm_fit.coef_names)
        pred = mm_fit.predict()
        assert len(pred) == len(mm_fit.residuals)
        hats = mm_fit.hatvalues()
        assert len(hats) == len(mm_fit.residuals)
        assert np.isfinite(mm_fit.rfpe())

    def test_cov_summary(self, cov_fit):
        summ = cov_fit.summary()
        assert summ.evals.shape[0] == cov_fit.center.shape[0]

    def test_pca_summary(self, pca_fit):
        summ = pca_fit.summary()
        assert len(summ.proportion_of_variance) == len(pca_fit.sdev)

    def test_to_dict_roundtrip_keys(self, mm_fit):
        d = mm_fit.to_dict()
        for key in ("coefficients", "scale", "r_squared", "converged", "iter"):
            assert key in d


# ---------------------------------------------------------------------------
# GLM: method × dataset
# ---------------------------------------------------------------------------

GLM_GRID = [
    ("by_logreg", "skin"),
    ("wby_logreg", "skin"),
    ("wml_logreg", "skin"),
    ("wby_logreg", "leuk_dat"),
]


def _glm_xy(loader: str):
    df = getattr(rpm.datasets, loader)()
    if loader == "skin":
        X = df[["logVOL", "logRATE"]].to_numpy(dtype=float)
        y = df["vasoconst"].to_numpy(dtype=float)
    else:
        X = df.iloc[:, :2].to_numpy(dtype=float)
        y = df["y"].to_numpy(dtype=float)
    return X, y


@needs_r
@pytest.mark.parametrize("method,loader", GLM_GRID, ids=[f"{m}-{l}" for m, l in GLM_GRID])
def test_glm_grid(method, loader):
    X, y = _glm_xy(loader)
    fit = getattr(rpm, method)(X, y)
    assert fit.coefficients.shape[0] >= 2
    assert len(fit.fitted_values) == len(y)
    assert np.all((fit.fitted_values >= 0) & (fit.fitted_values <= 1))


# ---------------------------------------------------------------------------
# Reproducibility: identical output under fixed seed
# ---------------------------------------------------------------------------

@needs_r
@pytest.mark.parametrize(
    "call",
    [
        lambda: rpm.cov_rob_mm(rpm.datasets.wine().to_numpy()),
        lambda: rpm.prcomp_rob(rpm.datasets.bus().to_numpy(), rank=3),
        lambda: rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral()),
    ],
    ids=["cov_rob_mm", "prcomp_rob", "lmrobdet_mm"],
)
def test_seed_reproducibility(call):
    rpm.set_seed(123)
    a = call()
    rpm.set_seed(123)
    b = call()
    if hasattr(a, "scale"):
        assert a.scale == b.scale
        np.testing.assert_array_equal(a.coefficients, b.coefficients)
    elif hasattr(a, "sdev"):
        np.testing.assert_array_equal(a.sdev, b.sdev)
        np.testing.assert_array_equal(a.rotation, b.rotation)
    elif hasattr(a, "center"):
        np.testing.assert_array_equal(a.center, b.center)
        np.testing.assert_array_equal(a.cov, b.cov)


# ---------------------------------------------------------------------------
# Stretch packages (optional CRAN deps)
# ---------------------------------------------------------------------------

def _has_r_pkg(name: str) -> bool:
    try:
        from robstatm_py._r import r_pkg
        r_pkg(name)
        return True
    except Exception:
        return False


needs_pense = pytest.mark.skipif(not _has_r_pkg("pense"), reason="pense not installed")
needs_gse = pytest.mark.skipif(not _has_r_pkg("GSE"), reason="GSE not installed")


@needs_r
@needs_pense
def test_pense_synthetic_vs_r(R):
    rpm.set_seed(1)
    n, p = 40, 6
    X = np.random.default_rng(0).normal(size=(n, p))
    beta = np.array([2.0, -1.0, 0.5, 0, 0, 0])
    y = X @ beta + np.random.default_rng(1).normal(size=n) * 0.3
    py = rpm.pense(X, y, alpha=0.5, nlambda=8)
    from robstatm_py._r import r
    ro = r()
    ro.globalenv["Xp"] = X
    ro.globalenv["yp"] = y
    ro.r("set.seed(1L); rfit <- pense::pense(Xp, drop(yp), alpha=0.5, nlambda=8)")
    r_lam = np.asarray(ro.r("rfit$lambda[[1]]"), dtype=float)
    np.testing.assert_allclose(py.lambda_path, r_lam, rtol=0, atol=0)


@needs_r
@needs_gse
def test_gse_wine_subset():
    rpm.set_seed(5)
    X = rpm.datasets.wine().to_numpy()
    # Introduce MCAR missingness
    X_miss = X.copy()
    rng = np.random.default_rng(5)
    mask = rng.random(X.shape) < 0.05
    X_miss[mask] = np.nan
    result = rpm.gse(X_miss)
    assert result.mu.shape[0] == X.shape[1]
    assert result.cov.shape == (X.shape[1], X.shape[1])
    assert len(result.pmd) == X.shape[0]


@needs_r
@needs_gse
def test_tsgs_biochem():
    rpm.set_seed(3)
    X = rpm.datasets.biochem().to_numpy()
    result = rpm.tsgs(X)
    assert result.mu.shape[0] == 2
    assert result.cov.shape == (2, 2)


# ---------------------------------------------------------------------------
# Plotting smoke (R PNG path exists)
# ---------------------------------------------------------------------------

@needs_r
def test_plotting_residuals_png(tmp_path):
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
    path = rpm.plotting.residuals(fit, path=str(tmp_path / "resid.png"))
    assert path.exists() and path.stat().st_size > 1000
