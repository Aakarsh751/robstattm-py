"""Smoke check: lmrobdet_mm on mineral vs direct R."""
import numpy as np
import robstatm_py as rpm
from robstatm_py._r import r

ro = r()
ro.r("library(RobStatTM); data(mineral)")
r_fit = ro.r("lmrobdetMM(zinc ~ copper, data = mineral)")

df = rpm.datasets.mineral()
py = rpm.lmrobdet_mm("zinc ~ copper", data=df)

print(py)
print()

# Pull R scalars
r_coef = np.asarray(ro.r("coef(fit_for_check <- lmrobdetMM(zinc ~ copper, data=mineral))")).astype(float)
r_scale = float(ro.r("fit_for_check$scale")[0])
r_R2 = float(ro.r("fit_for_check$r.squared")[0])
r_iter = int(ro.r("fit_for_check$iter")[0])
r_conv = bool(ro.r("fit_for_check$converged")[0])
r_loss = float(ro.r("fit_for_check$loss")[0])
r_rweights = np.asarray(ro.r("fit_for_check$rweights")).astype(float)
r_residuals = np.asarray(ro.r("fit_for_check$residuals")).astype(float)
r_fitted = np.asarray(ro.r("fit_for_check$fitted.values")).astype(float)
r_cov = np.asarray(ro.r("fit_for_check$cov")).astype(float)

def chk(label, py_v, r_v):
    py_a = np.asarray(py_v, dtype=float)
    r_a = np.asarray(r_v, dtype=float)
    max_diff = np.max(np.abs(py_a - r_a)) if py_a.size else 0.0
    flag = "OK" if max_diff == 0.0 else f"DIFF max={max_diff:.3e}"
    print(f"  {label:18s} {flag}")

chk("coefficients", py.coefficients, r_coef)
chk("scale", py.scale, r_scale)
chk("r_squared", py.r_squared, r_R2)
chk("iter", py.iter, r_iter)
chk("converged", py.converged, r_conv)
chk("loss", py.loss, r_loss)
chk("rweights", py.rweights, r_rweights)
chk("residuals", py.residuals, r_residuals)
chk("fitted_values", py.fitted_values, r_fitted)
chk("cov", py.cov, r_cov)
