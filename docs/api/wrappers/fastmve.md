# `fastmve`

> **R original:** `fastmve` &nbsp;·&nbsp; **Python module:** `robstatm_py.covariance` &nbsp;·&nbsp; Minimum Volume Ellipsoid covariance estimator

This function uses a fast algorithm to compute the Minimum Volume
Ellipsoid (MVE) for multivariate location and scatter.

This function computes the Minimum Volume
Ellipsoid (MVE) for multivariate location and scatter, using a
fast algorithm related to the fast algorithm for S-regression
estimators (see ``lmrob``).

## Usage

```python
from robstatm_py import fastmve

def fastmve(X, nsamp: 'int' = 500):
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `nsamp` | int | `500` | number of random starts for the iterative algorithm, these are constructed using subsamples of the data. |


> **Note** — handled internally, not exposed in Python: `x`. These are constructed for you from the inputs above.


## Returns

A `FastMVEResult` object. Its attributes mirror the fields of the R
`fastmve` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `center` | center | a vector with the robust multivariate location estimate |
| `cov` | cov | a matrix with the robust covariance / scatter matrix estimate |
| `scale` | scale | A scalar that equals the median of the mahalanobis distances of the data to the `center`, multiplied by the determinant of the covariance matrix to the power 1/p |
| `best` | best | Indices of the observations that correspond to the MVE estimator |
| `nsamp` | nsamp | Number of random starts used for the iterative algorithm |
| `nsing` | nsing | Number of random subsamples (among the `nsamp` attempted) that failed (resulting in singular initial values) |
| `column_names` | — | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |




## Methods

The `FastMVEResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

wine = rpm.datasets.wine()

# fastmve computes the Minimum Volume Ellipsoid (MVE) estimator of location
# and scatter — a fast resampling-based robust starting point.
rpm.set_seed(11)
res = rpm.fastmve(wine)
print(res)
```

<details>
<summary>Equivalent R code</summary>

```r
data(wine)

# fastmve computes the Minimum Volume Ellipsoid (MVE) estimator of location
# and scatter — a fast resampling-based robust starting point.
set.seed(11)
res <- fastmve(as.matrix(wine))

print(round(res$center, 2))
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `fastmve`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
