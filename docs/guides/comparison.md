# Comparing robust and classical fits

A robust fit is most convincing next to the classical one it improves on. This
guide covers the two things RobStatTM-Py gives you for that:

1. **Comparison models** (`robstattm_py.comparison`): thin wrappers for the
   non-RobStatTM estimators you want as a baseline, each returning a native
   Python result with an R-style `.summary()`.
2. **`compare()`**: R's `fit.models` side-by-side view, lining two or more fits
   up so their coefficient tables and diagnostics sit column by column.

This is the workflow the RobStatTM book uses: fit `lm` and `lmrobdetMM` on the
same data and read the difference straight off.

## The comparison models

Each wraps a model from another R package and returns a native Python result
(numpy/pandas fields, `.summary()` porting R's `summary.*`, `.predict()`,
`.coef()`, `.vcov()`, `.confint()`):

| Function | R source | Role |
| --- | --- | --- |
| `rpm.lm` | `stats::lm` | classical least squares |
| `rpm.glm` | `stats::glm` | classical GLM (default `binomial`) |
| `rpm.rlm` | `MASS::rlm` | Huber-type M regression |
| `rpm.lts_reg` | `robustbase::ltsReg` | least trimmed squares |
| `rpm.lmrob` | `robustbase::lmrob` | robustbase MM regression |
| `rpm.cov_classic` | `RobStatTM::covClassic` | classical covariance |

`lts_reg` and `lmrob` are **stochastic**; call `rpm.set_seed(...)` first for a
reproducible fit.

### Fitting and reading a summary

```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()
ls = rpm.lm("zinc ~ copper", data=mineral)

print(ls.coef())          # named pandas Series
print(ls.summary())       # summary.lm: Estimate / Std. Error / t value / Pr(>|t|)
```

Every summary keeps R's own column names, so a `glm` shows `z value` and an
`rlm` shows no p-value column, exactly as in R.

### The full accessor set

```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()
ls = rpm.lm("zinc ~ copper", data=mineral)

ls.vcov()                 # coefficient covariance (vcov.lm)
ls.confint(level=0.95)    # confidence intervals (confint.lm)
ls.predict()              # in-sample predictions
ls.resid(); ls.fitted()   # pandas Series
ls.to_r()                 # the live R fit, for anything not wrapped here
```

Anything a model exposes in R that is not surfaced as a method is still reachable
through `.to_r()`.

## Side-by-side with `compare()`

`compare()` produces R's `fit.models` object. It needs the sibling package
`fitmodels-py`:

```
pip install robstattm-py[compare]
```

Pass two or more fits of the **same data**, named:

<!-- doc-check: skip - needs the optional fitmodels-py package -->
```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()
ls = rpm.lm("zinc ~ copper", data=mineral)
rob = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

fm = rpm.compare(LeastSquares=ls, Robust=rob)
print(fm.summary())       # R's summary.lmfm: both coefficient tables aligned
print(fm.coef())          # models x terms frame
fm["Robust"]              # reach one member back as a live R fit
```

The comparison exposes the full `fit.models` method set: `summary()`, `plot()`,
`coef()`, `residuals()`, `fitted()`, iteration, indexing and `rename()`.

Supported members are the regression results (`lm`, `glm`, `rlm`, `lts_reg`,
`lmrob`, and RobStatTM's `lmrobdet_mm` / `lmrobM` / `lmrobdet_dcml`).

### Covariance comparison

Classical against robust covariance is a `covfm`:

<!-- doc-check: skip - needs the optional fitmodels-py package -->
```python
import robstattm_py as rpm

wine3 = rpm.datasets.wine().iloc[:, :3]
cov_fm = rpm.compare(
    Classical=rpm.cov_classic(wine3),
    Robust=rpm.cov_rob(wine3),
)
print(cov_fm.summary())   # covariance/correlation estimates side by side
print(cov_fm.center())    # location estimates, one row per model
```

`covfm` offers `cov()`, `cor()`, `center()`, `eigenvalues()` and `distances()`
instead of `coef()` (location/scatter estimates have no coefficients, exactly as
R's `fit.models` decides).

## Notes

- `compare()` refits each model with the estimator's **defaults**, so a custom
  control on the original fit is not carried into the comparison.
- You cannot mix covariance and regression models in one `compare()`; R's
  `fit.models` compares `covfm` and `lmfm` separately.
- A runnable end-to-end port of the book's fit.models vignette lives at
  `examples/vignette_fit_models_comparison.py`.
