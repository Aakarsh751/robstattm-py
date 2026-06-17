# `kurt_sd_new`

> **R original:** `initPP` &nbsp;·&nbsp; **Python module:** `robstatm_py.covariance` &nbsp;·&nbsp; Robust multivariate location and scatter estimators

This function computes robust multivariate location and scatter
estimators using both random and deterministic starting points.

This function computes robust multivariate location and scatter
using both Pen~a-Prieto and random candidates.

## Usage

```python
from robstatm_py import kurt_sd_new

def kurt_sd_new(X, muldirand: 'int' = 20, muldifix: 'int' = 10, dirmin: 'int' = 1000):
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | a data matrix with observations in rows. |
| `muldirand` | int | `20` | used to determine the number of random directions (candidates), which is `max(p*muldirand, dirmin)`, where `p` is the number of columns in `X`. |
| `muldifix` | int | `10` | used to determine the number of random directions (candidates), which is `min(n, 2*muldifix*p)`. |
| `dirmin` | int | `1000` | minimum number of random directions |



## Returns

A `KurtSDResult` object. Its attributes mirror the fields of the R
`initPP` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `idx` | idx | A zero/one vector with ones in the positions of the suspected outliers |
| `disma` | disma | Robust squared Mahalanobis distances |
| `center` | center | Robust mean estimate |
| `cova` | cova | Robust covariance matrix estimate |
| `t` | t | Outlyingness of data points |
| `column_names` | — | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |




## Methods

The `KurtSDResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

wine = rpm.datasets.wine()

# KurtSDNew computes the kurtosis-based projection directions used internally
# to initialise robust covariance and PCA estimators.
rpm.set_seed(42)
res = rpm.kurt_sd_new(wine)
print(res)
```

<details>
<summary>Equivalent R code</summary>

```r
data(bus)
X0 <- as.matrix(bus)
X1 <- X0[,-9]
tmp <- initPP(X1)
round(tmp$cov[1:10, 1:10], 3)
tmp$center
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Ricardo Maronna, <rmaronna@retina.ar>, based on original code
by D. Pen~a and J. Prieto. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `initPP`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
