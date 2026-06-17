# `lmrobdet_dcml`

> **R original:** `lmrobdetDCML` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; Robust Distance Constrained Maximum Likelihood estimators for linear regression

This function computes robust Distance Constrained Maximum Likelihood
estimators for linear models.

This function computes Distance Constrained Maximum Likelihood regression estimators
computed using an MM-regression estimator based on Pen~a-Yohai
candidates (instead of subsampling ones).
This function makes use of the functions `lmrob.fit`,
`lmrob..M..fit`, `.vcov.avar1`, `lmrob.S` and
`lmrob.lar`, from robustbase,
along with utility functions used by these functions,
modified so as to include use of the analytic form of the
optimal psi and rho functions (for the optimal psi function , see
Section 5.8.1 of Maronna, Martin, Yohai and Salibian Barrera, 2019)

## Usage

```python
from robstatm_py import lmrobdet_dcml

def lmrobdet_dcml(
                  formula: 'str | None' = None,
                  data: 'pd.DataFrame | None' = None,
                  X=None,
                  y=None,
                  control: 'LmrobdetControl | None' = None,
                  family: 'str | None' = None,
                  efficiency: 'float | None' = None,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `formula` | str \| None | `None` | a symbolic description of the model to be fit. |
| `data` | DataFrame \| None | `None` | an optional data frame, list or environment containing the variables in the model. If not found in `data`, model variables are taken from `environment(formula)`, which usually is the root environment of the current R session. |
| `X` | — | `None` | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `y` | — | `None` | Response vector of length `n` — used together with `X`. |
| `control` | LmrobdetControl \| None | `None` | a list specifying control parameters as returned by the function `lmrobdet.control`. |
| `family` | str \| None | `None` | Robust loss-function family shortcut (e.g. `"mopt"`, `"bisquare"`); sets the corresponding field on `control`. |
| `efficiency` | float \| None | `None` | Target Gaussian efficiency shortcut (e.g. `0.95`); sets the corresponding field on `control`. |


> **Note** — handled internally, not exposed in Python: `subset`, `weights`, `na.action`, `model`, `x`, `singular.ok`, `contrasts`, `offset`. These are constructed for you from the inputs above.


## Returns

A `LmrobdetDCMLResult` object. Its attributes mirror the fields of the R
`lmrobdetDCML` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `coefficients` | coefficients | The estimated vector of regression coefficients |
| `coef_names` | — | (Python-side convenience field) |
| `cov` | cov | The estimated covariance matrix of the regression estimates |
| `residuals` | residuals | The vector of residuals associated with the robust fit |
| `fitted_values` | fitted.values | Fitted values associated with the robust fit |
| `scale` | scale | The estimated scale of the residuals |
| `t0` | — | (Python-side convenience field) |
| `rank` | rank | Numeric rank of the fitted linear model |
| `converged` | converged | Logical value indicating whether IRWLS iterations for the MM-estimator have converged |
| `df_residual` | df.residual | The residual degrees of freedom |
| `iter` | iter | Number of IRWLS iterations for the MM-estimator |
| `rweights_mm` | — | (Python-side convenience field) |
| `formula` | — | (Python-side convenience field) |
| `control` | — | (Python-side convenience field) |


> **R fields not surfaced in Python** — the R `lmrobdetDCML` list also contains
> `rweightsMM`, `contrasts`, `xlevels`, `call`, `model`, `x`, `y`, `na.action`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `LmrobdetDCMLResult` object also provides these methods:

| Method | Description |
|---|---|
| `coef_df()` | Return ``coefficients`` as a pandas Series, indexed by coef name. |
| `hatvalues()` | Port of R's ``hatvalues.lmrob`` on an ``lmrobdetDCML`` fit. |
| `predict(newdata, se_fit)` | Port of R's ``predict.lmrob`` on an ``lmrobdetDCML`` fit. |
| `r_squared_classic()` | Classical (least-squares) R² for the DCML fit. |
| `summary()` | Port of R's ``summary.lmrobdetMM`` (DCML dispatches there). |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

mineral = rpm.datasets.mineral()

# DCML ("Distance Constrained Maximum Likelihood") blends a robust and a
# classical fit, giving high efficiency while staying robust to outliers.
fit = rpm.lmrobdet_dcml("zinc ~ copper", data=mineral)

print("coefficients:", dict(zip(fit.coef_names, fit.coefficients.round(4))))
print("residual scale:", round(fit.scale, 4))
# DCML has no canonical robust R²; use the classical least-squares R² instead.
print("classical R²:", round(fit.r_squared_classic(), 4))
```

<details>
<summary>Equivalent R code</summary>

```r
data(coleman, package='robustbase')
m1 <- lmrobdetDCML(Y ~ ., data=coleman)
m1
summary(m1)
```
</details>


## See also

- `DCML` (R-side helper; not a separate Python wrapper)
- `MMPY` (R-side helper; not a separate Python wrapper)
- `SMPY` (R-side helper; not a separate Python wrapper)



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>, based on `lmrob`. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `lmrobdetDCML`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
