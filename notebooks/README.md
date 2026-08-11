# Notebooks

Reproductions of the RobStatTM textbook examples (Maronna, Martin, Yohai &
Salibián-Barrera, *Robust Statistics: Theory and Methods*, 2019) and the
package's example scripts, all built on `robstattm_py`.

> **Notebooks or [`examples/`](../examples/)?** Both cover the same 25 R
> scripts, differently. `examples/` is **one Python script per R script** — go
> there to port a specific R script, or to run one from a terminal. The
> galleries here are **one notebook per book chapter**, consolidating several
> scripts with figures rendered inline — go here to read a chapter's worth of
> material with the plots visible. Neither is a subset of the other, and both
> are executed in CI.

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
| `gallery/ch6_autism.ipynb` | `autism.R` | `varComprob` (robust variance components) |
| `gallery/ch7_glm.ipynb` | `leukemia.R`, `skin.R`, `epilepsy.R` | `BYlogreg`, `WBYlogreg`, `WMLlogreg`, `glmrob`, `cubinf` |
| `gallery/ch8_timeseries.ipynb` | `resex.R`, `ar3.R`, `identAR2.R`, `identMA1.R`, `MA1-AO.R`, `ar1.R` | `arima_rob` |
| `gallery/vignette.ipynb` | `fitmodelsRobStatTM.R`, `VignetteRobStatTM.R` | `lmrobdetMM`, `covClassic`, `covRob` |

The notebooks are regenerable from `gallery/_build_galleries.py`,
`_build_external_demo.py`, and `../dev/build_new_notebooks.py` (ch6 autism, ch7
epilepsy, ch8 time series).

> The ch6-autism / ch7-epilepsy / ch8 galleries need the optional R packages
> `robustvarComp`, `robcbi` (+ `robeth`), `robustarima` and `WWGbook` installed
> (see [`../docs/guides/external.md`](../docs/guides/external.md)). CI skips
> notebook execution (`RPM_SKIP_NOTEBOOKS=1`), so they run locally.

## Out-of-scope example scripts

**None.** As of **D-024** (2026-06-21), all **26/26** `robstattm/examples-scripts/`
scripts are reproduced from Python. The eight that previously blocked on external
packages — `autism.R` (`robustvarComp`), `epilepsy.R` (`robustbase::glmrob` +
`robcbi::cubinf`), and the six Chapter-8 time-series scripts (`resex.R`, `ar3.R`,
`identAR2.R`, `identMA1.R`, `MA1-AO.R`, `ar1.R`, all `robustarima`) — are now
covered by the optional `robstattm_py.external` wrappers and the galleries above.
This **closes B-007** (the Chapter-8 "inline time-series code" worry was moot —
`arima.rob` is a real exported entry point in `robustarima`).

Comparators that several scripts call only as a *non-robust baseline* (e.g.
`quantreg::rq`, `robust::glmRob`, `rrcov::CovMcd`/`CovSest`, the `fit.models`
framework, and the MATLAB-only `epiMP` estimator in `epilepsy.R`) are dropped,
documented as constants, or reproduced via direct R in the notebook — not exposed
as new Python wrappers.
