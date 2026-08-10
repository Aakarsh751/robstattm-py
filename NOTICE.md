# Licensing and third-party software

## This package

**RobStatTM-Py** is released under the **MIT License** (see `LICENSE`).

Everything in `src/robstattm_py/` is original work: wrapper functions,
result classes, the R-environment subsystem, the plotting suite, the CLI, the
tests and the documentation.

## What is *not* included

RobStatTM-Py contains **no R code and no R binaries**. It calls R through
[rpy2](https://rpy2.github.io/) at run time.

`robstattm-py setup` *downloads* R and the R packages from
[conda-forge](https://conda-forge.org/) onto your machine, at your request and
after telling you what it is about to fetch. Nothing is bundled, vendored, or
redistributed by this project, and no GPL-licensed code is combined into or
shipped with the MIT-licensed wheel.

Those downloads are governed by their own licences:

| Software | Licence | Role |
|---|---|---|
| [R](https://www.r-project.org/) | GPL-2 \| GPL-3 | The language and runtime that performs the computation |
| [RobStatTM](https://cran.r-project.org/package=RobStatTM) | GPL (≥ 3) | The robust estimators being wrapped |
| [pyinit](https://cran.r-project.org/package=pyinit) | GPL (≥ 2) | Initial estimator used by `lmrobdetMM` |
| [robustbase](https://cran.r-project.org/package=robustbase) | GPL (≥ 2) | Dependency of RobStatTM |
| [rrcov](https://cran.r-project.org/package=rrcov) | GPL (≥ 2) | Dependency of RobStatTM |
| [micromamba](https://github.com/mamba-org/mamba) | BSD-3-Clause | Fetches the above during `setup` |

Optional, installed only if you ask for them:

| Software | Licence | Wrapper |
|---|---|---|
| [pense](https://cran.r-project.org/package=pense) | MIT | `pense`, `pense_cv` |
| [GSE](https://cran.r-project.org/package=GSE) | GPL (≥ 2) | `gse`, `tsgs` |
| [robust](https://cran.r-project.org/package=robust) | GPL-2 | test data (`breslow.dat`) |
| [robustarima](https://cran.r-project.org/package=robustarima) | GPL-2 | `arima_rob` |
| [robustvarComp](https://cran.r-project.org/package=robustvarComp) | GPL (≥ 2) | `var_comprob` |
| [robcbi](https://cran.r-project.org/package=robcbi) | GPL (≥ 2) | `cubinf` (archived on CRAN) |
| [WWGbook](https://cran.r-project.org/package=WWGbook) | GPL-2 | test data |

## Python dependencies

`rpy2` (GPL-2 / LGPL / MPL tri-licence), `numpy` (BSD-3-Clause), `pandas`
(BSD-3-Clause), `platformdirs` (MIT), `packaging` (Apache-2.0 / BSD-2-Clause).
These are installed by `pip` as ordinary dependencies and are likewise not
redistributed here.

> **Note on rpy2.** rpy2 is available under GPL-2 among other licences, and it
> is a normal `pip` dependency of this package rather than something bundled
> with it. If your organisation has policies about GPL dependencies, that is the
> component to review — the MIT licence covers RobStatTM-Py's own code only, and
> makes no claim about the licences of software it imports or downloads.

## Attribution

RobStatTM-Py wraps the R package accompanying:

> Maronna, R. A., Martin, R. D., Yohai, V. J., & Salibián-Barrera, M. (2019).
> *Robust Statistics: Theory and Methods (with R)*, 2nd edition. Wiley.

The estimators, their behaviour and their numerical results are the work of the
RobStatTM authors. This package provides a Python interface to them and adds
nothing to the statistics. Upstream:
<https://github.com/msalibian/RobStatTM>.

If you use this package in published work, please cite the book and the
RobStatTM package, not just this wrapper.
