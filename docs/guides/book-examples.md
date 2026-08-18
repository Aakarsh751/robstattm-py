# Reproducing the book's examples

The RobStatTM R package ships 25 example scripts, one per worked example in
Maronna, Martin, Yohai & Salibián-Barrera, *Robust Statistics: Theory and
Methods (with R)*. You can list them from R with
`system.file("scripts", package = "RobStatTM")`.

Every one of them has a Python counterpart in the
[`examples/`](https://github.com/Aakarsh751/robstattm-py/tree/main/examples)
directory of this repository, written against this package's public API.

## Running them

```bash
git clone https://github.com/Aakarsh751/robstattm-py
cd robstattm-py
pip install -e ".[examples]"

python examples/ch05_mineral_lmrobdet_mm.py
```

The `[examples]` extra adds `matplotlib` and `scipy`. Neither is a dependency of
the package: they are there for the *non-robust* comparators, the least-squares
line, the classical F test, that the R scripts plot next to the robust fit.

Scripts print to stdout and write figures to `examples/_figures/`; nothing
opens a window, so they are safe to run over SSH or in CI.

## What they cover

| Chapter | Scripts | What they show |
|---|---|---|
| 2 | `flour` | M-estimation of location against the mean and a trimmed mean |
| 4 | `shock`, `oats` | M-regression; robust ANOVA via `rob.linear.test` |
| 5 | `mineral`, `wood`, `step`, `algae`, `ExactFit` | MM-regression, high-leverage outliers, RFPE variable selection, the exact-fit property |
| 6 | `biochem`, `wine`, `vehicle`, `bus`, `wine1`, `autism` | Robust covariance, masking, the Rocke estimator, robust PCA, missing and cellwise data, variance components |
| 7 | `leukemia`, `skin`, `epilepsy` | Robust logistic and Poisson regression |
| 8 | `ar1`, `ar3`, `identAR2`, `identMA1`, `MA1-AO`, `resex` | Additive vs innovation outliers, model identification, filtered tau estimation |
|, | `fitmodelsRobStatTM`, `VignetteRobStatTM` | The two package vignettes |

The full script-by-script map, including which optional R packages each needs,
is in
[`examples/README.md`](https://github.com/Aakarsh751/robstattm-py/blob/main/examples/README.md).

## They are tested, not just written

`tests/test_examples.py` executes every script end to end in a subprocess on
every CI runner and asserts a zero exit status. An example that stops working
is a failing build.

A script that needs an R package you do not have prints one line saying which,
and exits with status 77, reported as a skip naming the package, never as a
pass. Most scripts need only RobStatTM; the exceptions are listed in the
examples README.

## What was substituted, and why

Several R scripts draw a non-robust line for contrast: `lm`, `quantreg::rq`,
`glm`, `rrcov::CovMcd`, or the `fit.models` framework. Those are comparators,
not estimators this package wraps, so they are computed in plain numpy in
`examples/_common.py` rather than becoming new wrappers or new dependencies.
Each script's docstring names what it substituted.

The simulated examples in Chapters 5 and 8 draw their data from **R's** RNG
under the same `set.seed` the R script uses, so their output is directly
comparable with running the R script. Drawing from `numpy.random` would give a
different sample from the same distribution: the conclusions would hold, but the
printed numbers would not line up.

Where a script's result contradicts the tidy version of the story, a robust
scale that comes out *larger* than the least-squares one, an automatic order
selection that overshoots, a robust correlation that only moves halfway, the
script says so and explains why. The comment next to a number always describes
the number that is actually printed.
