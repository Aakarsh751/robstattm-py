# `lmrobdet_control`

> **R original:** `lmrobdet.control` &nbsp;·&nbsp; **Python module:** `robstattm_py.regression` &nbsp;·&nbsp; Tuning parameters for lmrobdetMM and lmrobdetDCML

This function sets tuning parameters for the MM estimator implemented in `lmrobdetMM` and
the Distance Constrained Maximum Likelihood regression estimators
computed by `lmrobdetDCML`.

The argument `family` specifies the name of the family of loss
function to be used. Current valid options are "bisquare", "opt", "mopt", 
"optV0" and "moptV0". "mopt" is a modified  version of the optimal psi 
function to make it strictly increasing close to 0, and to make the
corresponding weight function non-increasing.

## Usage

```python
from robstattm_py import lmrobdet_control

def lmrobdet_control(**kwargs: 'Any'):
```

## Returns

A `LmrobdetControl` object. Its attributes mirror the fields of the R
`lmrobdet.control` result, converted to NumPy / pandas / native Python types:

Defaults below mirror R's `lmrobdet.control` (RobStatTM 1.0.11) field-for-field.

| Attribute | R name | Default | Notes |
|---|---|---|---|
| `bb` | `bb` | `0.5` | breakdown-point parameter of the S-scale |
| `efficiency` | `efficiency` | `0.95` | target Gaussian efficiency of the MM step |
| `family` | `family` | `"mopt"` | ρ-loss family |
| `tuning_psi` | `tuning.psi` | `None` | derived from `efficiency`/`family` when `None` |
| `tuning_chi` | `tuning.chi` | `None` | derived from `bb`/`family` when `None` |
| `compute_rd` | `compute.rd` | `False` | compute robust leverage distances |
| `corr_b` | `corr.b` | `True` | finite-sample bias correction |
| `split_type` | `split.type` | `"f"` | design-split type |
| `initial` | `initial` | `"S"` | initial estimator |
| `max_it` | `max.it` | `100` | max IRWLS iterations |
| `refine_tol` | `refine.tol` | `1e-7` | refinement convergence tolerance |
| `rel_tol` | `rel.tol` | `1e-7` | relative convergence tolerance |
| `refine_s_py` | `refine.S.py` | `1e-7` | **tolerance** for refining the Peña–Yohai candidates (float, not a count) |
| `refine_py` | `refine.PY` | `10` | number of Peña–Yohai refinement steps |
| `solve_tol` | `solve.tol` | `1e-7` | linear-solve tolerance |
| `trace_lev` | `trace.lev` | `0` | verbosity |
| `psc_keep` | `psc_keep` | `0.5` | proportion of PSC candidates kept |
| `resid_keep_method` | `resid_keep_method` | `"threshold"` | residual-keep rule |
| `resid_keep_thresh` | `resid_keep_thresh` | `2.0` | threshold for `resid_keep_method="threshold"` |
| `resid_keep_prop` | `resid_keep_prop` | `0.2` | proportion for `resid_keep_method="proportion"` |
| `py_maxit` | `py_maxit` | `20` | max Peña–Yohai iterations |
| `py_eps` | `py_eps` | `1e-5` | Peña–Yohai convergence tolerance |
| `mscale_maxit` | `mscale_maxit` | `50` | max M-scale iterations |
| `mscale_tol` | `mscale_tol` | `1e-6` | M-scale convergence tolerance |
| `mscale_rho_fun` | `mscale_rho_fun` | `"bisquare"` | M-scale ρ family |





## Choice of Rho Loss Function

As of RobStatTM Versopm 1.0.7, the opt and mopt rhos functions are
calculated using polynomials, rather than using the standard normal error
function (erf) as in versions of RobStatTM prior to 1.0.7. The numerical
results one now gets with the opt or mopt choices will differ by small
amounts from those in earlier RobStatTM versions. Users who wish to replicate
results from releases prior to 1.0.7 may do so using the family arguments
family = "optV0" or family = "moptV0". Note that the derivative of the rho
loss function, known as the "psi" function, is not the derivative of the rho
polynomial,instead it is still the analytic optimal psi function whose formula
is given in the second of the Vignettes referenced just below.

## Related Vignettes

For further details, see the Vignettes "Polynomial Opt and mOpt Rho Functions",
and "Optimal Bias Robust Regression Psi and Rho".

## Example

```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()

# A control object bundles the tuning knobs for lmrobdet_mm / lmrobdet_dcml.
# Here: switch the loss family and lower the target efficiency.
ctrl = rpm.lmrobdet_control(family="bisquare", efficiency=0.85)
print(ctrl)

fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=ctrl)
print("coefficients:", fit.coefficients.round(4))
```

<details>
<summary>Equivalent R code</summary>

```r
data(mineral)

# A control object bundles the tuning knobs for lmrobdetMM / lmrobdetDCML.
# Here: switch the loss family and lower the target efficiency.
ctrl <- lmrobdet.control(family = "bisquare", efficiency = 0.85)
fit  <- lmrobdetMM(zinc ~ copper, data = mineral, control = ctrl)
coef(fit)
```
</details>


## See also

- [`m_scale`](m_scale.md), Python wrapper for R `scaleM`




## Credits

R implementation by Matias Salibian-Barrera, <matias@stat.ubc.ca>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `lmrobdet.control`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`): byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
