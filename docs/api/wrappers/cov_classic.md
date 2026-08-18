# `cov_classic`

> **R original:** `covClassic` &nbsp;·&nbsp; **Python module:** `robstattm_py.covariance` &nbsp;·&nbsp; Classical Covariance Estimation

Compute an estimate of the covariance/correlation matrix and location
vector using classical methods.

Its main intention is to return an object compatible to that
produced by ``covRob``, but fit using classical methods.

## Usage

```python
from robstattm_py import cov_classic

def cov_classic(
                X,
                corr: 'bool' = False,
                center: 'bool' = True,
                distance: 'bool' = True,
                na_action: 'str | None' = None,
                unbiased: 'bool' = True,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | n/a | *required* | Design matrix of predictors with shape `(n, p)`, the array-input alternative to the `formula` + `data` form. |
| `corr` | bool | `False` | a logical flag.  If `corr = TRUE` then the estimated correlation matrix is computed. |
| `center` | bool | `True` | a logical flag or a numeric vector of length `p` (where `p` is the number of columns of `x`) specifying the center.  If `center = TRUE` then the center is estimated.  Otherwise the center is taken to be 0. |
| `distance` | bool | `True` | a logical flag.  If `distance = TRUE` the Mahalanobis distances are computed. |
| `na_action` | str \| None | `None` | a function to filter missing data.  The default `na.fail` produces an error if missing values are present.  An alternative is `na.omit` which deletes observations that contain one or more missing values. |
| `unbiased` | bool | `True` | a logical flag. If `TRUE` the unbiased estimator is returned (computed with denominator equal to `n-1`), else the MLE (computed with denominator equal to `n`) is returned. |


> **Note:** handled internally, not exposed in Python: `data`. These are constructed for you from the inputs above.


## Returns

A `CovClassicResult` object. Its attributes mirror the fields of the R
`covClassic` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `center` | center | a numeric vector containing the estimate of the location vector. |
| `cov` | cov | a numeric matrix containing the estimate of the covariance matrix. |
| `cor` | cor | a numeric matrix containing the estimate of the correlation matrix if the argument `corr = TRUE`. Otherwise it is set to `NULL`. |
| `dist` | dist | a numeric vector containing the squared Mahalanobis distances. Only present if `distance = TRUE` in the `call`. |
| `column_names` | n/a | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |
| `classical` | n/a | Always True; lets generic helpers tell us apart from robust results. |


> **R fields not surfaced in Python.** The R `covClassic` list also contains
> `call`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `CovClassicResult` object also provides these methods:

| Method | Description |
|---|---|
| `summary()` | Port of R's ``summary.covClassic``. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstattm_py as rpm

wine = rpm.datasets.wine()

# The classical (non-robust) mean and covariance  -  handy as a baseline to
# compare against the robust estimators (cov_rob_mm, cov_rob_rocke).
fit = rpm.cov_classic(wine)

print("covariance shape :", fit.cov.shape)
print(fit.summary())             # eigenvalues of the covariance matrix
```

<details>
<summary>Equivalent R code</summary>

```r
data(wine)
round( covClassic(wine)$cov, 2)
```
</details>





---

> **Bit-for-bit equivalence.** This wrapper calls the original R `covClassic`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`): byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
