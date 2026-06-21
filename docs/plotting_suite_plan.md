# Native Plotting Suite — Plan

**Created:** 2026-06-21. **Status:** PHASE 0 — awaiting user confirmation before Phase 1.
**Decision:** `project_memory/decisions.md` **D-023** (native plotting suite; native default backend; Path A = fidelity reference).
**Complements:** `docs/plotting_strategy.md` (Paths A/B/C), `docs/user_interface.md` §6/§10, `docs/quality_gates.md`.

> **Renumber note.** The resume prompt said "propose D-020", but D-020, D-021, and
> D-022 are already used. This work is recorded as **D-023**.

---

## 0. Why this exists

Today `src/robstatm_py/plotting.py` is **Path A only**: every helper *refits the model
in R*, opens a PNG device, and returns a `pathlib.Path`. That is pixel-faithful to the
book but:

- not composable — you cannot pass `ax=` and build a subplot grid;
- not themable — no palettes, no outlier annotation, no style control;
- refits on every call (slow, and needs `_data`/`_r_control`);
- returns a `Path`, contradicting `user_interface.md §6` which advertises
  `ax = fit.plot_residuals()` → a matplotlib `Axes`.

The textbook reproductions (mineral Figs 5.1–5.7, wine Fig 6.3, bus/vehicle PCA, flour
Ch2) are currently hand-drawn with matplotlib **inside the notebooks** — there is no
reusable, public plotting API for them.

This suite adds that API **without removing Path A** (kept as the fidelity reference,
reachable with `backend="r"`).

---

## 1. Module layout

```
src/robstatm_py/
  plot/                      # NEW public subpackage  →  rpm.plot
    __init__.py              # public surface: set_theme/get_theme/PlotStyle,
                             #   all plot fns, backend constants
    _deps.py                 # lazy import guards (matplotlib / plotnine) with a
                             #   helpful ImportError naming the [plots] extra
    _style.py                # PlotStyle dataclass + theme registry + palettes
    _backends.py             # resolve backend="auto"|"native"|"matplotlib"
                             #   |"plotnine"|"r"; dispatch table per plot fn
    _data.py                 # extract plot-ready arrays from result objects
                             #   (NO refit — reads frozen dataclass fields only)
    regression.py            # residuals, qq, scale_location, weights,
                             #   resid_vs_leverage, diagnostics,
                             #   scatter_with_fit, compare_fits
    multivariate.py          # distance_distance, mahalanobis_panel, scree,
                             #   scores, loadings, biplot, cov_heatmap
    univariate.py            # location_scale
    _r_backend.py            # adapter to the existing Path-A helpers
  plotting.py                # KEPT — back-compat alias; re-exports Path-A fns
                             #   (r_plot, show_png, residuals, qq, diagnostics)
```

`robstatm_py.plot` is re-exported from `__init__.py` alongside `plotting`. Importing
either is cheap; matplotlib/plotnine are imported only when a native/plotnine plot is
actually drawn.

---

## 2. Backend policy (D-023)

`rpm.plot.<fn>(result, *, backend="auto", ax=None, style=None, **kw)`

| `backend`               | Engine               | Returns            | Refits? |
|-------------------------|----------------------|--------------------|---------|
| `"auto"` (default)      | native mpl, else R   | `Axes`/`Figure`/`Path` | no (native) |
| `"native"`/`"matplotlib"` | matplotlib (primary) | `Axes` / `Figure`  | **no** |
| `"plotnine"`            | plotnine (secondary) | `ggplot`           | **no** |
| `"r"`                   | R graphics (Path A)  | `pathlib.Path`     | yes (in R) |

- `"auto"` → native matplotlib when a native renderer exists **and** matplotlib is
  importable; else `"r"` if an R renderer exists; else a helpful `ImportError`
  (`pip install "robstatm-py[plots]"`).
- **matplotlib is primary** (Axes return type per spec, composable `ax=`, lighter dep,
  already the engine in the notebooks/archive). **plotnine is secondary** for
  grammar-of-graphics users.
- **D-008 stays in force**: Path A is the fidelity reference; native is the default only
  for this new public suite.

---

## 3. Theme / style API

```python
import robstatm_py as rpm

rpm.plot.set_theme("publication")          # named theme (global default)
rpm.plot.set_theme("book", font_scale=1.1) # named theme + overrides
style = rpm.plot.PlotStyle(weight_cmap="magma", annotate_outliers=True)
rpm.plot.residuals(fit, style=style, highlight=[3, 17], labels=names)
```

`PlotStyle` (frozen dataclass) — proposed fields:

| Field | Default | Purpose |
|-------|---------|---------|
| `palette` | Okabe–Ito (cb-safe) | categorical series colors |
| `weight_cmap` | `"viridis"` | continuous cmap for robust-weight coloring |
| `inlier_color` / `outlier_color` | steel / firebrick | when not weight-mapped |
| `fit_color` / `ols_color` / `ref_line_color` | — | regression lines / 0-line |
| `point_size`, `alpha` | 36, 0.85 | marker styling |
| `figsize`, `dpi` | (6.4, 4.8), 110 | new-figure sizing |
| `spine_top`, `spine_right`, `grid` | False, False, True | axis chrome |
| `font_scale` | 1.0 | scales all font sizes |
| `annotate_outliers` | True | label flagged points |
| `outlier_weight_thresh` | 0.5 | `rweights <` ⇒ flagged |
| `outlier_resid_thresh` | 2.5 | `|std resid| >` ⇒ flagged |
| `color_by_weight` | True | color points by robust weight |

Named themes: `"publication"` (default — clean, no top/right spines, cb-safe palette),
`"book"` (mimics the Maronna et al. base-R look), `"minimal"`, `"dark"`.

Resolution order per call: explicit `**kw` > `style=` > global theme (`set_theme`) >
built-in `"publication"`.

---

## 4. Return-type contract

- matplotlib: single-panel → `Axes`; multi-panel (`diagnostics`) → `Figure`. Accepts
  `ax=` (single) / `fig=` (multi); creates one if `None`. **Never calls `plt.show()`.**
- plotnine: returns a `ggplot` object.
- r: returns `pathlib.Path` to a PNG (unchanged Path-A behavior).
- Common kwargs on every fn: `backend`, `ax`/`fig`, `style`, `highlight` (indices),
  `labels` (point labels), `annotate` (override), `title`, `save` (path; writes file),
  `show` (default `False`).

---

## 5. Plot inventory

Native = matplotlib renderer to build. ✓R = a Path-A (`backend="r"`) equivalent already
exists / will be wired. "Reproduces" = textbook figure or archive reference it covers.

### 5.1 Regression — from `lmrobdet_mm` / `lmrobdet_dcml` / `lmrob_m`
Data used (no refit): `residuals`, `fitted_values`, `rweights`, `scale`,
`coefficients`/`coef_names`; `.hatvalues()` for leverage; `_data` for scatter overlays.

| fn | Native | ✓R | Reproduces |
|----|:--:|:--:|---|
| `residuals(fit)` resid vs fitted, weight-colored, outliers labeled | ✓ | ✓ | Fig 5.3 |
| `qq(fit)` normal QQ of standardized residuals + robust ref line | ✓ | ✓ | Figs 5.2 / 5.6 |
| `scale_location(fit)` √\|std resid\| vs fitted | ✓ | ✓ | — |
| `weights(fit)` robust weight vs index (cutoff line) | ✓ | – | strategy Path B |
| `resid_vs_leverage(fit)` std resid vs hatvalue (influence) | ✓ | – | **new analytical** |
| `diagnostics(fit)` 2×2 panel (combines the above) | ✓ | ✓ | Fig 5.5 spirit |
| `scatter_with_fit(fit, x=...)` data + robust line (+optional OLS) | ✓ | – | Figs 5.1 / 5.4 |
| `compare_fits([...], x=...)` overlay several lines/fits on a scatter | ✓ | – | Figs 5.1 / 5.7 |

### 5.2 Multivariate — `cov_classic` / `cov_rob_mm` / `cov_rob_rocke` / `pca_rob_s` / `prcomp_rob`
Data used: `dist`, `center`, `cov`, `cor`, `wts`; PCA `repre`/`scores`, `prop_spc`,
`propex`, `eigvec`/`rotation`, `sdev`, `mu`, `q`.

| fn | Native | ✓R | Reproduces |
|----|:--:|:--:|---|
| `distance_distance(robust, classical)` robust vs classical Mahalanobis + χ² cutoff | ✓ | ✓ | archive `covRob_distance_distance` |
| `mahalanobis_panel(cov)` √dist vs index + cutoff + outlier labels | ✓ | – | Fig 6.3 |
| `scree(pca)` proportion of (robust) scale, bars + cumulative line | ✓ | – | bus/wine scree |
| `scores(pca, comps=(0,1))` score scatter, outliers highlighted | ✓ | – | Fig 6.10 |
| `loadings(pca)` loadings heatmap (or arrows) | ✓ | – | **new analytical** |
| `biplot(pca)` scores + loading arrows overlaid | ✓ | ✓R(base biplot) | Fig 6.10 |
| `cov_heatmap(cov, other=None)` robust corr, or robust−classical Δ | ✓ | – | **new analytical** |

### 5.3 Univariate — `loc_scale_m`
| fn | Native | ✓R | Reproduces |
|----|:--:|:--:|---|
| `location_scale(result, data)` hist/density + robust μ±disper vs mean±sd bands | ✓ | – | Ch2 flour |

### 5.4 New analytical plots (NOT in the example notebooks)
Per the user's request — demonstrate working with the data in Python, all statistically
correct:
- `resid_vs_leverage` — robust influence diagnostic (std residual × leverage).
- `weight_ecdf(fit)` — ECDF / lollipop of robust weights showing how much mass is
  downweighted (the robustness "fingerprint").
- `cov_heatmap(robust, classical)` — Δ-correlation heatmap: how outliers distort the
  classical correlation structure.
- `loadings` heatmap — interpret robust principal directions across original variables.
- `outlier_overlay` (compose) — flag points that are outliers in *both* the regression
  residual sense and the Mahalanobis/leverage sense.

---

## 6. Tests (`tests/plot/`)

All import-guarded: `pytest.importorskip("matplotlib")` (and `plotnine` where relevant);
the fast unit loop and R-free CI still pass when `[plots]` is absent.

- `test_style.py` — `PlotStyle` defaults, named-theme registry, `set_theme`/`get_theme`,
  override resolution order.
- `test_backends.py` — `backend="auto"` resolves native when mpl present; falls back to
  `"r"`; raises a clear `ImportError` when neither available.
- `test_regression_diagnostics.py` — return types (`Axes`/`Figure`), `ax=` is honored
  (no new figure created), `highlight`/`labels`/`annotate` take effect, **no-refit guard**
  (native path must not call into R — assert the R bridge is untouched), `plt.show` never
  called.
- `test_multivariate.py`, `test_univariate.py` — same contract for those families.
- `pytest-mpl` baselines: **opt-in / visual-only** (consistent with D-019); not part of
  the strict gate. Baselines, if added, live in `tests/plot/baseline/` and are
  re-generated only with mentor sign-off.

Numerical fidelity is already guaranteed upstream: native plots consume strict-tier
arrays, and the R reference is one `backend="r"` away.

---

## 7. Docs & Sphinx site

- `docs/plotting_strategy.md` §3 — status column updated to point at the native renderers.
- `docs/guides/plotting.md` — NEW user guide: quickstart, backend switch, theming,
  per-plot gallery, customization recipes, the new analytical plots.
- Sphinx: add `guides/plotting` to the toctree; a **Plotting gallery** page showing, for
  each figure, **native vs `backend="r"` (Path A) side by side**, plus the
  customization showcase and the new analytical plots. (Path-A/R examples are not yet on
  the site — this adds them, per the user's request.)
- Images for the static site are pre-rendered to `docs/_static/plots/` by a small
  `docs/scripts/render_plots.py` (run locally with R available; the Sphinx build itself
  stays R-free, matching `conf.py`'s no-import policy).

---

## 8. Demo notebook (Phase 3)

`notebooks/plotting_suite_demo.ipynb`:
1. Path A vs native side-by-side for the headline figures.
2. Theme/customization tour (palettes, weight-coloring, outlier annotation, subplot
   composition via `ax=`).
3. The new analytical plots on textbook data.
Added to the `tests/test_notebooks.py` sweep (executed clean in CI per D-019).

---

## 9. Sequencing (maps to the resume prompt's phases)

- **Phase 1** — `plot/` package + `PlotStyle`/themes + `_backends.py` + regression
  diagnostics (`residuals`/`qq`/`scale_location`/`weights`/`resid_vs_leverage`/
  `diagnostics`); rewire `_result_mixins` shortcuts; `tests/plot/test_regression_*`.
- **Phase 2** — multivariate (`distance_distance`/`mahalanobis_panel`/`scree`/`scores`/
  `loadings`/`biplot`/`cov_heatmap`) + univariate (`location_scale`) +
  `scatter_with_fit`/`compare_fits`; tests.
- **Phase 3** — `notebooks/plotting_suite_demo.ipynb` + notebook CI.
- **Phase 4** — `docs/guides/plotting.md`, strategy §3 update, Sphinx gallery (native +
  Path A + new analytical plots).

---

## 10. Phase-0 decisions (CONFIRMED by user 2026-06-21)

1. **`fit.plot_*()` return type** → `Axes`/`Figure` (native default); PNG still via
   `backend="r"`. ✅ confirmed.
2. **Primary engine** → matplotlib primary, plotnine secondary. ✅ confirmed.
3. **Image tests** → visual-only / opt-in for now; no `pytest-mpl` baselines yet
   (consistent with D-019). ✅ confirmed.
