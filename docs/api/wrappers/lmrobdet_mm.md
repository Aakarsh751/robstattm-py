# `lmrobdet_mm`

> **R original:** `lmrobdetMM` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; Robust Linear Regression Estimators

This function computes an MM-regression estimators for linear models
using deterministic starting points.

This function computes MM-regression estimators
computed using Pen~a-Yohai candidates (instead of subsampling ones).
This function makes use of the functions `lmrob.fit`,
`lmrob..M..fit`, `.vcov.avar1`, `lmrob.S` and
`lmrob.lar`, from robustbase,
along with utility functions used by these functions,
modified so as to include use of the analytic form of the
optimal psi and rho functions (for the optimal psi function , see
Section 5.8.1 of Maronna, Martin, Yohai and Salibian Barrera, 2019).

## Usage

```python
from robstatm_py import lmrobdet_mm

def lmrobdet_mm(
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

A `LmrobdetMMResult` object. Its attributes mirror the fields of the R
`lmrobdetMM` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `coefficients` | coefficients | The estimated vector of regression coefficients |
| `coef_names` | — | Names of the estimated coefficients, aligned positionally with `coefficients`. |
| `scale` | scale | The robust residual M-scale estimate using the final residuals from the converged iterated weighted least square (IRWLS) algorithm final estimate |
| `residuals` | residuals | The vector of residuals associated with the robust fit |
| `loss` | loss | Value of the objective function at the final MM-estimator |
| `converged` | converged | Logical value indicating whether IRWLS iterations for the MM-estimator have converged |
| `iter` | iter | Number of IRWLS iterations for the MM-estimator |
| `fitted_values` | fitted.values | Fitted values associated with the robust fit |
| `rweights` | rweights | Robustness weights for the MM-estimator |
| `rank` | rank | Numeric rank of the fitted linear model |
| `cov` | cov | The estimated covariance matrix of the regression estimates |
| `df_residual` | df.residual | The residual degrees of freedom |
| `degree_freedom` | degree.freedom | The residual degrees of freedom |
| `scale_s` | scale.S | Minimum robust scale associated with the preliminary highly robust but inefficient S-estimator. |
| `iters_const` | iters.const | The number of refinement iterations used to compute the estimator without covariates (to calculate the robust R^2). |
| `r_squared` | r.squared | The robust multiple correlation coefficient |
| `adj_r_squared` | adj.r.squared | The adjusted robust multiple correlation coefficient taking into account the degrees of freedom of each term |
| `formula` | — | The model formula used for the fit (echoes the input). |
| `control` | — | The control object used for the fit (echoes the input). |


> **R fields not surfaced in Python** — the R `lmrobdetMM` list also contains
> `contrasts`, `xlevels`, `call`, `model`, `x`, `y`, `terms`, `iters.py`, `assign`, `na.action`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `LmrobdetMMResult` object also provides these methods:

| Method | Description |
|---|---|
| `coef()` | Return coefficients as a named pandas Series. |
| `coef_df()` | Return ``coefficients`` as a pandas Series, indexed by coef name. |
| `drop1(scope, scale)` | Port of R's ``drop1.lmrobdetMM`` — single-term-deletion RFPE table. |
| `hatvalues()` | Port of R's ``hatvalues.lmrob`` — leverages of the fitted model. |
| `predict(newdata, se_fit)` | Port of R's ``predict.lmrobdetMM`` (dispatched via ``robustbase``). |
| `rfpe(both_vals)` | Port of R's ``lmrobdetMM.RFPE`` — robust final prediction error. |
| `summary()` | Port of R's ``summary.lmrobdetMM``. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Choice of Rho Loss Function

This is done by the user choice of family = "opt" or family = "mopt"
in the function lmrobdet.control. As of RobStatTM Versopm 1.0.7, the
opt and mopt rhos functions are calculated using polynomials, rather
than using the standard normal error function (erf) as in versions of
RobStatTM prior to 1.0.7. The numerical results one now gets with the
opt or mopt choices will differ by small amounts from those in earlier
RobStatTM versions. Users who wish to replicate results from releases
prior to 1.0.7 may do so using the family arguments family = "optV0" 
or family = "moptV0". Note that the derivative of the rho loss function,
known as the "psi" function, is not the derivative of the rho polynomial,
instead it is still the optimal psi function referred to above.

## Related Vignettes

For further details, see the Vignettes "Polynomial Opt and mOpt Rho Functions",
and "Optimal Bias Robust Regression Psi and Rho".

## Example

```python
import robstatm_py as rpm

# Load Coleman's school data — 20 obs of school outcomes vs predictors.
coleman = rpm.datasets.load("robustbase", "coleman")

# Fit a robust MM-regression.  ``Y ~ .`` means "regress Y on every
# other column".  The wrapper handles dot formulas correctly.
fit = rpm.lmrobdet_mm("Y ~ .", data=coleman)

print(fit)               # short S3-style summary
print()
print(fit.summary())     # full summary table with std errors / p-values

print(f"\nR² = {fit.r_squared:.4f}   converged after {fit.iter} IRWLS iterations")
print(f"coefficients: {dict(zip(fit.coef_names, fit.coefficients.round(3)))}")
```

<details>
<summary>Equivalent R code</summary>

```r
data(coleman, package='robustbase')
m2 <- lmrobdetMM(Y ~ ., data=coleman)
m2
summary(m2)
```
</details>


## See also

- `DCML` (R-side helper; not a separate Python wrapper)
- `MMPY` (R-side helper; not a separate Python wrapper)
- `SMPY` (R-side helper; not a separate Python wrapper)



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>, based on `lmrob` from package `robustbase`. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `lmrobdetMM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
