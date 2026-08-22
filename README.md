# RobStatTM-Py

**Python wrappers for the [RobStatTM](https://cran.r-project.org/package=RobStatTM) robust-statistics R package.**

RobStatTM-Py brings RobStatTM's robust estimators, MM-regression, robust
covariance, robust PCA, robust GLM, M-estimators of location/scale, and more,
to Python users with no R knowledge required. It calls the original R routines
through [`rpy2`](https://rpy2.github.io/), so every numeric result is
**bit-identical to R** (the test suite compares at `atol=0, rtol=0`).

> **GSoC 2026:** see the [final report](GSOC_FINAL_REPORT.md) for a summary of
> what was built, the current state, and what remains.

> Companion to the 2019 Wiley textbook *Robust Statistics: Theory and Methods
> (with R)* by Maronna, Martin, Yohai & Salibian-Barrera.

---

## Three ways to get started

> **Not on PyPI yet.** `pip install robstattm-py` will fail with *"No matching
> distribution found"* until the package is published. Install from source
> meanwhile, it is one extra command, and everything afterwards is identical.

| | Command | R installed for you? |
|---|---|---|
| **pip** | `git clone https://github.com/Aakarsh751/robstattm-py.git` then `pip install ./robstattm-py` then `robstattm-py setup` | Yes, by `setup` |
| **conda** | `conda env create -f environment.yml` | Yes, by conda |
| **Docker** | `docker build -t robstattm-py .` then `docker run --rm -it robstattm-py` | Already inside |

All three end with a working R that you never had to install or configure. If
you already have R, the plain `pip install` finds it automatically, no `R_HOME`,
no configuration.

> **New to Python or to the terminal?** Start with
> [Install in 10 minutes](docs/guides/install-beginner.md), which assumes
> nothing.
>
> **Coming from R?** [Coming from R](docs/guides/for-r-users.md) is the whole
> translation on one page.

---

## Requirements

- **Python** ≥ 3.10
- **R** ≥ 4.2, [install it from CRAN](https://cran.r-project.org/) if you don't
  already have it.

You do **not** need to configure R. RobStatTM-Py finds it on its own, via the
Windows registry, `PATH`, an active conda environment, or the standard install
location for your OS, and rejects an R built for the wrong CPU architecture
before it can crash Python.

## Install

```bash
pip install -e robstattm-py/          # from the repo root
# or, from inside the package folder:
cd robstattm-py && pip install -e .
```

> **Linux, and no R installed yet?** Prefix the command with
> `RPY2_CFFI_MODE=ABI`. rpy2 ships no Linux wheels, so pip compiles it, and its
> default mode refuses to build without R already present. ABI mode binds to R
> at run time instead, see [platform support](docs/guides/platform-support.md).

Then the R packages, from your normal terminal, no R console required:

```bash
robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov
robstattm-py install-r-packages pense GSE      # optional stretch estimators
```

Optional Python extras: `pip install -e ".[notebooks,plots,dev,docs,benchmarks]"`
(`notebooks` = scipy + matplotlib + Jupyter, needed to run the example notebooks).

## Check your setup

```bash
robstattm-py doctor
```

Reports Python, rpy2, R, and every R package, and when something is wrong, the
exact command that fixes it.

> **`robstattm-py: command not found`?** On Windows, `pip` often installs
> scripts to a folder outside your `PATH`. `python -m robstattm_py.cli doctor`
> always works and does exactly the same thing.

From inside Python or a notebook:

```python
import robstattm_py as rpm

rpm.check_setup()        # reports R, rpy2, and each R package as READY / MISSING
```

> Stuck? See the [troubleshooting guide](docs/guides/troubleshooting.md), or the
> full cross-OS [installation guide](docs/guides/installation.md).

## Quickstart

```python
import robstattm_py as rpm

# 1. Load a textbook dataset (returned as a pandas DataFrame)
mineral = rpm.datasets.mineral()

# 2. Robust MM-regression, formula interface, just like R
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

Prefer R names? `import robstattm_py.compat_r as rtm` exposes every wrapper under
its original R identifier (`lmrobdetMM`, `covRobMM`, `BYlogreg`, …).

## Testing

The suite validates every wrapper field-by-field against direct R calls at
strict tolerance (`atol=0, rtol=0`).

```bash
cd robstattm-py
# fast unit loop (skips the slow notebook-execution tests)
RPM_SKIP_NOTEBOOKS=1 python -m pytest tests/ -q
# everything, including end-to-end notebook execution
python -m pytest tests/ -q
```

`python verify.py --quick` runs a ~5 s smoke check that every wrapper family
executes; `python verify.py --coverage` prints the R↔Python coverage matrix.

## Examples

[`examples/`](examples/) holds a runnable Python script for **every** example
script that ships with the RobStatTM R package, 25 of them, covering Chapters
2 and 4–8 of Maronna et al. plus both vignettes.

```bash
pip install -e ".[examples]"
python examples/ch05_mineral_lmrobdet_mm.py
```

Each keeps its source script's structure, example numbers and figure numbers, so
you can read it next to the book. Every one is executed end to end by
`tests/test_examples.py`, so an example that stops working is a failing test.
See [`examples/README.md`](examples/README.md) for the full R → Python map.

## Layout

```
robstattm-py/
├── pyproject.toml          # PEP 621 metadata, build + tooling config
├── verify.py               # fast human-readable confidence harness
├── src/robstattm_py/       # the package (src-layout)
├── examples/               # one Python script per RobStatTM R example script
├── tests/                  # strict-tier pytest suite + example/notebook CI
├── notebooks/              # textbook reproductions + tutorials + galleries
├── exploration/            # exploratory parity tests (not part of the suite)
├── templates/              # wrapper/test/docstring code-gen templates
├── docs/                   # contributor docs, API pages, rd→md pipeline
└── .github/workflows/      # CI (pytest + lint on Linux, Windows, macOS)
```

## Project context

This package is the deliverable of the GSoC 2026 project proposal. The proposal,
book website, and legacy proof-of-concept material live in the **parent repo**
(`../docs/gsoc2026_proposal/`, `../Book_Website/`, `../archive/`), keeping this
folder a clean, self-contained, installable library.

- **Mentors:** Doug Martin (UW), Matias Salibian-Barrera (UBC), Brian Peterson
- **Upstream R package:** [msalibian/RobStatTM](https://github.com/msalibian/RobStatTM)
- **License:** MIT
