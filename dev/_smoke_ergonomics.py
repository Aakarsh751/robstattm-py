import os, sys
if sys.platform == "win32" and "R_HOME" not in os.environ:
    os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
    os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]

import robstattm_py as rpm

df = rpm.datasets.mineral()
fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)

print("--- to_dict ---")
d = fit.to_dict()
print("keys:", sorted(d)[:8])

print("\n--- to_r ---")
print("type:", type(fit.to_r()).__name__)

print("\n--- coef_df ---")
print(fit.coef_df())

print("\n--- _repr_html_ length ---")
print(len(fit._repr_html_()))

print("\n--- rpm.help('lmrobdetMM') ---")
rpm.help("lmrobdetMM")

print("\n--- list_names ---")
print("# of R names:", len(rpm.list_names()))
