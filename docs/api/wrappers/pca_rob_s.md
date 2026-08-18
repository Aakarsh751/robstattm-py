# `pca_rob_s`

> **R original:** `pcaRobS` &nbsp;·&nbsp; **Python module:** `robstattm_py.pca` &nbsp;·&nbsp; Robust principal components

This function computes robust principal components based on the minimization of
the "residual" M-scale.

## Usage

```python
from robstattm_py import pca_rob_s

def pca_rob_s(
              X,
              ncomp: 'int | None' = None,
              desprop: 'float' = 0.9,
              deltasca: 'float' = 0.5,
              maxit: 'int' = 100,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | n/a | *required* | a data matrix with observations in rows. |
| `ncomp` | int \| None | `None` | desired (maximum) number of components |
| `desprop` | float | `0.9` | desired (minimum) proportion of explained variability (default = 0.9) |
| `deltasca` | float | `0.5` | "delta" parameter of the scale M-estimator (default=0.5) |
| `maxit` | int | `100` | maximum number of iterations (default= 100) |



## Returns

A `PcaRobSResult` object. Its attributes mirror the fields of the R
`pcaRobS` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `eigvec` | eigvec | Eigenvectors, in a `p x q` matrix |
| `fit` | fit | an `n x p` matrix with the rank-q approximation to `X` |
| `repre` | repre | An `n x q` matrix with representation of data in R^q (scores) |
| `propex` | propex | The actual proportion of unexplained variability |
| `prop_spc` | n/a | Per-direction proportions of robust scale (R: `propSPC`). |
| `mu` | n/a | Robust center. |
| `q` | q | The actual number of principal components |
| `column_names` | n/a | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |


> **R fields not surfaced in Python.** The R `pcaRobS` list also contains
> `propSPC`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `PcaRobSResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstattm_py as rpm

bus = rpm.datasets.bus()         # 218 buses, 18 shape features

# Robust principal components via spherical/S-estimation  -  resistant to the
# outlying vehicles that would distort a classical PCA.
rpm.set_seed(42)
res = rpm.pca_rob_s(bus, ncomp=3)   # extract the first 3 robust components
print(res)
```

<details>
<summary>Equivalent R code</summary>

```r
data(bus)
X0 <- as.matrix(bus)
X1 <- X0[,-9]
ss <- apply(X1, 2, mad)
mu <- apply(X1, 2, median)
X <- scale(X1, center=mu, scale=ss)
q <- 3  #compute three components
rr <- pcaRobS(X, q, 0.99)
round(rr$eigvec, 3)
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Ricardo Maronna, <rmaronna@retina.ar>, based on original code
by D. Pen~a and J. Prieto. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `pcaRobS`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`): byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
