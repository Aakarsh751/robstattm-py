"""Live UI demo — exercises the user-facing surface in docs/user_interface.md.

Run with:  python tests/_ui_demo.py
This is NOT a pytest test; it's a smoke-walk-through that prints what a
new user sees when they reach for the library.
"""
from __future__ import annotations




def banner(s):
    print("\n" + "=" * 78); print(s); print("=" * 78)


banner("1.  import robstattm_py as rpm")
import robstattm_py as rpm
print(f"   version  = {rpm.__version__}")
print(f"   modules  = datasets, plotting, psi")
print(f"   wrappers = {len([n for n in dir(rpm) if not n.startswith('_')])} symbols on the package root")


banner("2.  rpm.check_setup()  — environment check")
rpm.check_setup()


banner("3.  rpm.datasets.<name>()  — pandas DataFrames")
df = rpm.datasets.mineral()
print(f"   mineral.shape = {df.shape}")
print(df.head(3))


banner("4.  rpm.lmrobdet_mm('y ~ x', data=df)  — actual robust fit")
fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
print(f"   repr -> {fit!r}")


banner("5.  fit.summary()  — port of R's summary.lmrobdetMM")
s = fit.summary()
print(s)


banner("6.  fit.summary().coefficients_table  — pandas DataFrame, R column names")
print(s.coefficients_table)


banner("7.  fit.predict(newdata)  — works on the wrapped fit")
import pandas as pd
new_df = pd.DataFrame({"copper": [10, 50, 100, 500]})
pred = fit.predict(new_df)
print(f"   predict({list(new_df.copper)}) = {pred}")


banner("8.  fit.hatvalues()  — port of R's hatvalues.lmrob")
hv = fit.hatvalues()
print(f"   hatvalues range:  [{hv.min():.4f}, {hv.max():.4f}]")
print(f"   hatvalues sum:     {hv.sum():.4f}  (should equal #predictors = 2)")


banner("9.  Covariance pipeline")
wine = rpm.datasets.wine()
rpm.set_seed(42)
cov_fit = rpm.cov_rob_mm(wine)
print(f"   cov_rob_mm    : {cov_fit!r}")
print(f"   .summary()    : {cov_fit.summary()!r}")
print(f"   eigvals first :  {cov_fit.summary().evals[:3]}")
print(f"   prop variance :  {cov_fit.summary().proportion_of_variance[:3]}")


banner("10. Robust PCA")
rpm.set_seed(42)
prc = rpm.prcomp_rob(wine)
print(f"   prcomp_rob    : {prc!r}")
psum = prc.summary()
print(f"   importance matrix (first 4 components):")
print(psum.importance.iloc[:, :4])


banner("11. Robust logistic regression")
import numpy as np
np.random.seed(0)
n = 60
x = np.random.randn(n)
y = (x + 0.5 * np.random.randn(n) > 0).astype(int)
glm_df = pd.DataFrame({"x": x, "y": y})
logfit = rpm.by_logreg(X=glm_df[["x"]].to_numpy(), y=glm_df["y"].to_numpy())
print(f"   by_logreg     : coefficients = {logfit.coefficients}")
print(f"   converged     : {logfit.converged}")


banner("12. Plotting (Path A — R-graphics via rpy2)")
from robstattm_py.plotting import r_plot
path = r_plot("plot(zinc ~ copper, data=mineral, pch=19, main='Mineral')",
              path="tests/_ui_demo.png", dpi=80)
print(f"   r_plot returned: {path}")
print(f"   file size: {path.stat().st_size} bytes")


banner("13. Round-trip: result objects are pickle-safe")
import pickle
b = pickle.dumps(fit)
back = pickle.loads(b)
print(f"   pickle round-trip OK; back.summary() works:")
print(f"     coef = {back.coefficients}")
print(f"     summary scale = {back.summary().scale:.6f}")


banner("14. R-name aliases (compat layer status)")
try:
    from robstattm_py import compat_r
    print("   compat_r module: AVAILABLE")
except ImportError:
    print("   compat_r module: NOT YET IMPLEMENTED (planned per UI §2.3)")


banner("UI demo complete.")
