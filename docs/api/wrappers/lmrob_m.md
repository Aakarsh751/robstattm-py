# `lmrob_m`

> **R original:** `lmrobM` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; Robust estimators for linear regression with fixed designs

This function computes a robust regression
estimator for a linear models with fixed designs.

This function computes robust regression estimators for linear
models with fixed designs. It computes an L1 estimator,
and uses it as a starting point to find a minimum of a
re-descending M estimator. The scale is set to a quantile of the
absolute residuals from the L1 estimator.
This function makes use of the functions `lmrob.fit`,
`lmrob..M..fit`, `.vcov.avar1`, `lmrob.S` and
`lmrob.lar`, from robustbase,
along with utility functions used by these functions,
modified so as to include use of the analytic form of the
optimal psi and rho functions (for the optimal psi function , see
Section 5.8.1 of Maronna, Martin, Yohai and Salibian Barrera, 2019)

## Usage

```python
from robstatm_py import lmrob_m

def lmrob_m(
            formula: 'str | None' = None,
            data: 'pd.DataFrame | None' = None,
            X=None,
            y=None,
            control: 'LmrobMControl | None' = None,
            bb: 'float | None' = None,
            family: "Literal['opt', 'mopt', 'bisquare', 'huber', 'moptv0', 'optv0'] | None" = None,
            efficiency: 'float | None' = None,
            max_it: 'int | None' = None,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `formula` | str \| None | `None` | a symbolic description of the model to be fit. |
| `data` | DataFrame \| None | `None` | an optional data frame, list or environment containing the variables in the model. If not found in `data`, model variables are taken from `environment(formula)`, which usually is the root environment of the current R session. |
| `X` | — | `None` | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `y` | — | `None` | Response vector of length `n` — used together with `X`. |
| `control` | LmrobMControl \| None | `None` | a list specifying control parameters as returned by the function `lmrobM.control`. |
| `bb` | float \| None | `None` |  |
| `family` | Literal['opt', 'mopt', 'bisquare', 'huber', 'moptv0', 'optv0'] \| None | `None` | Robust loss-function family shortcut (e.g. `"mopt"`, `"bisquare"`); sets the corresponding field on `control`. |
| `efficiency` | float \| None | `None` | Target Gaussian efficiency shortcut (e.g. `0.95`); sets the corresponding field on `control`. |
| `max_it` | int \| None | `None` |  |


> **Note** — handled internally, not exposed in Python: `subset`, `weights`, `na.action`, `model`, `x`, `singular.ok`, `contrasts`, `offset`. These are constructed for you from the inputs above.


## Returns

A `LmrobMResult` object. Its attributes mirror the fields of the R
`lmrobM` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `coefficients` | coefficients | The estimated vector of regression coefficients |
| `coef_names` | — | Names of the estimated coefficients, aligned positionally with `coefficients`. |
| `scale` | scale | The estimated scale of the residuals |
| `residuals` | residuals | The vector of residuals associated with the robust fit |
| `loss` | — | Value of the objective function at the final M-estimator. |
| `converged` | converged | Logical value indicating whether IRWLS iterations for the MM-estimator have converged |
| `iter` | iter | Number of IRWLS iterations for the MM-estimator |
| `fitted_values` | fitted.values | Fitted values associated with the robust fit |
| `rweights` | rweights | Robustness weights for the MM-estimator |
| `rank` | rank | Numeric rank of the fitted linear model |
| `cov` | cov | The estimated covariance matrix of the regression estimates |
| `df_residual` | df.residual | The residual degrees of freedom |
| `degree_freedom` | — | The residual degrees of freedom. |
| `r_squared` | — | The robust multiple correlation coefficient (robust R²). |
| `formula` | — | The model formula used for the fit (echoes the input). |


> **R fields not surfaced in Python** — the R `lmrobM` list also contains
> `contrasts`, `xlevels`, `call`, `model`, `x`, `y`, `na.action`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `LmrobMResult` object also provides these methods:

| Method | Description |
|---|---|
| `coef()` | Return coefficients as a named pandas Series. |
| `coef_df()` | Return ``coefficients`` as a pandas Series, indexed by coef name. |
| `hatvalues()` | Hat-matrix diagonal computed via QR of ``sqrt(rweights) * X``. |
| `predict(newdata)` | Predictions on ``data`` (or ``newdata`` if given). |
| `summary()` | Port of R's ``summary.lmrobdetMM`` (lmrobM dispatches there). |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

mineral = rpm.datasets.mineral()

# lmrob_m fits an M-estimator of regression (a simpler robust fit than the
# full MM-estimator). Good when you want a fast, bounded-influence fit.
fit = rpm.lmrob_m("zinc ~ copper", data=mineral)

print(fit)                       # short summary
print()
print("coefficients:", dict(zip(fit.coef_names, fit.coefficients.round(4))))
print("robust scale:", round(fit.scale, 4))
```

<details>
<summary>Equivalent R code</summary>

```r
data(shock)
cont <- lmrobM.control(bb = 0.5, efficiency = 0.85, family = "bisquare")
shockrob <- lmrobM(time ~ n.shocks, data = shock, control=cont)
shockrob
summary(shockrob)
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Victor Yohai, <vyohai@gmail.com>, based on `lmrob`. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `lmrobM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
