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
Every licence below was read from the installed package's own `DESCRIPTION`
(`packageDescription(pkg)$License`), not from a web page, and last verified on
2026-08-12 against the versions named. `dev/_check_licences.py` reprints them.

| Software | Licence | Role |
|---|---|---|
| [R](https://www.r-project.org/) 4.5.2 | GPL-2 \| GPL-3 | The language and runtime that performs the computation |
| [RobStatTM](https://cran.r-project.org/package=RobStatTM) 1.0.11 | GPL (≥ 3) | The robust estimators being wrapped |
| [pyinit](https://cran.r-project.org/package=pyinit) 1.1.5 | GPL (≥ 2) | Initial estimator used by `lmrobdetMM` |
| [robustbase](https://cran.r-project.org/package=robustbase) 0.99.7 | GPL (≥ 2) | Dependency of RobStatTM |
| [rrcov](https://cran.r-project.org/package=rrcov) 1.7.7 | GPL (≥ 3) | Dependency of RobStatTM |
| [micromamba](https://github.com/mamba-org/mamba) | BSD-3-Clause | Fetches the above during `setup` |

Optional, installed only if you ask for them:

| Software | Licence | Wrapper |
|---|---|---|
| [pense](https://cran.r-project.org/package=pense) 2.5.2 | MIT + file LICENSE | `pense`, `pense_cv` |
| [GSE](https://cran.r-project.org/package=GSE) 4.2.4 | GPL (≥ 2) | `gse`, `tsgs` |
| [robust](https://cran.r-project.org/package=robust) 0.7.5 | GPL (≥ 3) | test data (`breslow.dat`) |
| [robustarima](https://cran.r-project.org/package=robustarima) 0.2.7 | BSD-3-Clause + file LICENSE | `arima_rob` |
| [robustvarComp](https://cran.r-project.org/package=robustvarComp) 0.1.7 | **GPL-2 (version 2 only)** | `var_comprob` |
| [robcbi](https://cran.r-project.org/package=robcbi) 1.1.4 | GPL (≥ 2) | `cubinf` (archived on CRAN) |
| [robeth](https://cran.r-project.org/package=robeth) 2.7.8 | GPL (≥ 2) | Dependency of `robcbi` |
| [WWGbook](https://cran.r-project.org/package=WWGbook) 1.0.2 | GPL (≥ 2) | test data (`autism`) |

> **`robustvarComp` is the only GPL-2-*only* item here.** Everything else in the
> chain is "or later", so an adopter may elect GPL-3. The distinction matters to
> anyone combining this stack with Apache-2.0 code, which the FSF considers
> [incompatible with GPLv2 but compatible with
> GPLv3](https://www.gnu.org/licenses/license-list.en.html#apache2).

## Python dependencies

| Package | Licence |
|---|---|
| [rpy2](https://rpy2.github.io/) | **GPL-2.0-or-later** |
| [numpy](https://numpy.org/) | BSD-3-Clause |
| [pandas](https://pandas.pydata.org/) | BSD-3-Clause |
| [packaging](https://github.com/pypa/packaging) | Apache-2.0 \| BSD-2-Clause |

These are installed by `pip` as ordinary dependencies and are likewise not
redistributed here.

> **Note on rpy2.** rpy2 is licensed **GPL-2.0-or-later** — one licence, not a
> choice of several, and the same licence R itself uses. It is a normal `pip`
> dependency rather than something bundled here. If your organisation has
> policies about GPL dependencies, that is the component to review. The MIT
> licence covers RobStatTM-Py's own code only and makes no claim about the
> licences of software it imports or downloads.
>
> The "or later" matters: an adopter may take rpy2 under GPL-3, which resolves
> most conflicts with an Apache-2.0 or GPL-3 stack.

## If you build a container or a conda package

Everything above rests on this package **not distributing** R or any R package.
GPL obligations attach to distribution, not to use — GPLv2 §0: *"The act of
running the Program is not restricted."*

An artifact that **contains** R and RobStatTM is a different matter. The
`Dockerfile` in this repository builds exactly such an image, and so does a
conda package built from `environment.yml`. Publishing one means distributing a
combined work, and the GPL terms of the bundled components apply to that
artifact — including the obligation to offer corresponding source. That is a
normal and legitimate thing to do; it simply is not covered by this package's
MIT licence, and is worth deciding deliberately rather than discovering
afterwards.

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
