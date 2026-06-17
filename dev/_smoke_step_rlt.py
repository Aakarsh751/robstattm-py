"""Smoke check: step_lmrobdet + rob_linear_test."""
import numpy as np
import robstatm_py as rpm
from robstatm_py import set_seed
from robstatm_py._r import r

ro = r()
ro.r("library(RobStatTM); data(mineral); data(stackloss)")

# step --------------------------------------------------------
set_seed(42)
fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
set_seed(42)
sfit = rpm.step_lmrobdet(fit)
print("step:", sfit)
print("rfpe trace:", sfit.anova_rfpe)
print("final formula:", sfit.final_formula)

# Compare R-side
ro.r("set.seed(42L); f_r <- lmrobdetMM(zinc ~ copper, data=mineral); "
     "set.seed(42L); s_r <- step.lmrobdetMM(f_r, trace=FALSE)")
r_rfpe = np.asarray(ro.r("s_r$anova$RFPE"), dtype=float)
print("R-side RFPE:", r_rfpe)
diff = float(np.max(np.abs(sfit.anova_rfpe - r_rfpe))) if sfit.anova_rfpe.size else 0
print(f"diff anova_rfpe: {'OK' if diff == 0.0 else diff}")

# rob_linear_test ---------------------------------------------------
print("\n=== rob_linear_test ===")
df = rpm.datasets.stackloss()
set_seed(42)
full = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df)
set_seed(42)
red = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)
t = rpm.rob_linear_test(full, red)
print(t)

# Compare
ro.r("set.seed(42L); ff <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., data=stackloss); "
     "set.seed(42L); rr <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp, data=stackloss); "
     "rlt <- rob.linear.test(ff, rr)")
r_test = float(ro.r("rlt$test")[0])
r_cp = float(ro.r("rlt$chisq.pvalue")[0])
r_fp = float(ro.r("rlt$F.pvalue")[0])
print(f"diff test:         {'OK' if t.test == r_test else abs(t.test - r_test)}")
print(f"diff chisq_pvalue: {'OK' if t.chisq_pvalue == r_cp else abs(t.chisq_pvalue - r_cp)}")
print(f"diff f_pvalue:     {'OK' if t.f_pvalue == r_fp else abs(t.f_pvalue - r_fp)}")
