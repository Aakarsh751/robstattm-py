# `lmrobm_control`

> **R original:** `lmrobM.control` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; Tuning parameters for lmrobM

This function sets tuning parameters for the M estimators of regression implemented
in ``lmrobM``.

## Usage

```python
from robstatm_py import lmrobm_control

def lmrobm_control(**kwargs: 'Any'):
```

## Returns

A `LmrobMControl` object. Its attributes mirror the fields of the R
`lmrobM.control` result, converted to NumPy / pandas / native Python types:

Defaults below mirror R's `lmrobM.control` (RobStatTM 1.0.11) field-for-field.
Note `lmrobM` uses a smaller control surface than `lmrobdet_control` — it does
not run the deterministic-initial / Peña–Yohai / pyinit cascade.

| Attribute | R name | Default | Notes |
|---|---|---|---|
| `bb` | `bb` | `0.5` | breakdown-point parameter of the M-scale |
| `efficiency` | `efficiency` | `0.99` | target Gaussian efficiency of the M step |
| `family` | `family` | `"opt"` | ρ-loss family |
| `tuning_psi` | `tuning.psi` | `None` | derived from `efficiency`/`family` when `None` |
| `tuning_chi` | `tuning.chi` | `None` | derived from `bb`/`family` when `None` |
| `max_it` | `max.it` | `100` | max IRWLS iterations |
| `rel_tol` | `rel.tol` | `1e-7` | relative convergence tolerance |
| `mscale_tol` | `mscale_tol` | `1e-6` | M-scale convergence tolerance |
| `mscale_maxit` | `mscale_maxit` | `50` | max M-scale iterations |
| `trace_lev` | `trace.lev` | `0` | verbosity |





## Example

```python
import robstatm_py as rpm

mineral = rpm.datasets.mineral()

# Control object for the M-estimator lmrob_m: choose the loss family,
# efficiency, and the breakdown tuning constant `bb`.
ctrl = rpm.lmrobm_control(efficiency=0.85, family="bisquare", bb=0.5)
print(ctrl)

fit = rpm.lmrob_m("zinc ~ copper", data=mineral, control=ctrl)
print("coefficients:", fit.coefficients.round(4))
```

<details>
<summary>Equivalent R code</summary>

```r
data(coleman, package='robustbase')
m2 <- lmrobM(Y ~ ., data=coleman, control=lmrobM.control())
m2
summary(m2)
```
</details>




## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `lmrobM.control`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
