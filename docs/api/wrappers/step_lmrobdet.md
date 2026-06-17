# `step_lmrobdet`

> **R original:** `step.lmrobdetMM` &nbsp;·&nbsp; **Python module:** `robstatm_py.regression` &nbsp;·&nbsp; Robust stepwise using RFPE

This function performs stepwise model selection on a robustly fitted
linear model using the RFPE
criterion and the robust regression estimators computed with
``lmrobdetMM``. Only backwards stepwise is currently implemented.

Presently only backward stepwise selection is supported. During each step the 
Robust Final Prediction Error (as computed by the function `lmrobdetMM.RFPE`) is 
calculated for the current model and for each sub-model achievable by deleting a 
single term. If the argument `whole.path` is `FALSE`, the function steps 
to the sub-model with the lowest 
Robust Final Prediction Error or, if the current model has the lowest Robust Final 
Prediction Error, terminates. If the argument `whole.path` is `TRUE`, the 
function steps through all smaller submodels removing, at each step, the variable 
that most reduces the Robust Final Prediction Error. The scale estimate from `object` 
is used to compute the Robust Final Prediction Error throughout the procedure.

## Usage

```python
from robstatm_py import step_lmrobdet

def step_lmrobdet(
                  fit: 'LmrobdetMMResult',
                  direction: "Literal['backward']" = 'backward',
                  trace: 'bool' = False,
                  steps: 'int' = 1000,
)
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fit` | LmrobdetMMResult | *required* |  |
| `direction` | Literal['backward'] | `"backward"` | the direction of stepwise search. Currenly only `backward` stepwise  searches are implemented. |
| `trace` | bool | `False` | logical. If `TRUE` information about each step is printed on the screen. |
| `steps` | int | `1000` | maximum number of steps to be performed. Defaults to 1000, which should mean as many as needed. |


> **Note** — handled internally, not exposed in Python: `object`, `scope`, `keep`, `whole.path`. These are constructed for you from the inputs above.


## Returns

A `StepResult` object. Its attributes mirror the fields of the R
`step.lmrobdetMM` result, converted to NumPy / pandas / native Python types:

| Attribute | R name | Description |
|---|---|---|
| `final_formula` | — | Formula of the selected model. |
| `anova_rfpe` | — | RFPE trace across steps (column of the R `anova` table). |
| `coefficients` | — | Coefficients of the selected fit. |
| `coef_names` | — | Names of the estimated coefficients, aligned positionally with `coefficients`. |
| `scale` | — | Robust scale of the selected fit. |




## Methods

The `StepResult` object also provides these methods:

| Method | Description |
|---|---|
| `to_dict()` | Return a plain-Python ``dict`` view of ``self``. |
| `to_r()` | Return the underlying rpy2 R object. |



## Example

```python
import robstatm_py as rpm

df = rpm.datasets.stackloss()

# Fit the full model, then let step_lmrobdet drop terms to minimise the
# robust final prediction error (RFPE) — robust stepwise model selection.
rpm.set_seed(42)
full = rpm.lmrobdet_mm(
    "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df
)
step = rpm.step_lmrobdet(full)

print("selected coefficients:", step.coefficients.round(4))
print("RFPE at each step     :", step.anova_rfpe.round(3))
```

<details>
<summary>Equivalent R code</summary>

```r
cont <- lmrobdet.control(bb = 0.5, efficiency = 0.85, family = "bisquare")
set.seed(300)
X <- matrix(rnorm(50*6), 50, 6)
beta <- c(1,1,1,0,0,0)
y <- as.vector(X \%*\% beta) + 1 + rnorm(50)
y[1:6] <- seq(30, 55, 5)
for (i in 1:6) X[i,] <- c(X[i,1:3],i/2,i/2,i/2)
Z <- cbind(y,X)
Z <- as.data.frame(Z)
obj <- lmrobdetMM(y ~ ., data=Z, control=cont)
out <- step.lmrobdetMM(obj)
```
</details>


## See also

- `DCML` (R-side helper; not a separate Python wrapper)
- `MMPY` (R-side helper; not a separate Python wrapper)
- `SMPY` (R-side helper; not a separate Python wrapper)



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Victor Yohai, <victoryohai@gmail.com>, Matias Salibian-Barrera, <matias@stat.ubc.ca>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `step.lmrobdetMM`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
