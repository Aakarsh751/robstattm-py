"""One-off parity check: stackloss step_lmrobdet with custom control."""
import numpy as np
import robstatm_py as rpm
from robstatm_py._r import r

df = rpm.datasets.stackloss()
ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")

full = rpm.lmrobdet_mm(
    "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
    data=df,
    control=ctrl,
)
step = rpm.step_lmrobdet(full)

ro = r()
ro.r("library(RobStatTM); data(stackloss)")
ro.r('cont <- lmrobdet.control(bb= 0.5, efficiency = 0.85, family = "bisquare")')
ro.r(
    "full_r <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., "
    "data=stackloss, control=cont)"
)
ro.r("step_r <- step.lmrobdetMM(full_r, trace=FALSE)")

r_coef = np.asarray(ro.r("coef(step_r)"), dtype=float)
r_rfpe = np.asarray(ro.r("step_r$anova$RFPE"), dtype=float)
r_scale = float(np.asarray(ro.r("step_r$scale"), dtype=float).ravel()[0])
r_formula = str(ro.r("deparse(formula(step_r))")[0])

py_coef = step.coefficients
py_rfpe = step.anova_rfpe
py_scale = step.scale

print("=== Coefficients ===")
print("Python:", np.round(py_coef, 6))
print("R     :", np.round(r_coef, 6))
print("Match :", np.array_equal(py_coef, r_coef))

print("\n=== RFPE ===")
print("Python:", np.round(py_rfpe, 6))
print("R     :", np.round(r_rfpe, 6))
print("Match :", np.array_equal(py_rfpe, r_rfpe))

print("\n=== Scale ===")
print("Python:", py_scale)
print("R     :", r_scale)
print("Match :", py_scale == r_scale)

print("\n=== Formula ===")
print("Python:", step.final_formula)
print("R     :", r_formula)

overall = (
    np.array_equal(py_coef, r_coef)
    and np.array_equal(py_rfpe, r_rfpe)
    and py_scale == r_scale
)
print("\nOVERALL BIT-IDENTICAL:", overall)
