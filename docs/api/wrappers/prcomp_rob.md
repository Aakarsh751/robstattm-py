# `prcomp_rob`

> **R original:** `prcompRob` &nbsp;·&nbsp; **Python module:** `robstatm_py.pca` &nbsp;·&nbsp; Robust Principal Components Cont'd

This function uses the pcaRobS function to compute all principal components while
behaving similarly to the prcomp function

## Usage

```python
from robstatm_py import prcomp_rob

def prcomp_rob(
               X,
               rank: 'int | None' = None,
               delta_scale: 'float' = 0.5,
               max_iter: 'int' = 100,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `X` | — | *required* | Design matrix of predictors with shape `(n, p)` — the array-input alternative to the `formula` + `data` form. |
| `rank` | int \| None | `None` |  |
| `delta_scale` | float | `0.5` | "delta" parametor of the scale M-estimator (default = 0.5) |
| `max_iter` | int | `100` | maximum number of iterations (default = 100) |


> **Note** — handled internally, not exposed in Python: `x`, `rank.`. These are constructed for you from the inputs above.


## Returns

A `PrcompRobResult` object. Its attributes mirror the fields of the R
`prcompRob` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `sdev` | sdev | the standard deviation of the principal components |
| `rotation` | rotation | matrix containing the factor loadings |
| `center` | center | the centering used |
| `scores` | — | Component scores (R: `x` — renamed for clarity). |
| `column_names` | — | Names of the input variables (columns of the input data), aligned with the rows/columns of the estimates. |
| `component_names` | — | Names of the principal components (`PC1`, `PC2`, …). |


> **R fields not surfaced in Python** — the R `prcompRob` list also contains
> `x`.
> These echo the inputs or are R-internal scaffolding; reach them via
> `result._r_fit` for an `rpy2` round-trip if you need them.



## Methods

The `PrcompRobResult` object also provides these methods:

| Method | Description |
|---|---|
| `summary()` | Port of R's ``summary.prcompRob``. |
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

# Bus silhouettes — 218 obs, 18 image-shape features.
bus = rpm.datasets.bus()

# Robust principal-components decomposition.
pc = rpm.prcomp_rob(bus.to_numpy())

print(f"top-5 robust std-devs:  {pc.sdev[:5].round(3)}")
print(f"variance explained by PC1-PC3: "
      f"{(pc.sdev[:3] ** 2 / (pc.sdev ** 2).sum() * 100).round(1)} %")
print(f"rotation shape: {pc.rotation.shape}   scores shape: {pc.scores.shape}")
```

<details>
<summary>Equivalent R code</summary>

```r
data(bus)                    # 218 obs, 18 image-shape features
X <- as.matrix(bus)

# Robust principal-components decomposition.
pc <- prcompRob(X)

print(round(pc$sdev[1:5], 3))
```
</details>




## Credits

R implementation by Gregory Brownson, <gregory.brownson@gmail.com>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `prcompRob`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
