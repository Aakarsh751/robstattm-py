# External (stretch) estimators

A handful of robust estimators referenced by the textbook ship in **separate
CRAN packages** rather than in RobStatTM itself. RobStatTM-Py wraps them under
`robstatm_py.external` (and re-exports them at the top level), with the same
rpy2 bridge and bit-for-bit parity as the core wrappers.

These require their R package to be installed separately:

```r
install.packages(c("pense", "GSE"))
```

`rpm.check_setup()` reports whether each is available; the wrappers raise a
clear `RobStatTMSetupError` if you call one whose package is missing.

| Function | R original | Package | What it does |
|---|---|---|---|
| [`pense`](#pense) | `pense::pense` | `pense` | Robust elastic-net S-estimator — full regularization path. |
| [`pense_cv`](#pense_cv) | `pense::pense_cv` | `pense` | Robust elastic-net with k-fold cross-validation. |
| [`gse`](#gse) | `GSE::GSE` | `GSE` | Generalized S-estimator of location/scatter with **missing data**. |
| [`tsgs`](#tsgs) | `GSE::TSGS` | `GSE` | Two-step GSE for **cell-wise** outliers. |

> All four are **stochastic** (Peña-Yohai / EMVE initial estimates, and CV folds
> for `pense_cv`). Call `rpm.set_seed(n)` immediately before for reproducible
> results.

## `pense`

Robust elastic-net regression (penalized S-estimator; the `alpha=1` case is the
MM-lasso). Returns the coefficient matrix along the automatically-chosen `lambda`
path, extracted via R's own `coef(fit, lambda=…)` so it matches R exactly.

```python
def pense(X, y, *, alpha=0.5, nlambda=50, bdp=0.25,
          intercept=True, standardize=True) -> PenseResult
```

| Field | Shape | Meaning |
|---|---|---|
| `coefficients` | `(p+1, n_lambda)` | intercept (row 0) + slopes, one column per `lambda` |
| `intercepts` / `slopes` | `(n_lambda,)` / `(p, n_lambda)` | convenience views |
| `lambda_path` | `(n_lambda,)` | penalty levels, descending |
| `alpha`, `bdp` | scalar | mixing parameter and breakdown point actually used |

```python
import numpy as np
import robstatm_py as rpm

rng = np.random.default_rng(0)
X = rng.standard_normal((60, 8))
y = X @ np.array([2.0, 0, -1.5, 0, 0, 0, 1.0, 0]) + rng.standard_normal(60)

rpm.set_seed(1)
fit = rpm.pense(X, y, alpha=0.75, nlambda=25)
print(fit.coefficients.shape)        # (9, 25)  -> intercept + 8 slopes
print(fit.lambda_path[:3])
```

## `pense_cv`

Same model selected by cross-validation; `coef_min` is `coef(fit, lambda="min")`.

```python
def pense_cv(X, y, *, alpha=0.5, nlambda=50, bdp=0.25,
             cv_k=5, cv_repl=1, intercept=True, standardize=True) -> PenseCVResult
```

`coef_min` (`(p+1,)`), `lambda_min`, `cv_avg` / `cv_se` per lambda, and the full
`cvres` table are returned.

```python
rpm.set_seed(1)
cv = rpm.pense_cv(X, y, alpha=0.75, nlambda=25, cv_k=5)
print(cv.lambda_min)
print(cv.coef_min.round(3))
```

## `gse`

Generalized S-estimator of multivariate location and scatter that handles
**missing entries** (`NaN`) natively — the point of the GSE family.

```python
def gse(X, *, tol=1e-4, maxiter=150, method="bisquare") -> GSEResult
```

Returns `mu` (location), `cov` (scatter), `pmd` / `pmd_adj` (partial Mahalanobis
distances), `weights`, `ximp` (imputed data), and scalars `sc` / `iter` / `eps`.

```python
import numpy as np, robstatm_py as rpm

X = rpm.datasets.wine().to_numpy()[:, :5].copy()
X[::10, 0] = np.nan                      # introduce some missingness
rpm.set_seed(7)
g = rpm.gse(X)
print(g.mu.shape, g.cov.shape)           # (5,) (5, 5)
print(np.isfinite(g.ximp).all())         # True — missing cells imputed
```

## `tsgs`

Two-step GSE for **cell-wise** contamination: step 1 flags individual outlying
cells (setting them to `NaN`), step 2 runs GSE on the filtered data. Same fields
as `gse` plus `xf`, the filtered matrix.

```python
def tsgs(X, *, filter="UBF-DDC", partial_impute=False,
         tol=1e-4, maxiter=150, method="bisquare") -> TSGSResult
```

```python
rpm.set_seed(7)
t = rpm.tsgs(rpm.datasets.wine().to_numpy()[:, :5])
print(t.cov.shape)                       # (5, 5)
print(np.isnan(t.xf).any())              # cells the filter flagged are NaN
```

## See also

- [API reference](../api/index.md) — the core (non-external) wrappers.
- [Setup & utilities](utilities.md) — `check_setup()` reports external-package availability.
