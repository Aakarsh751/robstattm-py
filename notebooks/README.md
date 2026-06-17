# Notebooks

Reproductions of the RobStatTM textbook examples (Maronna, Martin, Yohai &
Salibián-Barrera, *Robust Statistics: Theory and Methods*, 2019) and the
package's example scripts, all built on `robstatm_py`.

Every notebook here is executed end-to-end in CI by
[`tests/test_notebooks.py`](../tests/test_notebooks.py) (policy **D-019**); a
notebook is "done" only when it runs clean in the same suite as the unit tests.
Numeric claims that assert equality to R use the strict tier (`atol=0, rtol=0`);
figures are visual-only.

> **Running locally (Windows):** each notebook has a bootstrap cell that sets
> `R_HOME`. To run the CI test, set the R environment first:
> ```powershell
> $env:R_HOME = "C:\Program Files\R\R-4.5.2"
> $env:PATH = "C:\Program Files\R\R-4.5.2\bin\x64;" + $env:PATH
> python -m pytest tests/test_notebooks.py -q
> ```
> Set `RPM_SKIP_NOTEBOOKS=1` to skip them during the fast unit loop.

## Tutorials (`tutorials/`)

| Notebook | Story |
|---|---|
| `01_quickstart.ipynb` | "Robust regression for tomorrow's analysis" — mineral data |
| `02_outlier_detection.ipynb` | "Find multivariate outliers" — wine masking effect |
| `03_from_R.ipynb` | "Port my R scripts" — side-by-side R↔Python cheatsheet |

## Flagship reproductions

| Notebook | Reproduces | Figures |
|---|---|---|
| `ch5_mineral.ipynb` | `mineral.R` (`lmrobdetMM`) | 5.1–5.7 |
| `ch6_wine.ipynb` | `wine.R` (`covRobMM`, `pcaRobS`) | 6.3 + scree |
| `external_demo.ipynb` | `pense` / `gse` / `tsgs` stretch wrappers | — |
| `ui_demo.ipynb` | full user-facing API tour | — |

## Chapter galleries (`gallery/`)

Each gallery consolidates several example scripts for one book chapter (groups
A+B in [`../docs/notebook_plan.md`](../docs/notebook_plan.md) §2). Each reproduces
the robust-estimator core of its source scripts and cross-checks at least one
output bit-for-bit against direct R.

| Notebook | Example scripts | Estimators |
|---|---|---|
| `gallery/ch2_location_scale.ipynb` | `flour.R` | `locScaleM` |
| `gallery/ch4_regression.ipynb` | `shock.R`, `oats.R` | `lmrobM`, `rob.linear.test` |
| `gallery/ch5_regression.ipynb` | `algae.R`, `ExactFit.R`, `wood.R`, `step.R` | `lmrobdetMM`, `step.lmrobdetMM` |
| `gallery/ch6_multivariate.ipynb` | `biochem.R`, `vehicle.R`, `bus.R`, `wine1.R` | `covRobRocke`, `pcaRobS`, `covRobMM` |
| `gallery/ch7_glm.ipynb` | `leukemia.R`, `skin.R` | `BYlogreg`, `WBYlogreg`, `WMLlogreg` |
| `gallery/vignette.ipynb` | `fitmodelsRobStatTM.R`, `VignetteRobStatTM.R` | `lmrobdetMM`, `covClassic`, `covRob` |

The notebooks are regenerable from `gallery/_build_galleries.py` and
`_build_external_demo.py`.

## Out-of-scope example scripts

The following RobStatTM example scripts are **not** reproduced. Their *core*
estimator lives in a package outside this project's scope (the scope rule:
"every estimator exported by RobStatTM, plus `pense`/`GSE`/`TSGS`"). They are
listed here transparently rather than silently skipped — see **B-007** in
[`../project_memory/blockers.md`](../project_memory/blockers.md).

| Script | Blocking dependency | Reason |
|---|---|---|
| `autism.R` | `robustvarComp::varComprob` | robust variance-components — not in scope |
| `resex.R` | `robustarima` | robust ARIMA (time series) — not in NAMESPACE |
| `epilepsy.R` | `robustbase::glmrob` | robust GLM — not a wrapped RobStatTM function |
| `ar1.R` | RobStatTM time-series internals (not exported) | B-007 time-series gray zone |
| `ar3.R` | RobStatTM time-series internals (not exported) | B-007 |
| `identAR2.R` | RobStatTM time-series internals (not exported) | B-007 |
| `identMA1.R` | RobStatTM time-series internals (not exported) | B-007 |
| `MA1-AO.R` | RobStatTM time-series internals (not exported) | B-007 |

Comparators that several in-scope scripts call only as a *non-robust baseline*
(e.g. `quantreg::rq`, `robust::glmRob`, `rrcov::CovMcd`/`CovSest`, the
`fit.models` framework, and GSE helpers used purely for comparison) are dropped
or noted in the corresponding gallery, not reproduced.
