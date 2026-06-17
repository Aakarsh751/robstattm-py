# `cov_rob`

> **R original:** `covRob` &nbsp;·&nbsp; **Python module:** `robstatm_py.covariance` &nbsp;·&nbsp; Robust multivariate location and scatter estimators

This function computes robust estimators for multivariate location and scatter.

This function computes robust estimators for multivariate location and scatter.
The default behaviour (`type = "auto"`) computes a "Rocke" estimator
(as implemented in ``covRobRocke``) if the number
of variables is greater than or equal to 10, and an MM-estimator with a
SHR rho function (as implemented in ``covRobMM``) otherwise.

## Usage

```python
from robstatm_py import cov_rob

def cov_rob(
            X,
            type: "Literal['auto', 'MM', 'Rocke']" = 'auto',
            maxit: 'int' = 50,
            tol: 'float' = 0.0001,
            corr: 'bool' = False,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | a data matrix with observations in rows. |
| `type` | Literal['auto', 'MM', 'Rocke'] | `"auto"` | a string indicating which estimator to compute. Valid options are "Rocke" for Rocke's S-estimator, "MM" for an MM-estimator with a SHR rho function, or "auto" (default) which selects "Rocke" if the number of variables is greater than or equal to 10, and "MM" otherwise. |
| `maxit` | int | `50` | Maximum number of iterations, defaults to 50. |
| `tol` | float | `0.0001` | Tolerance for convergence, defaults to 1e-4. |
| `corr` | bool | `False` | A logical value. If `TRUE` a correlation matrix is included in the element `cor` of the returned object. Defaults to `FALSE`. |



## Returns

A `CovRobResult` object. Its attributes mirror the fields of the R
`covRob` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `center` | center | The location estimate. |
| `cov` | cov | The scatter matrix estimate, scaled for consistency at the normal distribution. |
| `cor` | cor | The correlation matrix estimate, if the argument `cor` equals `TRUE`. Otherwise it is set to `NULL`. |
| `dist` | dist | Robust Mahalanobis distances |
| `wts` | wts | weights |
| `mu` | mu | The location estimate. Same as `center` above. |
| `v` | V | The scatter matrix estimate, scaled for consistency at the normal distribution. Same as `cov` above. |
| `estimator_type` | — | (Python-side convenience field) |
| `column_names` | — | (Python-side convenience field) |


> **R fields not surfaced in Python** — the R `covRob` list also contains
> `call`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `CovRobResult` object also provides these methods:

| Method | Description |
|---|---|
| `summary()` | Port of R's ``summary.covRob``. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

wine = rpm.datasets.wine()       # 59 wines, 13 chemical measurements

# cov_rob is the convenient entry point: it auto-selects a robust covariance
# estimator (MM for low dimension, Rocke for high) based on the data shape.
rpm.set_seed(42)
fit = rpm.cov_rob(wine)

print("estimator chosen :", fit.estimator_type)
print("covariance shape :", fit.cov.shape)
print("robust center    :", fit.center.round(2))
```

<details>
<summary>Equivalent R code</summary>

```r
data(bus)
X0 <- as.matrix(bus)
X1 <- X0[,-9]
tmp <- covRob(X1)
round(tmp$cov[1:10, 1:10], 3)
tmp$mu
```
</details>


## See also

- [`cov_rob_rocke`](cov_rob_rocke.md) — Python wrapper for R `covRobRocke`
- [`cov_rob_mm`](cov_rob_mm.md) — Python wrapper for R `covRobMM`



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Ricardo Maronna, <rmaronna@retina.ar>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `covRob`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
