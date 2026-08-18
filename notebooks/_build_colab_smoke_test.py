"""Generate ``notebooks/colab_smoke_test.ipynb``.

The notebook is a *test*, not a demo. It exists because two failures were
reported from real machines that CI does not resemble, a Windows DLL conflict
and, on Google Colab, rpy2 refusing to load a provisioned R while `doctor`
simultaneously reported rpy2's version. Colab is the environment I cannot
reproduce locally, so the notebook has to do the reporting for me: every cell
prints enough that a failure is diagnosable from the output alone, and the last
cell prints a copy-pasteable report.

Regenerate with:  python notebooks/colab_smoke_test.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = "https://github.com/Aakarsh751/robstattm-py.git"

CELLS: list[tuple[str, str]] = []


def md(text: str) -> None:
    CELLS.append(("markdown", text.strip("\n")))


def code(text: str) -> None:
    CELLS.append(("code", text.strip("\n")))


md(f"""
# RobStatTM-Py - Colab smoke test

Runs the package end to end on Google Colab and reports what happened. Takes
about **6–10 minutes**, most of it downloading R.

Use **Runtime → Run all**. If anything fails, the last cell prints a report to
paste into an issue at
<https://github.com/Aakarsh751/robstattm-py/issues>.

This notebook exists to check two fixes that could not be verified locally:

1. rpy2 refusing to load a provisioned R, previously misreported as
   *"rpy2 is not installed"* while the same report showed rpy2's version.
2. The automatic fallback to rpy2's ABI binding when its compiled binding was
   built against a different R, which is the normal situation on Colab,
   where rpy2 comes preinstalled.

> Source: {REPO}
""")

md("""
## 0 - What we start with

Colab ships its own Python, and usually its own R and rpy2. Worth recording
before we change anything, because the interesting failures come from the
*combination*.
""")

code('''
import os, platform, shutil, subprocess, sys

REPORT = {}

def record(key, value):
    REPORT[key] = value
    print(f"{key:24} {value}")

record("python", platform.python_version())
record("machine", platform.machine())
record("platform", platform.platform())

r_binary = shutil.which("R")
record("R on PATH", r_binary or "none")
if r_binary:
    out = subprocess.run(["R", "--version"], capture_output=True, text=True).stdout
    record("R version", out.splitlines()[0] if out else "unknown")

try:
    import rpy2
    from importlib.metadata import version
    record("rpy2 preinstalled", version("rpy2"))
except Exception as exc:
    record("rpy2 preinstalled", f"no ({exc.__class__.__name__})")
''')

md("""
## 1 - Install

Not on PyPI yet, so this installs from the repository. `-q` keeps the output
short; drop it if the install itself is what fails.
""")

code(f'''
!git clone --depth 1 {REPO} /content/robstattm-py 2>&1 | tail -2
!pip install -q /content/robstattm-py 2>&1 | tail -5

from importlib.metadata import version
record("robstattm-py", version("robstattm-py"))
''')

md("""
## 2 - Import without R

Importing the package must **not** start R. If this is slow or fails, the
problem is packaging, not R.
""")

code('''
import importlib, sys

for mod in [m for m in list(sys.modules) if m.startswith(("robstattm_py", "rpy2"))]:
    sys.modules.pop(mod, None)

import robstattm_py as rpm
record("import ok", rpm.__version__)
record("R started by import", "rpy2.rinterface_lib.openrlib" in sys.modules)
print("\\nExpected: 'R started by import' is False, R is loaded lazily.")
''')

md("""
## 3 - Provision R

Downloads R plus RobStatTM into a directory the package owns. **This is the
step that failed before**, so its full output is kept.

Several minutes. `--yes` skips the confirmation prompt, which a notebook
cannot answer.
""")

code('''
import subprocess, sys

setup = subprocess.run(
    [sys.executable, "-m", "robstattm_py.cli", "setup", "--yes"],
    capture_output=True, text=True,
)
print(setup.stdout[-4000:])
if setup.stderr.strip():
    print("--- stderr ---")
    print(setup.stderr[-4000:])

record("setup exit code", setup.returncode)
REPORT["setup tail"] = (setup.stdout + setup.stderr)[-1500:]
''')

md("""
## 4 - Diagnose

`doctor` must end with **`Result: READY`**.

The specific bug this checks for: a report that names an rpy2 version *and*
claims rpy2 is not installed. Those cannot both be true, and the assertion below
fails if they ever are again.
""")

code('''
doctor = subprocess.run(
    [sys.executable, "-m", "robstattm_py.cli", "doctor"],
    capture_output=True, text=True,
)
print(doctor.stdout[-5000:])
if doctor.stderr.strip():
    print("--- stderr ---")
    print(doctor.stderr[-2000:])

record("doctor exit code", doctor.returncode)
record("doctor READY", "Result: READY" in doctor.stdout)
REPORT["doctor"] = doctor.stdout[-3000:]

text = doctor.stdout
contradiction = "rpy2 is not installed" in text and "  version" in text.split("rpy2")[1][:200]
record("self-contradictory", contradiction)
assert not contradiction, (
    "REGRESSION: doctor reports an rpy2 version and also says rpy2 is not "
    "installed. This is the Colab bug and it is supposed to be fixed."
)
''')

md("""
## 5 - Load R and fit something real

The first call that actually starts R. If rpy2's compiled binding cannot load
the provisioned R, the package should fall back to the ABI binding *with a
warning* rather than failing, that warning appearing here is a success, not a
problem.

The coefficients are checked against the values R produces. They should match to
the last digit; anything else means the bridge is not faithful.
""")

code('''
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    mineral = rpm.datasets.mineral()
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

abi = [str(w.message) for w in caught if "ABI" in str(w.message)]
record("fell back to ABI", bool(abi))
if abi:
    print("fallback warning (expected on Colab, not a failure):")
    print(" ", abi[0][:200], "\\n")

print(fit.summary())

EXPECTED = (15.2012174, 0.0125614958)
got = tuple(float(c) for c in fit.coefficients)
close = all(abs(a - b) < 1e-6 for a, b in zip(got, EXPECTED))
record("coefficients", [round(c, 8) for c in got])
record("matches R", close)
assert close, f"expected {EXPECTED}, got {got}"
''')

md("""
## 6 - Exercise the rest of the surface

One estimator per family, so a failure points at a specific area rather than
"something broke".
""")

code('''
import numpy as np

results = {}

def check(name, fn):
    try:
        results[name] = f"ok  {fn()}"
    except Exception as exc:
        results[name] = f"FAIL  {exc.__class__.__name__}: {exc}"
    print(f"  {name:22} {results[name][:90]}")

wine = rpm.datasets.wine()
check("loc_scale_m", lambda: round(float(rpm.loc_scale_m(mineral["zinc"].to_numpy()).mu), 4))
check("m_scale", lambda: round(float(rpm.m_scale(mineral["zinc"].to_numpy())), 4))
check("lmrob_m", lambda: rpm.lmrob_m("zinc ~ copper", data=mineral).coefficients.round(4).tolist())
check("lmrobdet_dcml", lambda: rpm.lmrobdet_dcml("zinc ~ copper", data=mineral).coefficients.round(4).tolist())
check("cov_classic", lambda: rpm.cov_classic(wine).cov.shape)
check("cov_rob_mm", lambda: rpm.cov_rob_mm(wine).cov.shape)
check("prcomp_rob", lambda: rpm.prcomp_rob(wine).sdev.shape)
check("summary()", lambda: type(fit.summary()).__name__)
check("predict()", lambda: np.asarray(fit.predict(mineral)).shape)
check("resid()/sigma()", lambda: round(fit.sigma(), 4))

REPORT["surface"] = results
record("surface failures", sum(1 for v in results.values() if v.startswith("FAIL")))
''')

md("""
## 7 - Column names, both spellings

`datasets.shock()` shows a column called `n_shocks`; the book calls it
`n.shocks`. Both must work and agree, the underscored spelling used to fail
with R's `object 'n_shocks' not found`.
""")

code('''
shock = rpm.datasets.shock()
print("columns as you see them:", list(shock.columns))

py = rpm.lmrob_m("time ~ n_shocks", data=shock).coefficients
r_ = rpm.lmrob_m("time ~ n.shocks", data=shock).coefficients
same = np.array_equal(py, r_)
record("both spellings agree", same)
print(" ", py.round(6).tolist())
assert same
''')

md("""
## 8 - Run one of the book's example scripts

The clone includes a Python port of every RobStatTM example script. Running one
end to end exercises far more than the calls above.
""")

code('''
example = subprocess.run(
    [sys.executable, "/content/robstattm-py/examples/ch05_mineral_lmrobdet_mm.py"],
    capture_output=True, text=True, timeout=900,
)
print(example.stdout[-2500:])
if example.returncode != 0:
    print("--- stderr ---")
    print(example.stderr[-2500:])
record("example exit code", example.returncode)
''')

md("""
## 9 - Report

Everything above, in one block. **If anything failed, paste this into an issue.**
""")

code('''
import json

failures = [
    k for k, v in REPORT.items()
    if (k.endswith("exit code") and v != 0)
    or (isinstance(v, bool) and k in {"doctor READY", "matches R", "both spellings agree"} and not v)
    or (k == "surface failures" and v)
]

print("=" * 68)
print("PASSED, everything worked" if not failures else f"FAILED: {failures}")
print("=" * 68)
print(json.dumps(
    {k: v for k, v in REPORT.items() if k not in {"doctor", "setup tail", "surface"}},
    indent=2, default=str,
))
print("\\n--- surface ---")
for k, v in REPORT.get("surface", {}).items():
    print(f"  {k:22} {v[:100]}")
if failures:
    print("\\n--- doctor ---\\n", REPORT.get("doctor", "")[-2000:])
    print("\\n--- setup tail ---\\n", REPORT.get("setup tail", "")[-1200:])
''')


def build() -> dict:
    cells = []
    for kind, source in CELLS:
        lines = source.splitlines(keepends=True)
        if kind == "markdown":
            cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
        else:
            cells.append({
                "cell_type": "code", "metadata": {}, "source": lines,
                "execution_count": None, "outputs": [],
            })
    return {
        "cells": cells,
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("colab_smoke_test.ipynb")
    out.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}  ({len(CELLS)} cells)")
