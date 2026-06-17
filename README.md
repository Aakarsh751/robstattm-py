# RobStatTM-Py

**Python wrappers for the [RobStatTM](https://cran.r-project.org/package=RobStatTM) robust-statistics R package.**

RobStatTM-Py brings RobStatTM's robust estimators — MM-regression, robust
covariance, robust PCA, robust GLM, M-estimators of location/scale, and more —
to Python users with no R knowledge required. It calls the original R routines
through [`rpy2`](https://rpy2.github.io/), so every numeric result is
**bit-identical to R** (the test suite compares at `atol=0, rtol=0`).

> Companion to the 2019 Wiley textbook *Robust Statistics: Theory and Methods
> (with R)* by Maronna, Martin, Yohai & Salibian-Barrera.

---

## Requirements

- **Python** ≥ 3.10
- **R** ≥ 4.2 with the `RobStatTM` package installed (plus its deps:
  `pyinit`, `robustbase`, `rrcov`). Optional stretch estimators need `pense`
  and `GSE`.
- On Windows, point `rpy2` at your R install before importing:

  ```python
  import os
  os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
  os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]
  ```

Install the R side once:

```r
install.packages(c("RobStatTM", "pyinit", "robustbase", "rrcov"))
# optional stretch estimators:
install.packages(c("pense", "GSE"))
```

## Install

```bash
pip install -e robstatm-py/          # from the repo root
# or, from inside the package folder:
cd robstatm-py && pip install -e .
```

Optional extras: `pip install -e ".[notebooks,plots,dev,docs,benchmarks]"`
(`notebooks` = scipy + matplotlib + Jupyter, needed to run the example notebooks).

> **Setting up on macOS or Linux, or hitting an `R_HOME` / rpy2 error?** See the
> full cross-OS [Installation & setup guide](docs/guides/installation.md) — it
> covers R + R-package install per OS, virtual environments, Jupyter, and a
> troubleshooting table.

## Check your setup

```python
import robstatm_py as rpm

rpm.check_setup()        # reports R, rpy2, and each R package as READY / MISSING
```

## Quickstart

```python
import robstatm_py as rpm

# 1. Load a textbook dataset (returned as a pandas DataFrame)
mineral = rpm.datasets.mineral()

# 2. Robust MM-regression — formula interface, just like R
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
print(fit.coefficients)         # numpy array, bit-equal to R
print(fit.summary())            # coefficients table, scale, R², ...

# 3. Predict / diagnostics
fit.predict(mineral)
fit.hatvalues()

# 4. Robust covariance & PCA
cov = rpm.cov_rob(rpm.datasets.wine())
pca = rpm.prcomp_rob(rpm.datasets.bus())

# 5. M-estimators of location / scale
rpm.loc_scale_m(mineral["zinc"].to_numpy())
rpm.m_scale(mineral["zinc"].to_numpy())
```

Prefer R names? `import robstatm_py.compat_r as rtm` exposes every wrapper under
its original R identifier (`lmrobdetMM`, `covRobMM`, `BYlogreg`, …).

## Testing

The suite validates every wrapper field-by-field against direct R calls at
strict tolerance (`atol=0, rtol=0`).

```bash
cd robstatm-py
# fast unit loop (skips the slow notebook-execution tests)
RPM_SKIP_NOTEBOOKS=1 python -m pytest tests/ -q
# everything, including end-to-end notebook execution
python -m pytest tests/ -q
```

`python verify.py --quick` runs a ~5 s smoke check that every wrapper family
executes; `python verify.py --coverage` prints the R↔Python coverage matrix.

## Layout

```
robstatm-py/
├── pyproject.toml          # PEP 621 metadata, build + tooling config
├── verify.py               # fast human-readable confidence harness
├── src/robstatm_py/        # the package (src-layout)
├── tests/                  # strict-tier pytest suite + notebook CI
├── notebooks/              # textbook reproductions + tutorials + galleries
├── exploration/            # exploratory parity tests (not part of the suite)
├── templates/              # wrapper/test/docstring code-gen templates
├── docs/                   # implementation docs, API pages, rd→md pipeline
└── .github/workflows/      # CI (pytest on Windows + Linux)
```

## Project context

This package is the deliverable of the GSoC 2026 project proposal. The proposal,
book website, and legacy proof-of-concept material live in the **parent repo**
(`../docs/gsoc2026_proposal/`, `../Book_Website/`, `../archive/`), keeping this
folder a clean, self-contained, installable library.

- **Mentors:** Doug Martin (UW), Matias Salibian-Barrera (UBC), Brian Peterson
- **Upstream R package:** [msalibian/RobStatTM](https://github.com/msalibian/RobStatTM)
- **License:** MIT
