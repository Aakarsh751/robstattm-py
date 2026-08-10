# Coming from R

If you already use RobStatTM in R, this page is the whole translation. The
functions, the arguments and the returned numbers are the same — only the
syntax around them changes.

Every result is computed by the same R code you would run yourself, through
[rpy2](https://rpy2.github.io/). The test suite compares field by field against
direct R calls at `atol=0, rtol=0`, so the numbers are not merely close: they are
identical.

---

## The five differences that matter

| | R | Python |
|---|---|---|
| Call a function | `lmrobdetMM(zinc ~ copper, data = mineral)` | `rpm.lmrobdet_mm("zinc ~ copper", data=mineral)` |
| Formula | bare expression | a **string** |
| Extract a component | `fit$coefficients` | `fit.coefficients` |
| Apply a method | `summary(fit)` | `fit.summary()` |
| Named arguments | `family = "bisquare"` | `family="bisquare"` (no spaces) |

Side by side:

```r
# R
library(RobStatTM)
data(mineral)
fit <- lmrobdetMM(zinc ~ copper, data = mineral)
summary(fit)
fit$coefficients
```

```python
# Python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
fit.summary()
fit.coefficients
```

---

## Prefer the original names?

Every wrapper is also exported under its exact R name:

```python
from robstattm_py.compat_r import lmrobdetMM, covRobMM, BYlogreg

fit = lmrobdetMM("zinc ~ copper", data=mineral)
```

These are the same objects, not copies — `compat_r.lmrobdetMM is rpm.lmrobdet_mm`
is `True`. Use whichever reads better to you.

---

## Name map

Python uses `snake_case`, so R's `lmrobdetMM` becomes `lmrobdet_mm`. Names that
are not valid Python identifiers (`step.lmrobdetMM`) drop the dot.

### Regression

| R | Python |
|---|---|
| `lmrobdetMM` | `lmrobdet_mm` |
| `lmrobdetDCML` | `lmrobdet_dcml` |
| `lmrobM` | `lmrob_m` |
| `lmrobdet.control` | `lmrobdet_control` |
| `lmrobM.control` | `lmrobm_control` |
| `step.lmrobdetMM` | `step_lmrobdet` |
| `rob.linear.test` | `rob_linear_test` |
| `drop1` | `drop1_lmrobdet`, or `fit.drop1()` |
| `pyinit` | `pyinit` |
| `refine.sm` | `refine_sm` |
| `INVTR2` | `invtr2` |

### Covariance and PCA

| R | Python |
|---|---|
| `covRob` | `cov_rob` |
| `covRobMM` | `cov_rob_mm` |
| `covRobRocke` | `cov_rob_rocke` |
| `covClassic` | `cov_classic` |
| `KurtSDNew` / `initPP` | `kurt_sd_new` |
| `fastmve` | `fastmve` |
| `pcaRobS` | `pca_rob_s` |
| `prcompRob` | `prcomp_rob` |

### Location, scale and GLM

| R | Python |
|---|---|
| `locScaleM` / `MLocDis` | `loc_scale_m` |
| `scaleM` / `mscale` | `m_scale` |
| `BYlogreg` | `by_logreg` |
| `WBYlogreg` | `wby_logreg` |
| `WMLlogreg` | `wml_logreg` |

`rpm.help("lmrobdetMM")` accepts either spelling and prints the documentation.
`rpm.list_names()` returns the whole map.

---

## Data

R's `data(mineral)` becomes a function call returning a pandas DataFrame:

```python
mineral = rpm.datasets.mineral()   # a DataFrame, not a magic global
```

All 20 textbook datasets are available this way — see [Datasets](datasets.md).
For a dataset from any other R package, give the package first:

```python
coleman = rpm.datasets.load("robustbase", "coleman")
print(coleman.shape)
```

Your own data works directly: pass any pandas DataFrame as `data=`. Most
estimators also accept plain arrays:

```python
import numpy as np

mineral = rpm.datasets.mineral()
X_array = mineral[["copper"]].to_numpy()
y_array = mineral["zinc"].to_numpy()

fit = rpm.lmrobdet_mm(X=X_array, y=y_array)
print(fit.coefficients)
```

---

## Control objects

Exactly as in R, built by a factory and passed as `control=`:

```r
ctrl <- lmrobdet.control(bb = 0.5, efficiency = 0.95, family = "bisquare")
fit  <- lmrobdetMM(zinc ~ copper, data = mineral, control = ctrl)
```

```python
ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.95, family="bisquare")
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=ctrl)
```

---

## Results

An R fit is a list you index with `$`. A Python fit is an object with
attributes, plus methods where R would use a generic:

| R | Python |
|---|---|
| `fit$coefficients` | `fit.coefficients` |
| `fit$scale` | `fit.scale` |
| `summary(fit)` | `fit.summary()` |
| `predict(fit, newdata)` | `fit.predict(newdata)` |
| `residuals(fit)` | `fit.resid()` |
| `fitted(fit)` | `fit.fitted()` |
| `weights(fit)` | `fit.weights()` |
| `vcov(fit)` | `fit.vcov()` |
| `sigma(fit)` | `fit.sigma()` |
| `hatvalues(fit)` | `fit.hatvalues()` |
| `drop1(fit)` | `fit.drop1()` |

> The accessor **methods** are named `resid()`, `fitted()` and so on rather than
> `residuals`/`fitted_values`, because those names are already taken by the data
> attributes they read.

`fit.to_dict()` gives you every field at once; `fit.coef_df()` returns the
coefficient table as a DataFrame. See [Result methods](result-methods.md).

---

## Reproducibility

The same rule as in R, with one convenience: `rpm.set_seed(n)` calls R's
`set.seed(n)` in the session the estimators actually run in.

```python
rpm.set_seed(42)
cov = rpm.cov_rob(rpm.datasets.wine())
```

Needed for the covariance, PCA and external estimators, which subsample.
`lmrobdet_mm`, `lmrobdet_dcml` and `lmrob_m` are deterministic and need no seed.

---

## Warnings and errors

R warnings surface as Python warnings, so nothing is lost in translation:

```python
import warnings
from robstattm_py import RobStatTMWarning

mineral = rpm.datasets.mineral()

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fit = rpm.lmrob_m("zinc ~ copper", data=mineral)

r_warnings = [w for w in caught if issubclass(w.category, RobStatTMWarning)]
print(f"{len(r_warnings)} R warning(s)")
```

`rpm.last_r_warnings()` returns the messages from the most recent call. R errors
are raised as `RobStatTMRError` with R's own traceback attached.

---

## Dropping into R when you need to

Nothing is hidden. For anything without a wrapper yet:

```python
from robstattm_py._r import r

ro = r()
ro.r('library(RobStatTM); fit <- lmrobdetMM(zinc ~ copper, data = mineral)')
```

`fit.to_r()` converts a Python result back into an R object.

---

## What you gain by moving

Everything already in the Python ecosystem: pandas for wrangling, matplotlib and
plotnine for plots ([Plotting](plotting.md)), scikit-learn pipelines, and
Jupyter. `fit.summary()` renders as a formatted table in a notebook.

## What is not here

`pense`, `GSE`, `TSGS`, `arima.rob`, `varComprob`, `glmrob` and `cubinf` come
from other R packages and are wrapped separately — see
[External estimators](external.md). They need those R packages installed:

```bash
robstattm-py install-r-packages pense GSE
```

## See also

- [Installation](installation.md) — setup, including letting the package install R.
- [API reference](../api/index.md) — every wrapper, with its R man page.
