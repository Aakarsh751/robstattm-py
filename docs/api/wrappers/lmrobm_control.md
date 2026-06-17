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

| Attribute | R name | Description |
|---|---|---|
| `bb` | — | (Python-side convenience field) |
| `efficiency` | — | (Python-side convenience field) |
| `family` | — | (Python-side convenience field) |
| `tuning_psi` | — | (Python-side convenience field) |
| `tuning_chi` | — | (Python-side convenience field) |
| `max_it` | — | (Python-side convenience field) |
| `rel_tol` | — | (Python-side convenience field) |
| `mscale_tol` | — | (Python-side convenience field) |
| `mscale_maxit` | — | (Python-side convenience field) |
| `trace_lev` | — | (Python-side convenience field) |





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
