import robstatm_py as rpm

df = rpm.datasets.stackloss()

# Fit the full model, then let step_lmrobdet drop terms to minimise the
# robust final prediction error (RFPE) — robust stepwise model selection.
# lmrobdet_mm / step_lmrobdet use the deterministic Peña–Yohai initial
# estimator, so results are reproducible without set_seed.
full = rpm.lmrobdet_mm(
    "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df
)
step = rpm.step_lmrobdet(full)

print("selected coefficients:", step.coefficients.round(4))
print("RFPE at each step     :", step.anova_rfpe.round(3))
