# step.lmrobdet

## 1. Statistical purpose
Robust **stepwise model selection** for `lmrobdetMM` fits using the **Robust Final Prediction Error (RFPE)** criterion. Maronna et al. (2019, §5.6).

## 2. Mathematical background
Analog of `step()` for classical `lm`: at each step add or remove a term that minimizes RFPE — a robust analogue of AIC that down-weights outliers in the prediction-error component.

## 3. R implementation
- Step function defined in `lmrobdet.R`; RFPE computation in `RFPE.R`.
- Returns the selected `lmrobdetMM`-class object plus a `step.anova` history.

## 4. Inputs / Outputs / Return structure
**Signature:** `step.lmrobdet(object, scope, direction = c("both","backward","forward"), trace = 1, steps = 1000, k = 2)`

Return: an `lmrobdetMM` object (with `anova` attribute holding the search trace).

## 5. Dependencies
- RobStatTM
- pyinit (transitively at each re-fit)
- robustbase

## 6. Python wrapper design

```python
def step_lmrobdet(
    fit: LmrobdetMMResult,
    *,
    scope: FormulaLike | dict | None = None,
    direction: Literal["both","backward","forward"] = "both",
    trace: int = 1,
    steps: int = 1000,
    k: float = 2.0,
) -> StepLmrobdetResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class StepLmrobdetResult:
    fit: LmrobdetMMResult
    anova: pd.DataFrame   # step-by-step search trace
```

**Edge cases:** empty scope (no candidate terms); convergence failure inside a step.

## 7. Validation strategy
Cases 1, 2, 7, 10. Reproduce a textbook stepwise example (e.g., `mineral.R`). Compare the selected formula and the `anova` table row-by-row.
