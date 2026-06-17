# `cov_rob_rocke`

> **R original:** `covRobRocke` &nbsp;·&nbsp; **Python module:** `robstatm_py.covariance` &nbsp;·&nbsp; Rocke's robust multivariate location and scatter estimator

This function computes Rocke's robust estimator for multivariate location and scatter.

This function computes Rocke's robust estimator for multivariate location and scatter.

## Usage

```python
from robstatm_py import cov_rob_rocke

def cov_rob_rocke(
                  X,
                  initial: "Literal['K', 'mve']" = 'K',
                  maxsteps: 'int' = 5,
                  propmin: 'float' = 2,
                  qs: 'float' = 2,
                  maxit: 'int' = 50,
                  tol: 'float' = 0.0001,
                  corr: 'bool' = False,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | a data matrix with observations in rows. |
| `initial` | Literal['K', 'mve'] | `"K"` | A character indicating the initial estimator. Valid options are 'K' (default) for the Pena-Prieto 'KSD' estimate, and 'mve' for the Minimum Volume Ellipsoid. |
| `maxsteps` | int | `5` | Maximum number of steps for the line search section of the algorithm. |
| `propmin` | float | `2` | Regulates the proportion of weights computed from the initial estimator that will be different from zero. The number of observations with initial non-zero weights will be at least p (the number of columns of X) times propmin. |
| `qs` | float | `2` | Tuning paramater for Rocke's loss functions. |
| `maxit` | int | `50` | Maximum number of iterations. |
| `tol` | float | `0.0001` | Tolerance to decide converngence. |
| `corr` | bool | `False` | A logical value. If `TRUE` a correlation matrix is included in the element `cor` of the returned object. Defaults to `FALSE`. |



## Returns

A `CovRobRockeResult` object. Its attributes mirror the fields of the R
`covRobRocke` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `center` | center | The location estimate. |
| `cov` | cov | The scatter matrix estimate, scaled for consistency at the normal distribution. |
| `cor` | cor | The correlation matrix estimate, if the argument `cor` equals `TRUE`. Otherwise it is set to `NULL`. |
| `dist` | dist | Robust Mahalanobis distances. |
| `wts` | wts | weights |
| `mu` | mu | The location estimate. Same as `center` above. |
| `v` | V | The scatter (or correlation) matrix estimate, scaled for consistency at the normal distribution.  Same as `cov` above. |
| `sig` | sig | sig |
| `gamma` | gamma | Final value of the constant gamma that regulates the efficiency. |
| `column_names` | — | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |
| `classical` | — | Always False. |


> **R fields not surfaced in Python** — the R `covRobRocke` list also contains
> `call`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `CovRobRockeResult` object also provides these methods:

| Method | Description |
|---|---|
| `summary()` | Port of R's ``summary.covRob`` (Rocke fit dispatches there). |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

wine = rpm.datasets.wine()

# Rocke's S-estimator of multivariate location and scatter — designed to stay
# efficient in higher dimensions where other robust estimators lose power.
rpm.set_seed(42)
fit = rpm.cov_rob_rocke(wine)

print("covariance shape :", fit.cov.shape)
print("robust center    :", fit.center.round(2))
# Mahalanobis distances flag the outlying wines.
print("largest distances:", fit.dist.round(1)[fit.dist.argsort()[-5:]])
```

<details>
<summary>Equivalent R code</summary>

```r
data(wine)

# Rocke's S-estimator of multivariate location and scatter — designed to stay
# efficient in higher dimensions where other robust estimators lose power.
set.seed(42)
fit <- covRobRocke(wine)

print(dim(fit$cov))
print(round(fit$center, 2))
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Ricardo Maronna, <rmaronna@retina.ar>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `covRobRocke`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
