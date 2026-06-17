# `by_logreg`

> **R original:** `logregBY` &nbsp;·&nbsp; **Python module:** `robstatm_py.glm` &nbsp;·&nbsp; Bianco and Yohai estimator for logistic regression

This function computes the M-estimator proposed by Bianco and Yohai for
logistic regression. By default, an intercept term is included and p
parameters are estimated. Modified by Yohai (2018) to take as initial estimator
a weighted ML estimator with weights derived from the MCD estimator.
For more details we refer to Croux, C., and Haesbroeck, G. (2002),
"Implementing the Bianco and Yohai estimator for Logistic Regression"

## Usage

```python
from robstatm_py import by_logreg

def by_logreg(
              X,
              y,
              intercept: 'bool' = True,
              const: 'float' = 0.5,
              kmax: 'int' = 1000,
              maxhalf: 'int' = 10,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `y` | — | *required* | vector of binomial responses (0 or 1); |
| `intercept` | bool | `True` | 1 or 0 indicating if an intercept is included or or not |
| `const` | float | `0.5` | tuning constant used in the computation of the estimator (default=0.5); |
| `kmax` | int | `1000` | maximum number of iterations before convergence (default=1000); |
| `maxhalf` | int | `10` | max number of step-halving (default=10). |


> **Note** — handled internally, not exposed in Python: `x0`. These are constructed for you from the inputs above.


## Returns

A `LogregResult` object. Its attributes mirror the fields of the R
`logregBY` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `coefficients` | coefficients | estimates for the regression coefficients |
| `standard_deviation` | standard.deviation | standard deviations of the coefficients |
| `fitted_values` | fitted.values | fitted values |
| `residual_deviances` | residual.deviances | residual deviances |
| `method` | — | Which estimator produced this (e.g. `"BYlogreg"`). |
| `objective` | objective | value of the objective function at the minimum |
| `converged` | — | Convergence flag. `None` for `WMLlogreg`. |
| `xweights` | — | Subsample weights used by WML. `None` for BY/WBY. |
| `cov` | — | Coefficient covariance matrix returned by WML. `None` for BY/WBY. |


> **R fields not surfaced in Python** — the R `logregBY` list also contains
> `components`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `LogregResult` object also provides these methods:

| Method | Description |
|---|---|
| `coef_df()` | Return ``coefficients`` as a pandas Series, indexed by coef name. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import numpy as np
import robstatm_py as rpm

# Skin dataset: 39 obs, 3 cols (3rd col is the binary vasoconst response).
skin = rpm.datasets.load("RobStatTM", "skin")

X = skin.iloc[:, :2].to_numpy()
y = skin["vasoconst"].to_numpy().astype(float)

# Bianco-Yohai robust logistic regression.
fit = rpm.by_logreg(X, y, intercept=True)

print(f"coefficients:       {fit.coefficients.round(4)}")
print(f"standard deviation: {fit.standard_deviation.round(4)}")
print(f"converged:          {fit.converged}")
print(f"method:             {fit.method}")
```

<details>
<summary>Equivalent R code</summary>

```r
data(skin)
Xskin <- as.matrix( skin[, 1:2] )
yskin <- skin$vasoconst
skinBY <- logregBY(Xskin, yskin, intercept=1)
skinBY$coeff
skinBY$standard.deviation
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Christophe Croux, Gentiane Haesbroeck, Victor Yohai. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `logregBY`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
