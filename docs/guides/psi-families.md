# ψ-loss families

Robust estimators replace the squared-error loss with a **bounded** loss
function ρ, whose derivative ψ caps the influence of any single observation.
RobStatTM-Py exposes the loss families and their ρ/ψ functions under
`robstattm_py.psi`.

```python
import robstattm_py as rpm
from robstattm_py import psi
```

## Available families

| Family | `psi.<name>` | Description |
|---|---|---|
| Bisquare (Tukey) | `psi.bisquare` | Redescending loss; influence drops to zero for large residuals. |
| Huber | `psi.huber` | Quadratic near zero, linear in the tails (monotone ψ). |
| Optimal | `psi.opt` | Optimal bias-robust loss (polynomial form, RobStatTM ≥ 1.0.7). |
| Modified optimal | `psi.mopt` | "mopt" variant of the optimal loss. |
| Optimal (legacy) | `psi.optv0` | Pre-1.0.7 optimal loss (for reproducing older results). |
| Modified optimal (legacy) | `psi.moptv0` | Pre-1.0.7 "mopt" loss. |

Each family object resolves the **tuning constant** that delivers a requested
Gaussian efficiency:

```python
cc = psi.bisquare(0.95)     # tuning constant for 95% efficiency
```

## ρ, ψ, and ψ′

The loss `rho`, its derivative `rhoprime` (the ψ function), and second
derivative `rhoprime2` are available directly:

```python
import numpy as np
from robstattm_py import psi

r = np.linspace(-6, 6, 13)
cc = psi.bisquare(0.95)

loss      = psi.rho(r, family="bisquare", cc=cc)        # the bounded loss values
influence = psi.rhoprime(r, family="bisquare", cc=cc)   # the ψ (influence) function
curvature = psi.rhoprime2(r, family="bisquare", cc=cc)  # ψ′
```

## Choosing a family

- **Bisquare** is the default for most estimators — strong outlier rejection.
- **Huber** is a gentler, monotone choice when you prefer downweighting over
  outright rejection.
- **opt / mopt** are the optimal bias-robust losses used by `lmrobdet_mm`; select
  them through `lmrobdet_control(family=...)`.

See [`lmrobdet_control`](../api/wrappers/lmrobdet_control.md) for wiring a family
into a regression fit.
