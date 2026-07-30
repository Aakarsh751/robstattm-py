# ψ-family infrastructure (bisquare, huber, mopt, moptv0, opt, optv0, rho, rhoprime, rhoprime2)

## 1. Statistical purpose
The low-level ψ/χ/ρ machinery used by every robust estimator in the package. Exposed publicly so users can:
- compute $\rho(u/s)$, $\psi(u/s) = \rho'(u/s)$, $\psi'(u/s) = \rho''(u/s)$ for any supported family;
- compare loss curves;
- write custom diagnostics that match the package's internal calibration.

## 2. Mathematical background
- **bisquare** (Tukey): $\rho(u) = 1 - (1 - u^2)^3$ for $|u|<1$, else 1.
- **huber**: hybrid quadratic / linear.
- **mopt** (modified optimal, Yohai/Salibian-Barrera): the default for `lmrobdetMM`.
- **opt** (Yohai optimal): asymptotically minimax.
- **moptv0**, **optv0**: alternative tuning-constant calibrations (legacy).

Tuning constants for a target efficiency (`eff = 0.85, 0.9, 0.95`) and breakdown point (`bdp = 0.5` typically) are precomputed inside RobStatTM via `consMMKur`, `consRocke`, etc.

## 3. R implementation
File: `psiFuns.R` + `psiFunUtils.R`. The family identifier objects (`bisquare`, `huber`, ...) are R objects (numeric codes) consumed by the C-level `Mpsi`/`Mchi`/`Mwgt` from robustbase that the RobStatTM C kernels also use. Top-level `rho(x, family, ...)`, `rhoprime(x, family, ...)`, `rhoprime2(x, family, ...)` dispatch on the family.

## 4. Inputs / Outputs / Return structure
- `bisquare`, `huber`, `mopt`, `opt`, `moptv0`, `optv0`: R objects (constants).
- `rho(x, family, k)`, `rhoprime(x, family, k)`, `rhoprime2(x, family, k)`: numeric vector inputs → numeric vector outputs of the same length.

## 5. Dependencies
RobStatTM only (uses base R + the package's own C kernels).

## 6. Python wrapper design
A small **`robstattm_py.psi` submodule**:

```python
from robstattm_py.psi import bisquare, huber, mopt, opt, moptv0, optv0
from robstattm_py.psi import rho, rhoprime, rhoprime2

# 1. Family identifiers
bisquare.name     # "bisquare"
bisquare.tuning_for(eff=0.95)   # default tuning constant for 95% efficiency

# 2. Evaluate
import numpy as np
u = np.linspace(-3, 3, 200)
rho(u, family="mopt", eff=0.95)         # array_like (200,)
rhoprime(u, family="mopt", eff=0.95)    # psi
rhoprime2(u, family="mopt", eff=0.95)   # psi prime

# 3. Plot a loss curve
import matplotlib.pyplot as plt
plt.plot(u, rho(u, family="bisquare", eff=0.95), label="bisquare")
plt.plot(u, rho(u, family="mopt", eff=0.95), label="m-opt")
plt.legend()
```

Each family object is a small frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class PsiFamily:
    name: Literal["bisquare","huber","mopt","opt","moptv0","optv0"]
    def tuning_for(self, *, eff: float | None = None, bdp: float | None = None) -> float: ...
```

The `rho`, `rhoprime`, `rhoprime2` functions accept either:
- `family="bisquare"` + `eff=0.95` (computes tuning automatically), or
- `family=bisquare` (the PsiFamily object) + explicit `k=` tuning constant.

## 7. Validation strategy
- **Pointwise strict-tier:** `rho(u, family="mopt", eff=0.95)` matches R `rho(u, family="mopt", efficiency=0.95)` for the same `u` array.
- **Tuning-constant table:** `bisquare.tuning_for(eff=e) == R("constant_for_eff('bisquare', e)")` for `e ∈ {0.85, 0.90, 0.95}`.
- **Identity tests:** `rhoprime` numeric derivative of `rho` (finite differences, Stable tier ≤ 1e-6).
- **Cross-validation:** the rweights of an `lmrobdet_mm` fit equal `rhoprime(fit.residuals / fit.scale, family=fit.control.family) / (fit.residuals / fit.scale)` (up to scaling) — verified in `tests/regression/test_lmrobdet_mm.py`.

This module is small but **load-bearing for every other module** — bugs here cascade. Schedule it for Phase 1 alongside the univariate wrappers.
