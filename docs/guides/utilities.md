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
