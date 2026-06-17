# TSGS (external R package GSE — IMPLEMENTED 2026-06-13)

> **Status (2026-06-13):** implemented against installed GSE **4.2-4** as
> `rpm.tsgs` in `robstatm_py.external`. S4 object, same shape as `GSEResult`
> plus the filtered-data matrix `xf`. 100% strict-tier vs R
> (`tests/external/test_gse.py::TestTSGS`). See "Actual implementation" below.

## 1. Statistical purpose
**Two-Step Generalized S-Estimator** for **cell-wise** outliers (individual entries contaminated rather than entire rows). Maronna et al. (2019, §6.13).

## 2. Mathematical background
Stage 1: flag suspicious cells using univariate or low-dim robust filters; Stage 2: treat flagged cells as missing and run `GSE` (see `docs/research/GSE.md`).

## 3. R implementation
- External CRAN package `GSE` (same package as `GSE` function).
- Main entry: `TSGS(x, filter = "UBF-DDC", partial.impute = FALSE, ...)`.

## 4. Inputs / Outputs / Return structure
S4 object similar to `GSE` plus `filtered` (boolean mask of flagged cells) and `filter` (name of method used).

## 5. Dependencies
- GSE
- Optional: cellWise (for the DDC filter); some versions vendor it internally

## 6. Python wrapper design

```python
def tsgs(
    X: ArrayLike,
    *,
    filter: Literal["UBF-DDC","DDC","UBF","UF"] = "UBF-DDC",
    partial_impute: bool = False,
    tol: float = 1e-4,
    maxiter: int = 150,
    method: Literal["bisquare","rocke"] = "bisquare",
) -> TSGSResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class TSGSResult:
    mu: np.ndarray
    cov: np.ndarray
    weights: np.ndarray
    filtered: np.ndarray         # bool mask of flagged cells
    iter: int
    converged: bool
```

## 7. Validation strategy
Cases 1, 2, 6 (cell-wise contamination is the point), 7, 10. Synthetic cell-wise outliers (corrupt 1% of entries chosen uniformly at random).

---

## Actual implementation (GSE 4.2-4, 2026-06-13)

**Module:** `robstatm_py.external.gse` — exposed as `rpm.tsgs`.

`GSE::TSGS(x, filter="UBF-DDC", partial.impute=FALSE, tol=1e-4, maxiter=150,
method="bisquare", ...)` returns an **S4** object (class `TSGS`) with the same
slots as `GSE` plus `xf` (the step-1 filtered data; flagged cells are NaN).

```python
@dataclass(frozen=True, slots=True)
class TSGSResult:
    mu:       np.ndarray
    cov:      np.ndarray   # slot S
    pmd:      np.ndarray
    pmd_adj:  np.ndarray
    weights:  np.ndarray
    ximp:     np.ndarray   # imputed
    xf:       np.ndarray   # filtered (NaN for flagged cells)
    sc:       float
    iter:     int
    eps:      float
    column_names: tuple[str, ...] | None
```

### Notes
- `filter` ∈ {"UBF-DDC", "UBF", "DDC", "UF"} (default "UBF-DDC").
- `xf` carries NaN for filtered cells; tests use nan-aware equality.
- Stochastic → `rpm.set_seed(n)` before for reproducibility.

### Validation
`tests/external/test_gse.py::TestTSGS`: mu, cov, pmd, xf (nan-aware), sc, repr.
Strict-tier; auto-skips via `needs_gse`.
