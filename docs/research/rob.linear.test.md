# rob.linear.test (lsRobTestMM)

## 1. Statistical purpose
**Robust likelihood-ratio-style test** for linear hypotheses (subset of coefficients = 0, or general $H_0: C\beta = c$) within an MM-regression fit. Maronna et al. (2019, §4.7).

## 2. Mathematical background
Compares the robust deviance of the full and restricted MM-fits, scaled so that under $H_0$ the statistic has an approximate $\chi^2$ distribution (`T`) or an asymptotic correction (`T0`).

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/lsRobTestMM.R` line 40.
- Function: `lsRobTestMM(object, test = c("T", "T0"), ...)`.
- Re-fits the restricted model internally; therefore transitively depends on the same packages as `lmrobdetMM`.

## 4. Inputs / Outputs / Return structure
**Signature:** `lsRobTestMM(object, test = c("T", "T0"))`

Returns a list (S3 class `lsRobTest`) with: `full`, `reduced`, `statistic`, `df`, `p.value`, `test`.

## 5. Dependencies
- RobStatTM
- pyinit (transitively via the MM re-fit)
- robustbase

## 6. Python wrapper design

```python
def rob_linear_test(
    fit: LmrobdetMMResult,
    *,
    restricted_formula: FormulaLike | None = None,
    drop: Sequence[str] | None = None,
    test: Literal["T", "T0"] = "T",
) -> RobLinearTestResult: ...
```

Two ways to specify the null: a `restricted_formula` string, or a list of terms to drop. Mutually exclusive.

```python
@dataclass(frozen=True, slots=True)
class RobLinearTestResult:
    statistic: float
    df: int
    p_value: float          # R: p.value
    test: str
```

## 7. Validation strategy
Cases 1, 2, 7, 10. Reproduce the §4.7 textbook example. Strict-tier on `statistic` and `p_value`.
