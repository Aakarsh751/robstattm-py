# Setup & utilities

Top-level helpers for configuring the R bridge, reproducibility, discovery, and
benchmarking.

## `check_setup()`

Verify that R, `rpy2`, and the required R packages are installed and loadable.
Prints a `READY` / `MISSING` checklist.

```python
import robstatm_py as rpm
rpm.check_setup()
```

## `set_seed(n)`

Seed **both** the Python and R random number generators so that stochastic
estimators (robust covariance, robust PCA) are reproducible and match R. Call it
immediately before the fit.

```python
rpm.set_seed(42)
cov = rpm.cov_rob_mm(rpm.datasets.wine())
```

## `help(name)`

Print the docstring for any wrapper, accepting **either** the R name or the
Python name.

```python
rpm.help("lmrobdetMM")     # by R name
rpm.help("lmrobdet_mm")    # by Python name — same output
```

## `list_names()`

Return the full R → Python name map, the single source of truth for the
correspondence used throughout these docs.

```python
mapping = rpm.list_names()
mapping["covRobMM"]        # -> "cov_rob_mm"
```

## Seeing R warnings and errors

The estimators run real R code, and that R code sometimes **warns** (e.g.
non-convergence, `NaNs produced`, rank deficiency). By default R *defers*
warnings, so a long fit used to end with only an opaque
`There were 50 or more warnings` line and the individual messages were lost.

RobStatTM-Py now captures every R warning and re-raises it through Python's
standard [`warnings`](https://docs.python.org/3/library/warnings.html) machinery
as a `RobStatTMWarning`. There are three ways to see them:

**1. They print automatically.** In a script or notebook the messages appear
inline, one per warning — no setup required.

**2. Record them programmatically** with `warnings.catch_warnings`:

```python
import warnings
import robstatm_py as rpm
from robstatm_py import RobStatTMWarning

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fit = rpm.lmrob_m("y ~ x", data=df)

for w in caught:
    if issubclass(w.category, RobStatTMWarning):
        print("R said:", w.message)
```

**3. Ask after the fact** with `last_r_warnings()`, which returns the messages
from the most recent R call (a fit *or* a result method such as `.summary()` /
`.predict()`):

```python
fit = rpm.lmrob_m("y ~ x", data=df)
rpm.last_r_warnings()
# ['M-step did NOT converge. Returning unconverged lM-estimate']
```

To **silence** them, filter like any Python warning:

```python
warnings.simplefilter("ignore", RobStatTMWarning)
```

To scope capture to a specific block (and get the list directly), use the
`capture_r_warnings()` context manager:

```python
from robstatm_py import capture_r_warnings

with capture_r_warnings() as messages:
    fit = rpm.lmrobdet_mm("y ~ x", data=df)
print(messages)   # list of R warning strings from inside the block
```

R **errors** are surfaced too: they are raised as `RobStatTMError` /
`RobStatTMRError`, carrying the R error text (and, where available, a curated
`.hint`) so you can act on them instead of seeing a raw rpy2 traceback.

## R-name compatibility layer

If you already know RobStatTM's R API, import wrappers under their original
names:

```python
from robstatm_py.compat_r import lmrobdetMM, covRobMM, BYlogreg
fit = lmrobdetMM("zinc ~ copper", data=rpm.datasets.mineral())
```

## Performance helpers

| Helper | Purpose |
|---|---|
| `rpm.r_started()` | `True` once the R bridge has been initialised. |
| `rpm.set_n_jobs(n)` | Set R's `mc.cores` for routines that parallelise; returns the previous value. |
| `rpm.bench.timer(fn)` | Time a call, splitting total vs. R-side vs. bridge overhead. |

```python
t = rpm.bench.timer(lambda: rpm.lmrobdet_mm("zinc ~ copper",
                                            data=rpm.datasets.mineral()))
print(f"{t.total_seconds * 1000:.1f} ms")
```

## Plotting (R graphics)

`rpm.plotting.r_plot(r_code, path=...)` renders any R graphics expression to a
PNG via R's own graphics device — pixel-equivalent to the textbook figures.

```python
rpm.plotting.r_plot(
    "plot(zinc ~ copper, data=mineral, pch=19)",
    path="scatter.png", dpi=120, width=5, height=4,
)
```
