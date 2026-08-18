# `m_scale`

> **R original:** `scaleM` &nbsp;·&nbsp; **Python module:** `robstattm_py.univariate` &nbsp;·&nbsp; M-scale estimator

This function computes an M-scale, which is a robust
scale (spread) estimator.
M-estimators of scale are a robust alternative to
the sample standard deviation. Given a vector of
residuals `r`, the M-scale estimator `s`
solves the non-linear equation `mean(rho(r/s, cc))=delta`,
where `delta` determines the breakdown point of the 
estimator, and `cc` is a tuning parameter 
calculated to obtain consistency under a Gaussian model. 
The breakdown point of the estimator is `min(delta, 1-delta)`,
so the optimal choice for `delta` is 0.5. To obtain a
consistent estimator the constant
`cc` is chosen such that E(rho(Z, cc)) = delta, where
Z is a standard normal random variable.

The iterative algorithm starts from the scaled median of
the absolute values of the input vector, and then
cycles through the equation \code{s_{k+1}^2 = s_k^2 * mean(rho(r/s_k, cc)) / delta}.

## Usage

```python
from robstattm_py import m_scale

def m_scale(
            u,
            delta: 'float' = 0.5,
            family: "Literal['bisquare', 'huber', 'mopt', 'opt', 'moptv0', 'optv0']" = 'bisquare',
            max_it: 'int' = 100,
            tol: 'float' = 1e-06,
            tuning_chi: 'float | None' = None,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `u` | n/a | *required* | vector of residuals |
| `delta` | float | `0.5` | the right hand side of the M-scale equation |
| `family` | Literal['bisquare', 'huber', 'mopt', 'opt', 'moptv0', 'optv0'] | `"bisquare"` | string specifying the name of the family of loss function to be used (current valid options are "bisquare", "opt" and "mopt"). |
| `max_it` | int | `100` | maximum number of iterations allowed |
| `tol` | float | `1e-06` | relative tolerance for convergence |
| `tuning_chi` | float \| None | `None` | the tuning object as returned by ``lmrobdet.control``, ``bisquare``, ``mopt``, or ``opt``. It defaults to the value that results in a consistent scale estimator for the specified `family`  of loss functions and breakdown point as set by `delta`. |


> **Note:** handled internally, not exposed in Python: `tolerancezero`. These are constructed for you from the inputs above.


## Returns

Returns `float`.



## Example

```python
import robstattm_py as rpm

# Concentration of zinc in 53 mineral samples (some are gross outliers).
zinc = rpm.datasets.mineral()["zinc"].to_numpy()

# The M-scale is a robust measure of spread. Unlike the standard deviation,
# a handful of outliers barely move it.
robust = rpm.m_scale(zinc)
classical = zinc.std(ddof=1)

print(f"robust M-scale     : {robust:.4f}")
print(f"classical std dev  : {classical:.4f}")
print(f"the SD is inflated by the outliers ({classical / robust:.1f}x larger)")
```

<details>
<summary>Equivalent R code</summary>

```r
data(mineral)
zinc <- mineral$zinc           # zinc concentration in 53 mineral samples

# The M-scale is a robust measure of spread; a handful of outliers barely move
# it, unlike the classical standard deviation.
robust    <- scaleM(zinc)
classical <- sd(zinc)

cat("robust M-scale   :", round(robust, 4), "\n")
cat("classical std dev:", round(classical, 4), "\n")
```
</details>




## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `scaleM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`): byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
