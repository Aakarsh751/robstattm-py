# Result-object methods

Every wrapper returns a small, typed result object (a frozen dataclass) instead
of a raw R list. Besides the data attributes documented on each function page,
these objects carry **methods** that mirror R's S3 generics (`summary`,
`predict`, …) plus Python conveniences.

## Available on every result

| Method | Returns | Description |
|---|---|---|
| `to_dict()` | `dict` | Plain-Python view of all fields (JSON-friendly). |
| `to_r()` | rpy2 object | The underlying R object, for an `rpy2` round-trip. |
| `coef_df()` | `pandas.Series` | Coefficients indexed by name (regression/GLM results). |
| `_repr_html_()` | `str` | Rich HTML table — renders automatically in Jupyter. |

```python
import robstatm_py as rpm

fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
fit.to_dict()        # {'coefficients': array([...]), 'scale': ..., ...}
fit.coef_df()        # (Intercept)  ...   copper  ...
```

## Regression results (`lmrobdet_mm`, `lmrobdet_dcml`, `lmrob_m`)

| Method | Description |
|---|---|
| `summary()` | Full table: estimates, robust standard errors, t-values, p-values, R², scale. |
| `predict(newdata=None, se_fit=False)` | Fitted/predicted values, optionally with standard errors. |
| `hatvalues()` | Leverages of the fitted model. |
| `coef()` | Coefficients as a named pandas `Series`. |
| `rfpe(both_vals=False)` | Robust Final Prediction Error (`lmrobdet_mm` only). |
| `drop1(scope=None, scale=None)` | Single-term-deletion RFPE table (`lmrobdet_mm` only). |
| `r_squared_classic()` | Classical least-squares R² (`lmrobdet_dcml` only — DCML has no robust R²). |

```python
fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())

print(fit.summary())          # coefficient table
fit.predict()                 # in-sample fitted values
fit.hatvalues()               # leverages
fit.rfpe()                    # robust final prediction error
```

> **Note** — `lmrob_m` results inherit a class that does not derive from R's
> `lmrob`, so its `predict()` / `hatvalues()` are computed from R primitives
> (bit-equal to the S3 path). Its `predict()` takes only `newdata` (no
> `se_fit` — the fit carries no QR decomposition for prediction standard
> errors), and it does not provide `rfpe()` or `drop1()`.

## Covariance & PCA results

| Method | Description |
|---|---|
| `summary()` | Eigenvalues of the covariance matrix (`cov_*`) or variance-explained (`prcomp_rob`). |

```python
cov = rpm.cov_classic(rpm.datasets.wine())
print(cov.summary())          # eigenvalues
```

## Diagnostic plots

Regression results expose diagnostic-plot shortcuts. By default they return a
**matplotlib `Axes`/`Figure`** from the native plotting suite
([`robstatm_py.plot`](plotting.md)); pass `backend="r"` for the pixel-faithful
PNG drawn by R's own graphics device.

| Method | Plot | Native return |
|---|---|---|
| `plot_residuals()` | Residuals vs. fitted (coloured by robust weight). | `Axes` |
| `plot_qq()` | Normal Q-Q plot of standardized residuals. | `Axes` |
| `plot_diagnostics()` | The 2×2 diagnostic panel. | `Figure` |

```python
fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())

ax  = fit.plot_residuals()                 # native matplotlib Axes
fig = fit.plot_diagnostics()               # native 2×2 Figure
png = fit.plot_residuals(backend="r",      # Path-A PNG (pathlib.Path)
                         path="resid.png")
```

See the **[Plotting guide](plotting.md)** for the full native suite (themes,
multivariate/univariate plots, customization, and the R/native gallery).
