# `refine_sm`

> **R original:** `refine.sm` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; IRWLS iterations for S- or M-estimators

This function performs iterative improvements for S- or
M-estimators.

This function performs iterative improvements for S- or
M-estimators. Both iterations are formally the same, the
only difference is that for M-iterations the residual
scale estimate remains fixed, while for S-iterations
it is updated at each step. In this case, we follow
the Fast-S algorithm of Salibian-Barrera and Yohai
an use one step updates for the M-scale, as opposed
to a full computation. This as internal function.

## Usage

```python
from robstatm_py import refine_sm

def refine_sm(
              X: 'np.ndarray',
              y: 'np.ndarray',
              initial_beta: 'Sequence[float] | np.ndarray',
              initial_scale: 'float',
              b: 'float',
              cc: 'float | Sequence[float] | np.ndarray',
              family: "Literal['bisquare', 'opt', 'mopt', 'moptv0', 'optv0', 'huber']",
              k: 'int' = 50,
              conv: 'int' = 1,
              step: "Literal['M', 'S']" = 'M',
              tol: 'float' = 1e-07,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | ndarray | *required* | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `y` | ndarray | *required* | vector of responses |
| `initial_beta` | Sequence[float] \| ndarray | *required* | vector of initial regression estimates |
| `initial_scale` | float | *required* | initial residual scale estimate. If missing the (scaled) median of the absolute residuals is used. |
| `b` | float | *required* | tuning constant for the M-scale estimator, used if iterations are for an S-estimator. |
| `cc` | float \| Sequence[float] \| ndarray | *required* | tuning constant for the rho function. |
| `family` | Literal['bisquare', 'opt', 'mopt', 'moptv0', 'optv0', 'huber'] | *required* | string specifying the name of the family of loss function to be used (current valid options are "bisquare", "opt" and "mopt") |
| `k` | int | `50` | maximum number of refining steps to be performed |
| `conv` | int | `1` | an integer indicating whether to check for convergence (1) at each step, or to force running k steps (0) |
| `step` | Literal['M', 'S'] | `"M"` | a string indicating whether the iterations are to compute an S-estimator ('S') or an M-estimator ('M') |
| `tol` | float | `1e-07` | tolerance to detect convergence (relative difference of consecutive vectors of parameters) |


> **Note** — handled internally, not exposed in Python: `x`. These are constructed for you from the inputs above.


## Returns

A `RefineSMResult` object. Its attributes mirror the fields of the R
`refine.sm` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `beta` | — | Refined regression coefficients (R: `beta.rw`). |
| `scale` | — | Refined scale estimate (R: `scale.rw`). |
| `converged` | converged | A logical value indicating whether the algorithm converged |
| `iterations` | — | Number of iterations actually used. |


> **R fields not surfaced in Python** — the R `refine.sm` list also contains
> `beta.rw`, `scale.rw`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `RefineSMResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import numpy as np

import robstatm_py as rpm

# Build a tiny linear dataset: y = 1 + 2*x + noise.
rng = np.random.default_rng(0)
x = rng.standard_normal(50)
X = np.column_stack([np.ones(50), x])
y = X @ np.array([1.0, 2.0]) + rng.standard_normal(50)

# refine_sm runs refinement (reweighting) iterations of an S-estimator,
# starting from an initial beta and scale.
res = rpm.refine_sm(
    X, y,
    initial_beta=[0.9, 1.9], initial_scale=0.5,
    b=0.5, cc=1.54764, family="bisquare", tol=1e-7,
)
print("refined beta :", np.round(res.beta, 4))
print("refined scale:", round(res.scale, 4))
print("converged    :", res.converged, "in", res.iterations, "iterations")
```




## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>.. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `refine.sm`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
