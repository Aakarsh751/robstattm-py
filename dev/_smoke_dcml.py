"""Smoke check: lmrobdet_dcml, lmrob_m, pyinit vs direct R."""
import numpy as np
import robstatm_py as rpm
from robstatm_py._r import r
from robstatm_py import set_seed

ro = r()
ro.r("library(RobStatTM); library(pyinit); data(mineral)")

# lmrobdet_dcml ---------------------------------------------------------
set_seed(42)
df = rpm.datasets.mineral()
d_py = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
ro.r("set.seed(42L); d_r <- lmrobdetDCML(zinc ~ copper, data=mineral)")

def chk(label, py_v, r_v):
    py_a = np.asarray(py_v, dtype=float)
    r_a = np.asarray(r_v, dtype=float)
    diff = float(np.max(np.abs(py_a - r_a))) if py_a.size else 0.0
    print(f"  {label:18s} {'OK' if diff == 0.0 else f'DIFF max={diff:.3e}'}")

print("=== DCML on mineral ===")
print(d_py)
chk("coefficients", d_py.coefficients, np.asarray(ro.r("coef(d_r)")))
chk("scale", d_py.scale, float(ro.r("d_r$scale")[0]))
chk("t0", d_py.t0, float(ro.r("d_r$t0")[0]))
chk("residuals", d_py.residuals, np.asarray(ro.r("d_r$residuals")))
chk("fitted_values", d_py.fitted_values, np.asarray(ro.r("d_r$fitted.values")))
chk("cov", d_py.cov, np.asarray(ro.r("d_r$cov")))

# lmrob_m ----------------------------------------------------------------
print("\n=== lmrobM on mineral ===")
set_seed(42)
m_py = rpm.lmrob_m("zinc ~ copper", data=df)
ro.r("set.seed(42L); m_r <- lmrobM(zinc ~ copper, data=mineral)")
print(m_py)
chk("coefficients", m_py.coefficients, np.asarray(ro.r("coef(m_r)")))
chk("scale", m_py.scale, float(ro.r("m_r$scale")[0]))
chk("r_squared", m_py.r_squared, float(ro.r("m_r$r.squared")[0]))
chk("rweights", m_py.rweights, np.asarray(ro.r("m_r$rweights")))

# pyinit -----------------------------------------------------------------
print("\n=== pyinit on mineral ===")
X = df[["copper"]].to_numpy(dtype=float)
y = df["zinc"].to_numpy(dtype=float)
set_seed(42)
p_py = rpm.pyinit(X, y)
ro.globalenv["X_pi"] = X
ro.globalenv["y_pi"] = y
ro.r("set.seed(42L); p_r <- pyinit::pyinit(x=X_pi, y=y_pi, cc=1.5476, "
     "psc_keep=0.5, resid_keep_prop=0.2, resid_keep_thresh=2)")
print(p_py)
chk("coefficients", p_py.coefficients, np.asarray(ro.r("p_r$coefficients")))
chk("objective", p_py.objective, np.asarray(ro.r("p_r$objective")))
