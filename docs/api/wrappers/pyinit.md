# `pyinit`

> **R original:** `pyinit` &nbsp;·&nbsp; **Python module:** `robstattm_py.regression` &nbsp;·&nbsp; Pena-Yohai initial estimator for robust regression

Computes the Pena-Yohai (PY) deterministic initial estimator for MM-regression. Instead of random subsampling, it builds a small set of robust candidate coefficient vectors by iteratively removing observations with high 'principal sensitivity'. RobStatTM uses these candidates as the deterministic starting points for `lmrobdetMM`. This wrapper exposes the `pyinit` routine from the companion `pyinit` package.

## Usage

```python
from robstattm_py import pyinit

def pyinit(
           X,
           y,
           intercept: 'bool' = True,
           delta: 'float' = 0.5,
           cc: 'float' = 1.5476,
           psc_keep: 'float' = 0.5,
           resid_keep_method: "Literal['threshold', 'proportion']" = 'threshold',
           resid_keep_prop: 'float' = 0.2,
           resid_keep_thresh: 'float' = 2.0,
           maxit: 'int' = 10,
           eps: 'float' = 1e-08,
           mscale_maxit: 'int' = 200,
           mscale_tol: 'float | None' = None,
           mscale_rho_fun: "Literal['bisquare', 'huber', 'gauss']" = 'bisquare',
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `y` | — | *required* | response vector of length n. |
| `intercept` | bool | `True` | whether to add an intercept column to the design matrix (default True). |
| `delta` | float | `0.5` |  |
| `cc` | float | `1.5476` |  |
| `psc_keep` | float | `0.5` | proportion of candidates to keep at each principal-sensitivity-component step. |
| `resid_keep_method` | Literal['threshold', 'proportion'] | `"threshold"` | method for keeping observations by residual size: 'threshold' or 'proportion'. |
| `resid_keep_prop` | float | `0.2` | proportion of observations to keep when `resid_keep_method='proportion'`. |
| `resid_keep_thresh` | float | `2.0` |  |
| `maxit` | int | `10` | maximum number of refinement iterations per candidate. |
| `eps` | float | `1e-08` |  |
| `mscale_maxit` | int | `200` |  |
| `mscale_tol` | float \| None | `None` |  |
| `mscale_rho_fun` | Literal['bisquare', 'huber', 'gauss'] | `"bisquare"` |  |


> **Note** — handled internally, not exposed in Python: `x`. These are constructed for you from the inputs above.


## Returns

A `PyinitResult` object. Its attributes mirror the fields of the R
`pyinit` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `coefficients` | coefficients | matrix whose columns are the candidate coefficient vectors (one robust starting point per column). |
| `objective` | objective | value of the robust objective for each candidate. |
| `best` | — | Column of `coefficients` with the smallest objective. Convenience. |




## Methods

The `PyinitResult` object also provides these methods:

| Method | Description |
|---|---|
| `coef_df()` | Return ``coefficients`` as a pandas Series, indexed by coef name. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()

# pyinit produces the deterministic Pena-Yohai starting points that
# lmrobdet_mm uses internally. Each column of `coefficients` is one robust
# candidate coefficient vector.
res = rpm.pyinit(
    X=mineral[["copper"]].to_numpy(),
    y=mineral["zinc"].to_numpy(),
)
print("candidate matrix shape (p x k):", res.coefficients.shape)
print("first candidate:", res.coefficients[:, 0].round(4))
```


## See also

- [`lmrobdet_mm`](lmrobdet_mm.md) — Python wrapper for R `lmrobdetMM`



## References

Pena, D. and Yohai, V. (1999). A fast procedure for outlier diagnostics in large regression problems. JASA 94(446), 434-445.


## Credits

R implementation by the pyinit package authors. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `pyinit`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
