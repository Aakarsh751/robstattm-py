# `cov_rob_mm`

> **R original:** `covRobMM` &nbsp;·&nbsp; **Python module:** `robstatm_py.covariance` &nbsp;·&nbsp; MM robust multivariate location and scatter estimator

This function computes an MM robust estimator for multivariate location and scatter with the "SHR" loss function.

This function computes an MM robust estimator for multivariate location and scatter with the "SHR" loss function.

## Usage

```python
from robstatm_py import cov_rob_mm

def cov_rob_mm(X, maxit: 'int' = 50, tolpar: 'float' = 0.0001, corr: 'bool' = False):
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | a data matrix with observations in rows. |
| `maxit` | int | `50` | Maximum number of iterations. |
| `tolpar` | float | `0.0001` | Tolerance to decide converngence. |
| `corr` | bool | `False` | A logical value. If `TRUE` a correlation matrix is included in the element `cor` of the returned object. Defaults to `FALSE`. |



## Returns

A `CovRobMMResult` object. Its attributes mirror the fields of the R
`covRobMM` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `center` | center | The location estimate. |
| `cov` | cov | The scatter matrix estimate, scaled for consistency at the normal distribution. Same as `V` above. |
| `cor` | cor | The correlation matrix estimate, if the argument `cor` equals `TRUE`. Otherwise it is set to `NULL`. |
| `dist` | dist | Robust Mahalanobis distances |
| `wts` | wts | weights |
| `mu` | mu | The location estimate. Same as `center` above. |
| `v` | V | The scatter or correlation matrix estimate, scaled for consistency at the normal distribution |
| `column_names` | — | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |
| `classical` | — | Always False; helpers use this to distinguish from CovClassicResult. |


> **R fields not surfaced in Python** — the R `covRobMM` list also contains
> `call`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `CovRobMMResult` object also provides these methods:

| Method | Description |
|---|---|
| `summary()` | Port of R's ``summary.covRob`` (MM fit dispatches there). |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import numpy as np
import robstatm_py as rpm

# Italian wine cultivar — 59 obs of 13 chemical measurements.
wine = rpm.datasets.wine()
X = wine.to_numpy()

# Robust MM-covariance estimator.
fit = rpm.cov_rob_mm(X)

print(f"robust center (first 5 vars):  {fit.center[:5].round(3)}")
print(f"robust covariance diag:        {np.diag(fit.cov)[:5].round(2)}")
print(f"# obs flagged as outliers:     {int((fit.dist > np.quantile(fit.dist, 0.95)).sum())}")
```

<details>
<summary>Equivalent R code</summary>

```r
data(bus)
X0 <- as.matrix(bus)
X1 <- X0[,-9]
tmp <- covRobMM(X1)
round(tmp$cov[1:10, 1:10], 3)
tmp$mu
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Ricardo Maronna, <rmaronna@retina.ar>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `covRobMM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
