# Examples

A runnable Python script for every example script that ships with the RobStatTM
R package (`system.file("scripts", package = "RobStatTM")`), written against
`robstattm_py`'s public API.

These are ports, not translations. Each script keeps its source's structure,
section comments, example numbers and figure numbers so you can hold the book —
Maronna, Martin, Yohai & Salibián-Barrera, *Robust Statistics: Theory and
Methods (with R)*, 2nd ed. — open next to the terminal and follow along. Where a
result differs from the printed one, the script says so and why.

## Running them

```bash
pip install -e ".[examples]"     # matplotlib + scipy, for the comparators
python examples/ch05_mineral_lmrobdet_mm.py
```

They can be run from anywhere; each is self-contained and prints to stdout.
Figures are written to `examples/_figures/` rather than shown, so nothing
blocks. Every script is executed end to end by
[`tests/test_examples.py`](../tests/test_examples.py) — an example that does not
run is a failing test, not a stale file.

A script needing an R package you do not have exits with status 77 and a line
telling you what to install. Nothing tracebacks.

## The map

| Python script | R script | Chapter / example | Estimators |
|---|---|---|---|
| `ch02_flour_location_scale.py` | `flour.R` | 2, Table 2.4 | `locScaleM` |
| `ch04_shock_lmrobm.py` | `shock.R` | 4.1, Figs 4.1/4.3 | `lmrobM` |
| `ch04_oats_robust_anova.py` | `oats.R` | 4.2, Figs 4.2/4.4 | `lmrobM`, `rob.linear.test` |
| `ch05_mineral_lmrobdet_mm.py` | `mineral.R` | 5.1, Figs 5.1–5.7 | `lmrobdetMM` |
| `ch05_wood_leverage.py` | `wood.R` | 5.2, Figs 5.8–5.12 | `lmrobdetMM` |
| `ch05_step_variable_selection.py` | `step.R` | 5.3, Table 5.2 | `step.lmrobdetMM` |
| `ch05_algae_multiple_regression.py` | `algae.R` | 5.4, Figs 5.14–5.15 | `lmrobdetMM` |
| `ch05_exactfit_synthetic.py` | `ExactFit.R` | 5.5 | `lmrobdetMM` |
| `ch06_biochem_bivariate.py` | `biochem.R` | 6.1, Figs 6.1/6.2 | `covRobMM` |
| `ch06_wine_covariance.py` | `wine.R` | 6.2, Fig 6.3 | `covRobMM`, `covRobRocke` |
| `ch06_vehicle_rocke.py` | `vehicle.R` | 6.3, Fig 6.7 | `covRobRocke` |
| `ch06_bus_robust_pca.py` | `bus.R` | 6.4, Fig 6.10, Table 6.6 | `pcaRobS` |
| `ch06_wine_missing_and_cellwise.py` | `wine1.R` | 6.5/6.6, Figs 6.11/6.12 | `GSE`, `TSGS`, `covRobMM` |
| `ch06_autism_variance_components.py` | `autism.R` | 6.7, Tables 6.8/6.9 | `varComprob` |
| `ch07_leukemia_logistic.py` | `leukemia.R` | 7.1, Fig 7.4, Table 7.1 | `logregBY`, `logregWBY`, `logregWML` |
| `ch07_skin_logistic.py` | `skin.R` | 7.2, Fig 7.5 | `logregBY`, `logregWBY`, `logregWML` |
| `ch07_epilepsy_poisson.py` | `epilepsy.R` | 7.3, Figs 7.6/7.7 | `glmrob`, `cubinf` |
| `ch08_ar1_outlier_types.py` | `ar1.R` | 8, Fig 8.6 | — (contamination types) |
| `ch08_ar3_estimator_comparison.py` | `ar3.R` | 8, Table 8.1 | `arima.rob`, `lmrobdetMM` |
| `ch08_identar2_identification.py` | `identAR2.R` | 8.3, Figs 8.7/8.8 | `arima.rob` |
| `ch08_identma1_identification.py` | `identMA1.R` | 8.4, Figs 8.9/8.10 | `arima.rob` |
| `ch08_ma1_ao_estimation.py` | `MA1-AO.R` | 8.5, Fig 8.11, Table 8.4 | `arima.rob` |
| `ch08_resex_seasonal.py` | `resex.R` | 8.6, Figs 8.12/8.13, Table 8.5 | `arima.rob` |
| `vignette_fit_models_comparison.py` | `fitmodelsRobStatTM.R` | vignette | `lmrobdetMM`, `covClassic`, `covRob` |
| `vignette_package_tour.py` | `VignetteRobStatTM.R` | vignette | the package tour |

25 R scripts, 25 Python scripts.

`wineDougtest.R`, which appears in the `robstattm/examples-scripts/` copy but
not upstream, is byte-identical to `wine.R` and so is covered by
`ch06_wine_covariance.py` rather than duplicated.

## Optional R packages

Most scripts need only RobStatTM. These need more, and skip cleanly without it:

| Script | Needs |
|---|---|
| `ch05_wood_leverage.py` | `robustbase` (the `wood` dataset) |
| `ch06_wine_missing_and_cellwise.py` | `GSE` |
| `ch06_autism_variance_components.py` | `robustvarComp`, `nlme`, `WWGbook` |
| `ch07_epilepsy_poisson.py` | `robustbase`, `robcbi` (which needs `robeth`) |
| `ch08_*` | `robustarima` |
| `vignette_package_tour.py` | `robustbase` (the `wood` dataset) |

Install them with `robstattm-py install-r-packages <name> ...`.

## Choices that apply to every script

**Non-robust comparators stay in Python.** Several R scripts draw an `lm`, an
`rq` (L1) or a `glm` line next to the robust fit. Those are foils, not
estimators this package wraps, so they are computed in `_common.py` with plain
numpy rather than by adding wrappers or dependencies. `quantreg`,
`rrcov::CovMcd`/`CovSest` and the `fit.models` framework are handled the same
way — see each script's docstring for what was substituted.

**Simulated data comes from R's RNG.** The Chapter 5 and 8 scripts that simulate
draw through R under the same `set.seed` the R script uses, so the numbers are
directly comparable with it. Drawing from `numpy.random` instead would give a
different sample from the same distribution: the conclusions would hold, the
printed values would not match.

**The book's controls, not today's defaults.** Several scripts specify
`family = "bisquare", efficiency = 0.85` because that is what the book used;
`lmrobdet.control` now defaults to `"mopt"` at 0.95. Where the difference
matters, both are fitted and printed.

**Reported, not narrated.** Where a result contradicts the obvious story — the
robust scale that is *larger* than the least-squares one in `algae`, the
automatic order selection that overshoots in `identAR2`, the robust correlation
in `biochem` that only moves halfway — the script says so and explains it. The
comment next to a number always describes the number that is actually printed.
