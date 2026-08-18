# Getting started

> **New to the R bridge, or on macOS/Linux?** This page is the 60-second path.
> For per-OS instructions (Windows · macOS · Linux), virtual environments,
> Jupyter, and a troubleshooting table, see the
> **[Installation & setup guide](guides/installation.md)**.

## 1. Install RobStatTM-Py

> **Not on PyPI yet.** `pip install robstattm-py` fails with *"No matching
> distribution found"* until the package is published, so install from a clone.

```bash
git clone https://github.com/Aakarsh751/robstattm-py.git
pip install ./robstattm-py
```

## 2. Get R

RobStatTM-Py is a *bridge* to R, so R has to be present, but you do not have to
install or configure it yourself:

```bash
robstattm-py setup
```

That downloads a private R plus RobStatTM into a directory this package owns,
leaving any R you already have untouched. It takes 3–6 minutes.

**Already have R?** Skip the command, R is found automatically, from the
Windows registry, `PATH`, a conda prefix, or the standard install locations.

> **You do not need to set `R_HOME`, on any platform, including Windows.**
> Earlier versions of this page told Windows users to set `R_HOME` and `PATH`
> before importing. That is no longer necessary and is best avoided: setting it
> by hand pins the choice of R before discovery runs, which is how people ended
> up bound to an R of the wrong architecture. Use `ROBSTATTM_R_HOME` only if you
> deliberately want to override the search.

If you prefer to install the R packages into an R you already have:

```bash
robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov
# optional stretch estimators (pense / GSE / TSGS):
robstattm-py install-r-packages pense GSE
```

## 3. Verify your setup

```bash
robstattm-py doctor
```

Look for **`Result: READY`** at the bottom. The report shows which R was found,
how it was found, and which packages are present; anything missing comes with
the command that fixes it.

The same check from inside Python:

```python
import robstattm_py as rpm
rpm.check_setup()
```

> If `robstattm-py` is "not found", common on Windows, where pip puts scripts
> outside `PATH`, use `python -m robstattm_py.cli doctor` instead. That
> substitution works for every `robstattm-py ...` command.

## 4. Your first robust fit

```python
import robstattm_py as rpm

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

- **[API reference](api/index.md)**, every function with a worked, runnable example.
- **[Datasets](guides/datasets.md)**, the 20 built-in datasets and using your own.
- **[Result methods](guides/result-methods.md)**, what you can do with a fit object.
- **[The book's examples](guides/book-examples.md)**, a runnable Python script
  for each of the 25 RobStatTM example scripts.
- **[Troubleshooting](guides/troubleshooting.md)**, when something goes wrong.

## The (X, y) array form

Every regression wrapper accepts a `formula` + `data` pair **or** plain arrays:

```python
import numpy as np
import robstattm_py as rpm

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
