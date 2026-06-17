# `rob_linear_test`

> **R original:** `lsRobTestMM` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; Test for Least Squares Bias Using Robust MM Regressions

Test for Least Squares Bias Using Robust MM Regressions

The original version of `lsRobTestMM` is the `lsRobTest`
in the package *robust*. The function `lsRobTest` had options *T1* and
*T2*. However, we only recommend *T2*, and deprecate *T1*. Accordingly we
use *T* for the former *T2*, and use *T0* for the former *T1*, and we
deprecate *T0*.

The *coefs* component of the list is a matrix whose row names are
the names of the regression predictor variables, and whose columns *LS*, 
*Robust*, *Delta*, *Std.error*, *t-stat*, *p-value* contain respectively,
the least squares and robust coefficient estimates, the differences in the
coefficient estimates, the standard errors of the differences, the resulting
t-statistic values, and the resulting z-test p-values.

The *full* component of the list is itself a list with components the full
model quadratic form chi-squared statistic value (*stat*), the degrees of 
freedom (*df*), and the full model p value (*p.value*).

The *test* component of the list is a character value indicating which of the 
tests *T* and *T0* has been computed.

The *efficiency* component of the list is *NULL* when test *T* has been used,
and is equal to the normal distribution efficiency of the *lmrobdetMM*
estimate when test *T0* has been used.

## Usage

```python
from robstatm_py import rob_linear_test

def rob_linear_test(object1: 'LmrobdetMMResult', object2: 'LmrobdetMMResult'):
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `object1` | LmrobdetMMResult | *required* |  |
| `object2` | LmrobdetMMResult | *required* |  |


> **Note** — handled internally, not exposed in Python: `object`, `test`, `...`. These are constructed for you from the inputs above.


## Returns

A `RobLinearTestResult` object. Its attributes mirror the fields of the R
`lsRobTestMM` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `test` | — | Test statistic. |
| `chisq_pvalue` | — | χ² approximation p-value. |
| `f_pvalue` | — | F approximation p-value. |
| `df` | — | (numerator, denominator) degrees of freedom. |




## Methods

The `RobLinearTestResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

df = rpm.datasets.stackloss()

# Robust analogue of the classical F-test for nested linear models:
# is the extra term `Acid.Conc.` worth keeping?
# lmrobdet_mm uses the deterministic Peña–Yohai initial estimator, so both
# fits are reproducible without set_seed.
full = rpm.lmrobdet_mm(
    "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df
)
reduced = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)

res = rpm.rob_linear_test(full, reduced)
print(res)
print(f"test statistic = {res.test:.4f}")
```

<details>
<summary>Equivalent R code</summary>

```r
args(lsRobTestMM)
```
</details>




## Credits

R implementation by Kjell Konis. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `lsRobTestMM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
