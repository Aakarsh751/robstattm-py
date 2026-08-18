# RobStatTM-Py

**Robust statistics for Python, backed bit-for-bit by R's RobStatTM.**

RobStatTM-Py gives Python users the robust estimators from the
[RobStatTM](https://cran.r-project.org/package=RobStatTM) R package
(MM-regression, robust covariance, robust PCA, robust GLM, and M-estimators of
location and scale) through a clean, Pythonic API. Every function calls the
original, peer-reviewed R routine through `rpy2`, so results are **byte-identical
to R** (validated at `atol=0, rtol=0`). No reimplementation, no surprises.

```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()                 # a built-in textbook dataset
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)   # robust MM-regression

print(fit.summary())          # coefficient table with robust std errors
print(fit.coefficients)       # numpy array, bit-identical to R
```

## Why robust statistics?

A single gross outlier can wreck an ordinary least-squares fit, a sample
covariance, or a PCA. Robust estimators are built to resist that: they fit the
bulk of the data and *flag* the anomalies instead of being dragged around by
them. RobStatTM-Py makes the methods from the textbook *Robust Statistics:
Theory and Methods (with R)* (Maronna, Martin, Yohai & Salibián-Barrera, 2019)
available without writing any R.

## Install

```bash
pip install -e robstattm-py/      # from the repo root
```

You also need **R** with the `RobStatTM` package (and its dependencies). See
[Getting started](getting-started.md) for the full setup, then run:

```python
import robstattm_py as rpm
rpm.check_setup()      # verifies R, rpy2, and each R package are READY
```

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} 🚀 Getting started
:link: getting-started
:link-type: doc

Install R + the package, verify your setup, and run your first robust fit.
:::

:::{grid-item-card} 📖 API reference
:link: api/index
:link-type: doc

Every wrapped function and result-object method, with worked examples.
:::

:::{grid-item-card} 🗃️ Datasets
:link: guides/datasets
:link-type: doc

The 20 built-in textbook datasets and how to load your own data.
:::

:::{grid-item-card} 🧩 Result methods
:link: guides/result-methods
:link-type: doc

`.summary()`, `.predict()`, `.to_dict()`, plotting, and more.
:::

::::

## How it maps to R

Python names are `snake_case` versions of the R names (`lmrobdetMM` →
`lmrobdet_mm`, `covRobMM` → `cov_rob_mm`). Prefer the originals? Every wrapper is
also exposed under its R name via `robstattm_py.compat_r`. See the
[API reference](api/index.md) for the complete map.

```{toctree}
:hidden:
:maxdepth: 2

getting-started
api/index
```

```{toctree}
:hidden:
:caption: Guides
:maxdepth: 1

guides/install-beginner
guides/installation
guides/platform-support
guides/troubleshooting
guides/testing-for-beginners
guides/for-r-users
guides/datasets
guides/psi-families
guides/utilities
guides/result-methods
guides/plotting
guides/external
guides/book-examples
```
