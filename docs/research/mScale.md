# mScale (also exposed as scaleM, mscale)

## 1. Statistical purpose
Univariate M-estimate of **scale** alone (no concurrent location estimate). Used both directly (Maronna et al. 2019, §2.5–§2.6) and as the inner scale step inside MM-regression and S/MM covariance fits.

## 2. Mathematical background
Solves $\frac{1}{n}\sum \rho\!\bigl(\frac{u_i}{s}\bigr) = \delta$ for $s$, with $\rho$ from the bisquare family (default) and $\delta = 0.5$ giving 50% breakdown.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/DCML.R`.
  - `scaleM` at line 52 (parameter-friendly entry point)
  - `mscale` at line 68 (alternative entry with explicit tuning.chi)
- The package exports both. RobStatTM's `Multirobu.R` also defines an internal `M_Scale` used by covariance fits — out of public scope.

## 4. Inputs / Outputs / Return structure
**Signature:** `scaleM(u, delta=0.5, family="bisquare", max.it=50, tol=1e-4)`

**Returns:** a single numeric (scalar) — *not* a list. This is unusual; the wrapper returns a plain `float`, not a dataclass.

## 5. Dependencies
- RobStatTM only.

## 6. Python wrapper design
```python
def m_scale(
    u: ArrayLike,
    *,
    delta: float = 0.5,
    family: Literal["bisquare", "huber", "mopt"] = "bisquare",
    max_it: int = 50,    # R: max.it
    tol: float = 1e-4,
) -> float: ...
```

**Conversions:** `u` → `np.asarray(u, dtype=float)`. Validate `delta in (0, 1)`.

**Edge cases:**
- All zeros → R returns 0; Python should too (strict-tier).
- Negative values OK (operates on the absolute deviations internally).

## 7. Validation strategy
Cases 1–4, 7, 9, 10. The existing notebook covers this — port the strict-tier comparison directly.
