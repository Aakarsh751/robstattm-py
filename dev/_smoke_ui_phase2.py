"""Smoke-test the new UI surfaces from this turn."""
import os, sys
if sys.platform == "win32" and "R_HOME" not in os.environ:
    os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
    os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]

import numpy as np, pandas as pd
import robstattm_py as rpm


def banner(s): print("\n=== " + s + " ===")

banner("r_started() BEFORE any wrapper call")
print("r_started:", rpm.r_started())

df = rpm.datasets.mineral()
fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)

banner("r_started() AFTER first call")
print("r_started:", rpm.r_started())

banner("fit.to_dict()")
d = fit.to_dict()
print("dict keys:", sorted(d)[:6], "...")

banner("fit.coef_df()")
print(fit.coef_df())

banner("fit.to_r()")
print("type:", type(fit.to_r()).__name__)

banner("fit._repr_html_() length")
print(len(fit._repr_html_()))

banner("fit.plot_residuals()")
p = fit.plot_residuals(path="tests/_smoke_residuals.png", dpi=80, width=5, height=4)
print("file:", p, "bytes:", p.stat().st_size)

banner("rpm.help('covRobMM')")
rpm.help("covRobMM")

banner("rpm.set_n_jobs(2)")
print("prev mc.cores:", rpm.set_n_jobs(2))

banner("rpm.bench.timer(...)")
t = rpm.bench.timer(lambda: rpm.lmrobdet_mm("zinc ~ copper", data=df))
print(t)

banner("(X, y) array form")
X = df[["copper"]].to_numpy()
y = df["zinc"].to_numpy()
fit_xy = rpm.lmrobdet_mm(X=X, y=y)
print("coefficients:", fit_xy.coefficients)
print("matches formula form:",
      np.array_equal(fit_xy.coefficients, fit.coefficients))

banner("(X, y) with pd.DataFrame X")
fit_df = rpm.lmrobdet_mm(X=df[["copper"]], y=df["zinc"])
print("formula auto-built:", fit_df.formula)
print("matches:", np.array_equal(fit_df.coefficients, fit.coefficients))

banner("error: mixing forms raises")
try:
    rpm.lmrobdet_mm("y ~ x", data=df, X=X, y=y)
except TypeError as e:
    print("OK:", e)

print("\nALL GOOD.")
