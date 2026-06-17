# Getting started

> **New to the R bridge, or on macOS/Linux?** This page is the 60-second path.
> For per-OS instructions (Windows · macOS · Linux), virtual environments,
> Jupyter, and a troubleshooting table, see the
> **[Installation & setup guide](guides/installation.md)**.

## 1. Install R and the RobStatTM package

RobStatTM-Py is a *bridge* to R, so you need a working R installation with the
`RobStatTM` package and its dependencies.

```r
# in an R session
install.packages(c("RobStatTM", "pyinit", "robustbase", "rrcov"))
# optional stretch estimators (pense / GSE / TSGS):
install.packages(c("pense", "GSE"))
```

## 2. Install RobStatTM-Py

```bash
pip install -e robstatm-py/      # from the repo root
```

On **Windows**, point `rpy2` at your R installation *before* importing the
package (adjust the version path to match yours):

```python
import os
os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]

import robstatm_py as rpm
```

## 3. Verify your setup

```python
import robstatm_py as rpm
rpm.check_setup()
```

This prints a checklist of R, `rpy2`, and each required R package, marking each
`READY` or `MISSING` so you know exactly what (if anything) is missing.

## 4. Your first robust fit

```python
import robstatm_py as rpm

# A built-in textbook dataset: zinc & copper content of 53 mineral samples.
mineral = rpm.datasets.mineral()

# Ordinary regression would be dragged around by the outlying samples.
# Robust MM-regression fits the bulk of the data instead.
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

print(fit)                 # one-line summary
print(fit.summary())       # full table: estimates, robust std errors, p-values
print(fit.coefficients)    # the raw coefficient vector (numpy, bit-equal to R)

# Diagnostics
fit.predict(mineral)       # fitted / predicted values
fit.hatvalues()            # leverages
```

## 5. Where to go next

- **[API reference](api/index.md)** — every function with a worked, runnable example.
- **[Datasets](guides/datasets.md)** — the 20 built-in datasets and using your own.
- **[Result methods](guides/result-methods.md)** — what you can do with a fit object.

## The (X, y) array form

Every regression wrapper accepts a `formula` + `data` pair **or** plain arrays:

```python
import numpy as np
import robstatm_py as rpm

mineral = rpm.datasets.mineral()
X = mineral[["copper"]].to_numpy()
y = mineral["zinc"].to_numpy()

fit = rpm.lmrobdet_mm(X=X, y=y)        # same result as the formula form
```

## Reproducibility

Several estimators (robust covariance, robust PCA) use randomised subsampling.
Call `rpm.set_seed(...)` immediately before the fit to get reproducible results
that also match R:

```python
rpm.set_seed(42)
cov = rpm.cov_rob_mm(rpm.datasets.wine())
```
