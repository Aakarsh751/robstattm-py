"""Manual strict-tier check: Python wrapper vs direct R reference."""
import numpy as np

import robstatm_py as rpm
from robstatm_py._r import r

# Deterministic input (no randomness) so R and Python see identical bits.
x = np.array(
    [
        1.2, -0.4, 0.7, 2.1, -1.0, 0.3, 1.8, -2.5, 0.9, 0.0,
        10.0, -10.0, 0.5, -0.3, 1.5, 2.2, -1.7, 0.6, 0.1, -0.8,
    ]
)

# Python wrapper outputs
py_mopt = rpm.loc_scale_m(x, psi="mopt", eff=0.95)
py_bisq = rpm.loc_scale_m(x, psi="bisquare", eff=0.95)
py_hub = rpm.loc_scale_m(x, psi="huber", eff=0.90)
py_scale_b = rpm.m_scale(x, family="bisquare", delta=0.5)
py_scale_h = rpm.m_scale(x, family="huber", delta=0.5)

# Direct R reference
ro = r()
ro.globalenv["x"] = x
ro.r('library(RobStatTM)')

cases = [
    ("mopt mu",     py_mopt.mu,     'locScaleM(x, psi="mopt", eff=0.95)$mu'),
    ("mopt std_mu", py_mopt.std_mu, 'locScaleM(x, psi="mopt", eff=0.95)$std.mu'),
    ("mopt disper", py_mopt.disper, 'locScaleM(x, psi="mopt", eff=0.95)$disper'),
    ("bisq mu",     py_bisq.mu,     'locScaleM(x, psi="bisquare", eff=0.95)$mu'),
    ("bisq disper", py_bisq.disper, 'locScaleM(x, psi="bisquare", eff=0.95)$disper'),
    ("huber mu",    py_hub.mu,      'locScaleM(x, psi="huber", eff=0.90)$mu'),
    ("huber disper",py_hub.disper,  'locScaleM(x, psi="huber", eff=0.90)$disper'),
    ("scale bisq",  py_scale_b,     'scaleM(x, family="bisquare", delta=0.5)'),
    ("scale huber", py_scale_h,     'scaleM(x, family="huber", delta=0.5)'),
]

n_ok = n_diff = 0
for label, py, rexpr in cases:
    rval = float(ro.r(rexpr)[0])
    diff = abs(float(py) - rval)
    flag = "OK" if diff == 0.0 else f"DIFF={diff:.3e}"
    print(f"  {label:14s}  py={py!r:24s}  r={rval!r:24s}  {flag}")
    if diff == 0.0:
        n_ok += 1
    else:
        n_diff += 1

print(f"\nStrict-tier match: {n_ok}/{len(cases)} ({n_diff} differ)")
