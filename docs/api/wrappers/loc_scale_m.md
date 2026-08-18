# `loc_scale_m`

> **R original:** `locScaleM` &nbsp;·&nbsp; **Python module:** `robstattm_py.univariate` &nbsp;·&nbsp; Robust univariate location and scale M-estimators

This function computes M-estimators for location and scale.

This function computes M-estimators for location and scale.

## Usage

```python
from robstattm_py import loc_scale_m

def loc_scale_m(
                x,
                psi: "Literal['mopt', 'bisquare', 'huber', 'opt', 'moptv0', 'optv0']" = 'mopt',
                eff: 'float' = 0.95,
                maxit: 'int' = 50,
                tol: 'float' = 0.0001,
                na_rm: 'bool' = False,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `x` | n/a | *required* | a vector of univariate observations |
| `psi` | Literal['mopt', 'bisquare', 'huber', 'opt', 'moptv0', 'optv0'] | `"mopt"` | a string indicating which score function to use. Valid options are "bisquare", "huber", "opt" and "mopt". |
| `eff` | float | `0.95` | desired asymptotic efficiency. Valid options are 0.85, 0.9 and 0.95 (default) when `psi` = "bisquare" or "huber", and 0.85, 0.9, 0.95 (default) and 0.99 when `psi` = "opt" or "mopt". |
| `maxit` | int | `50` | maximum number of iterations allowed. |
| `tol` | float | `0.0001` | tolerance to decide convergence of the iterative algorithm. |
| `na_rm` | bool | `False` | a logical value indicating whether `NA` values should be stripped before the computation proceeds. Defaults to `FALSE` |



## Returns

A `LocScaleMResult` object. Its attributes mirror the fields of the R
`locScaleM` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `mu` | mu | The location estimate |
| `std_mu` | std.mu | Estimated standard deviation of the location estimator `mu` |
| `disper` | disper | M-scale/dispersion estimate |




## Methods

The `LocScaleMResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstattm_py as rpm

# Zinc concentration in 53 mineral samples (some are gross outliers).
zinc = rpm.datasets.mineral()["zinc"].to_numpy()

# Robust M-estimators of location AND scale, in one call.
est = rpm.loc_scale_m(zinc, psi="bisquare", eff=0.95)

print(f"robust location: {est.mu:.4f}")
print(f"robust scale:    {est.disper:.4f}")
print(f"std-err of mu:   {est.std_mu:.4f}")
print()
print(f"compare classical: mean={zinc.mean():.4f}   std={zinc.std(ddof=1):.4f}")
print("(the classical mean/std are pulled by the outlying samples)")
```

<details>
<summary>Equivalent R code</summary>

```r
data(mineral)
zinc <- mineral$zinc          # zinc concentration in 53 mineral samples

# Robust M-estimators of location AND scale, in one call.
est <- locScaleM(zinc, psi = "bisquare", eff = 0.95)

cat("robust location:", round(est$mu, 4), "\n")
cat("robust scale:   ", round(est$disper, 4), "\n")
cat("std-err of mu:  ", round(est$std.mu, 4), "\n")
```
</details>



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Ricardo Maronna, <rmaronna@retina.ar>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `locScaleM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`): byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
