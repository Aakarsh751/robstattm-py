# `wml_logreg`

> **R original:** `logregWML` &nbsp;·&nbsp; **Python module:** `robstatm_py.glm` &nbsp;·&nbsp; Weighted likelihood estimator for the logistic model

This function computes a weighted likelihood estimator for the logistic model, where
the weights penalize high leverage observations. In this version the weights are zero or one.

## Usage

```python
from robstatm_py import wml_logreg

def wml_logreg(X, y, intercept: 'bool' = True):
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `y` | — | *required* | response vector |
| `intercept` | bool | `True` | 1 or 0 indicating if an intercept is included or or not |


> **Note** — handled internally, not exposed in Python: `x0`. These are constructed for you from the inputs above.


## Returns

A `LogregResult` object. Its attributes mirror the fields of the R
`logregWML` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `coefficients` | coefficients | vector of regression coefficients |
| `standard_deviation` | standard.deviation | standard deviations of the regression coefficient estimators |
| `fitted_values` | fitted.values | vector with the probabilities of success |
| `residual_deviances` | residual.deviances | residual deviances |
| `method` | — | Which estimator produced this (e.g. `"BYlogreg"`). |
| `objective` | objective | value of the objective function at the minimum |
| `converged` | — | Convergence flag. `None` for `WMLlogreg`. |
| `xweights` | xweights | vector of zeros and ones used to compute the weighted maimum likelihood estimator |
| `cov` | cov | covariance matrix of the regression estimates |




## Methods

The `LogregResult` object also provides these methods:

| Method | Description |
|---|---|
| `coef_df()` | Return ``coefficients`` as a pandas Series, indexed by coef name. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

# Skin dataset: 39 obs, 3 cols (3rd col is the binary vasoconst response).
skin = rpm.datasets.load("RobStatTM", "skin")
X = skin.iloc[:, :2].to_numpy()
y = skin["vasoconst"].to_numpy().astype(float)

# Weighted maximum-likelihood logistic regression — a robust ML variant that
# also reports a coefficient covariance matrix.
fit = rpm.wml_logreg(X, y, intercept=True)
print("coefficients      :", fit.coefficients.round(4))
print("standard deviation:", fit.standard_deviation.round(4))
```

<details>
<summary>Equivalent R code</summary>

```r
data(skin)
Xskin <- as.matrix( skin[, 1:2] )
yskin <- skin$vasoconst
skinWML <- logregWML(Xskin, yskin, intercept=1)
skinWML$coeff
skinWML$standard.deviation
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Victor Yohai. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `logregWML`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
