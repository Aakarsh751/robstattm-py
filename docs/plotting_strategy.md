# Plotting Strategy

**Requirement:** when the R package produces a plot, Python should reproduce it as faithfully as possible.
**Existing evidence:** `robstattm/python/figures/` already pairs R and Python plots side-by-side for `covRobMM`, `lmrobdetMM`, `pcaRobS`, and `scaleM`. The Python panels were drawn with matplotlib in the existing notebooks.

---

## 1. Three candidate paths

| Path | Description | Fidelity to R | Effort per plot | Python-native feel | CI cost |
|------|-------------|---------------|-----------------|--------------------|---------|
| **A. Direct R graphics through rpy2** | Open an R graphics device, run the R plot code, save the PNG; return the path to the user (or display inline in Jupyter via `IPython.display.Image`) | **Exact** — pixel-perfect | Lowest (we just call the R plot fn) | Lowest — the user is looking at R output | Low (PNG, no Python plotting libs needed) |
| **B. plotnine recreations** | Translate the ggplot-style R recipe into Python plotnine (proposal §3 endorses plotnine for this) | High — same grammar of graphics | Medium | High | Medium (plotnine has SciPy deps) |
| **C. matplotlib recreations** | Hand-redraw each plot in matplotlib | Medium — visual approximation only | Highest | High | Lowest |

**The proposal endorses A as the preferred default ("Use R-generated outputs through rpy2 whenever possible to preserve fidelity")** with matplotlib/plotnine for plot types where R doesn't have a built-in function. We adopt that policy.

---

## 2. Recommended decision tree

For each plot the proposal calls out:

```
Does RobStatTM ship an R function whose sole purpose is producing this plot?
├── Yes → Path A: call the R function via rpy2 to a PNG/SVG file device
│         Return the file path; offer .show() in Jupyter
└── No → Is the plot a standard statistical chart (residuals vs fitted,
        QQ plot, scree plot, distance–distance)?
        ├── Yes → Path B: plotnine recreation using the data the wrapper
        │         already returns (residuals, weights, distances, etc.)
        └── No → Path C: matplotlib + numpy from scratch
```

The user-facing API is uniform regardless of which path renders:

```python
fit = robstatm_py.lmrobdet_mm("zinc ~ copper", data=mineral)
ax  = robstatm_py.plotting.residuals(fit)         # returns a matplotlib Axes
img = robstatm_py.plotting.residuals(fit, backend="r")  # returns Path to PNG
```

`backend="auto"` (default) picks Path A if the wrapped object knows an R plot fn; otherwise Path B; otherwise Path C.

---

## 3. Per-plot inventory

| Plot type | Source (R) | Underlying data | Recommended path | Validation |
|-----------|-----------|-----------------|------------------|------------|
| Residuals vs. fitted (`lmrobdetMM`) | `plot.lmrobdetMM` (S3, lives in RobStatTM) | `fit$fitted.values`, `fit$residuals`, `fit$rweights` | **A** (R has it); also offer **B** plotnine | pytest-mpl image diff at `tol=2e-3` |
| QQ plot of robust residuals | `plot.lmrobdetMM` | residuals, scale | **A** | pytest-mpl |
| Robust weights vs. residual index | `plot.lmrobdetMM` | rweights | **B** (small plot; plotnine recipe is short and the data is already exposed) | pytest-mpl |
| Distance–distance plot (classical Mahalanobis vs. robust) | not a single R fn — RobStatTM examples do it inline | `covRobMM$dist`, `covClassic$dist` | **B** plotnine — proposal §10 Phase 3 explicitly lists a "distance–distance plot helper" | pytest-mpl |
| Scree plot (proportion of variance) | `plot.prcompRob` | `pcaRobS$eigenvalues` | **B** plotnine | pytest-mpl |
| PCA biplot (scores + loadings) | `biplot` (base R) | scores, loadings | **A** (matches book exactly) | image diff |
| Mineral dataset diagnostics (Fig 5.1–5.7) | `mineral.R` example script | mixed | **A** for the published figures; **B** for any derived inline panel | image diff against book PDFs is impossible (DPI differs); against R re-rendering at fixed DPI |
| Wine dataset Mahalanobis figure (Fig 6.3) | `wine.R` example | `covRobRocke$dist` | **B** plotnine | pytest-mpl |
| Bus dataset PCA figure (Fig 6.10) | `bus.R` example | `pcaRobS` scores | **B** plotnine + **A** R biplot side-by-side | image diff |

---

## 4. Implementation patterns

### 4.1 Path A — direct R graphics

```python
import tempfile, pathlib
from rpy2 import robjects as ro

def _r_plot(plot_call: str, *, dpi: int = 100, width: int = 6, height: int = 5) -> pathlib.Path:
    """Run an R plot expression to a temporary PNG and return the file path."""
    f = pathlib.Path(tempfile.mkstemp(suffix=".png")[1])
    ro.r(f'png(file="{f.as_posix()}", width={width}, height={height}, units="in", res={dpi})')
    try:
        ro.r(plot_call)
    finally:
        ro.r("dev.off()")
    return f
```

Wrappers expose this through helpers like `robstatm_py.plotting.residuals(fit, backend="r")` so the user never writes raw R code.

### 4.2 Path B — plotnine

```python
import pandas as pd
from plotnine import ggplot, aes, geom_point, geom_hline, labs, theme_bw

def residuals(fit, backend="auto"):
    df = pd.DataFrame({
        "fitted":    fit.fitted_values,
        "residuals": fit.residuals,
        "weight":    fit.rweights,
    })
    return (
        ggplot(df, aes("fitted", "residuals", color="weight"))
        + geom_hline(yintercept=0, linetype="dashed")
        + geom_point(alpha=0.7)
        + labs(x="Fitted values", y="Robust residuals")
        + theme_bw()
    )
```

Returns a plotnine `ggplot` object the user can `.draw()` or save with `.save(...)`. Matches the grammar-of-graphics expectations of R users.

### 4.3 Path C — matplotlib

Use only when neither A nor B fits cleanly (rare). Same data extraction; bespoke `fig, ax = plt.subplots()` recipe.

---

## 5. Image-regression testing

- Tool: `pytest-mpl`.
- Tolerance: `tol = 2e-3` (image L2 norm) for Path A (different runs of the same R code can shift one pixel), and `tol = 1e-2` for Paths B/C (plotnine has theme rendering quirks).
- Baselines stored under `tests/baseline_images/`.
- Re-baselining is a manual step (`pytest --mpl-generate-path=tests/baseline_images`) and must be done in a PR with mentor review.

---

## 6. Why not just "always matplotlib"

- The proposal is explicit that fidelity matters and that R-generated output should be used wherever possible.
- The mentor team will compare side-by-side against the book PDFs; matplotlib recreations introduce visual drift that obscures whether the underlying numerics match.
- We already have working evidence (`robstattm/python/figures/*.png`) that mixing both paths works: Path A for any plot the book renders with base R, Paths B/C for derived diagnostics.

---

## 7. Open questions

1. Should plotnine be a hard dependency or an optional extra (`pip install robstatm-py[plots]`)? Recommendation: **optional extra**, with helpful `ImportError` when a Path-B plot is requested without it installed.
2. R `png(...)` device on Windows occasionally needs `cairo` for anti-alias parity. Document in install guide.
3. SVG vs PNG default: PNG (broader notebook support), but expose `format="svg"` arg.
