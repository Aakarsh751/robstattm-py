# locScaleM (alias MLocDis)

## 1. Statistical purpose
Joint M-estimation of **location** and **scale** for a univariate sample. Robust to point outliers and asymmetric contamination. The recommended univariate building block in Maronna et al. (2019, §2.3 and §2.7).

## 2. Mathematical background
For a sample $x_1, \ldots, x_n$, the joint M-estimator $(\hat{\mu}, \hat{\sigma})$ solves
$$
\sum_{i=1}^n \psi\!\left(\frac{x_i - \mu}{\sigma}\right) = 0, \qquad
\sum_{i=1}^n \chi\!\left(\frac{x_i - \mu}{\sigma}\right) = (n-1)\delta,
$$
with a re-descending $\psi$ family (`mopt`, `bisquare`, `huber`) and tuning constants chosen for a target asymptotic efficiency (default 0.95). Equivalent to a robust mean / robust scale pair when $\psi$ and $\chi$ derive from the same $\rho$.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/MLocDis.R` line 40.
- Exported names: `locScaleM`, `MLocDis` (aliases).
- Internal helpers in the same file: `wfun` (weight), `psif`, `psipri` (psi prime). Tuning constants come from `psiFunUtils.R`.

## 4. Inputs / Outputs / Return structure
**Signature (R):** `locScaleM(x, psi="mopt", eff=0.95, maxit=50, tol=1e-4, na.rm=FALSE)`

**Returns** an R list with named elements (subject to confirmation at implementation time via `str(...)`):
- `mu` — robust location estimate
- `disper` — robust scale estimate
- `std.mu` — standard error of mu
- `iter` — IRLS iteration count

## 5. Dependencies
- RobStatTM only.

## 6. Python wrapper design
**Public API:**

```python
def loc_scale_m(
    x: ArrayLike,
    *,
    psi: Literal["mopt", "bisquare", "huber"] = "mopt",
    eff: float = 0.95,
    maxit: int = 50,
    tol: float = 1e-4,
    na_rm: bool = False,
) -> LocScaleMResult: ...
```

**Dataclass:**

```python
@dataclass(frozen=True, slots=True)
class LocScaleMResult:
    mu: float
    disper: float
    std_mu: float        # R: std.mu
    iter: int
```

**Conversions:**
- `x`: `np.asarray(x, dtype=float)`; raise `TypeError` for non-numeric.
- `na_rm=False` (default): NaN in input → raise `ValueError("input contains NaN; pass na_rm=True to drop")`.

**Edge cases:** sample size < 2; all-equal input (R returns 0 scale); tied-data warning (R emits `wrn` string — surface as Python `warnings.warn`).

## 7. Validation strategy
Cases 1, 2, 3, 4, 7, 8, 9 (family × eff sweep), 10 (determinism) from `docs/validation_strategy.md §3`. Existing notebook already validates this function at strict tier — port that fixture into `tests/univariate/test_loc_scale_m.py`.
