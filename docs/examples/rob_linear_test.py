import robstatm_py as rpm

df = rpm.datasets.stackloss()

# Robust analogue of the classical F-test for nested linear models:
# is the extra term `Acid.Conc.` worth keeping?
rpm.set_seed(42)
full = rpm.lmrobdet_mm(
    "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df
)
rpm.set_seed(42)
reduced = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)

res = rpm.rob_linear_test(full, reduced)
print(res)
print(f"test statistic = {res.test:.4f}")
