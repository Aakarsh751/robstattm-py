"""Generate notebooks/testing_walkthrough.ipynb — interactive test tour.

Run:  python notebooks/_build_testing_notebook.py
"""
from __future__ import annotations

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT = "notebooks/testing_walkthrough.ipynb"

BOOTSTRAP = r'''import os, sys, warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Windows R_HOME (skip if already set)
if sys.platform == "win32" and "R_HOME" not in os.environ:
    os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
    os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]

import numpy as np
import pandas as pd
from IPython.display import Markdown, display

import robstattm_py as rpm
from robstattm_py import set_seed
from robstattm_py._r import r as _r_bridge

ro = _r_bridge()
ro.r("suppressMessages(library(RobStatTM))")

print(f"robstattm_py {rpm.__version__}  |  R session ready: {rpm.r_started()}")'''

HELPERS = r'''# --- shared test helpers (strict tier: atol=0, rtol=0 vs direct R) ---
PASS, FAIL = 0, 0
LOG: list[str] = []

def _ok(label: str, detail: str = "") -> None:
    global PASS
    PASS += 1
    msg = f"  PASS  {label}" + (f"  ({detail})" if detail else "")
    LOG.append(msg)
    print(msg)

def _fail(label: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    msg = f"  FAIL  {label}" + (f"  ({detail})" if detail else "")
    LOG.append(msg)
    print(msg)

def check(label: str, cond: bool, detail: str = "") -> None:
    (_ok if cond else _fail)(label, detail)

def parity_array(py, r_expr: str, label: str) -> None:
    r_val = np.asarray(ro.r(r_expr), dtype=float)
    py_a = np.asarray(py, dtype=float)
    try:
        np.testing.assert_array_equal(py_a, r_val)
        _ok(label, f"shape={py_a.shape}")
    except AssertionError as e:
        _fail(label, str(e)[:120])

def parity_scalar(py, r_expr: str, label: str) -> None:
    r_val = float(np.asarray(ro.r(r_expr), dtype=float).ravel()[0])
    py_v = float(np.asarray(py, dtype=float).ravel()[0])
    if (np.isnan(py_v) and np.isnan(r_val)) or py_v == r_val:
        _ok(label, f"value={py_v}")
    else:
        _fail(label, f"py={py_v} r={r_val}")

def section(title: str) -> None:
    display(Markdown(f"### {title}"))
    print("=" * 60)'''

SETUP = r'''section("Setup & utilities")
display(Markdown("Environment diagnostics, seeds, help, and control objects."))

# check_setup
core_ok = rpm.check_setup(verbose=True)
check("check_setup() core packages", core_ok)

# r_started flips after first R touch
check("r_started()", rpm.r_started())

# set_seed — reset R RNG and draw twice; must match
set_seed(20260617)
a = np.asarray(ro.r("rnorm(5)"), dtype=float)
set_seed(20260617)
b = np.asarray(ro.r("rnorm(5)"), dtype=float)
check("set_seed R reproducibility", np.array_equal(a, b), f"draw1={a.round(4)}")

# list_names / help smoke
names = rpm.list_names()
check("list_names() non-empty", len(names) > 20, f"{len(names)} entries")
import io
from contextlib import redirect_stdout
_hbuf = io.StringIO()
with redirect_stdout(_hbuf):
    rpm.help("lmrobdetMM")
check("help('lmrobdetMM') mentions Python name", "lmrobdet_mm" in _hbuf.getvalue())

# control objects
ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
check("lmrobdet_control fields", ctrl.bb == 0.5 and ctrl.family == "bisquare")
ctrl_m = rpm.lmrobm_control(family="huber", efficiency=0.90)
check("lmrobm_control", ctrl_m.family == "huber")

# datasets API
avail = rpm.datasets.available()
check("datasets.available() == 20", len(avail) == 20)

try:
    coleman = rpm.datasets.load("robustbase", "coleman")
    check("datasets.load('robustbase','coleman')", coleman.shape[0] == 20)
except Exception as e:
    _fail("datasets.load cross-package", str(e)[:80])

print(f"\nSetup block: {PASS} passed, {FAIL} failed so far")'''

DATASETS = r'''section("All 20 RobStatTM datasets")
display(Markdown(
    "Each loader returns a **pandas DataFrame**. "
    "R column names (with dots) become Python underscores; originals live in "
    "`df.attrs['r_columns']`."
))

for name in sorted(rpm.datasets.available()):
    loader = getattr(rpm.datasets, name)
    df = loader()
    info = rpm.datasets.info(name)
    display(Markdown(f"**`datasets.{name}()`** — {info}"))
    display(df.head(min(5, len(df))))
    # shape sanity vs catalog
    check(f"load {name}", df.shape[0] > 0 and df.shape[1] > 0, f"shape={df.shape}")
    if hasattr(df, "attrs") and "r_columns" in df.attrs:
        check(f"{name} r_columns metadata", len(df.attrs["r_columns"]) == df.shape[1])

print(f"\nDatasets block cumulative: {PASS} passed, {FAIL} failed")'''

PSI = r'''section("ψ / loss families (all 6)")
display(Markdown(
    "RobStatTM defines **bisquare**, **huber**, **mopt**, **opt**, **moptv0**, **optv0**. "
    "For each: tuning constant(s) at efficiency 0.95, then ρ, ρ′, ρ″ on a grid."
))

U_GRID = np.array([-3., -2., -1., -0.5, 0., 0.5, 1., 2., 3.])
SCALAR_FAMS = ["bisquare", "huber"]
VECTOR_FAMS = ["mopt", "opt", "moptv0", "optv0"]
ALL_FAMS = SCALAR_FAMS + VECTOR_FAMS
E = 0.95

ro.globalenv["u_test"] = U_GRID

for fam in ALL_FAMS:
    display(Markdown(f"#### family `{fam}` @ efficiency={E}"))
    cc = getattr(rpm.psi, fam)(E)
    if fam in SCALAR_FAMS:
        parity_scalar(cc, f"RobStatTM::{fam}({E})", f"{fam} tuning cc")
    else:
        parity_array(np.asarray(cc), f"RobStatTM::{fam}({E})", f"{fam} tuning cc vector")
    ro.globalenv["cc_test"] = np.atleast_1d(np.asarray(cc, dtype=float))
    parity_array(
        rpm.psi.rho(U_GRID, family=fam, cc=cc),
        f'RobStatTM::rho(u_test, family="{fam}", cc=cc_test)',
        f"{fam} rho",
    )
    parity_array(
        rpm.psi.rhoprime(U_GRID, family=fam, cc=cc),
        f'RobStatTM::rhoprime(u_test, family="{fam}", cc=cc_test)',
        f"{fam} rhoprime",
    )
    parity_array(
        rpm.psi.rhoprime2(U_GRID, family=fam, cc=cc),
        f'RobStatTM::rhoprime2(u_test, family="{fam}", cc=cc_test)',
        f"{fam} rhoprime2",
    )

print(f"\nPsi block cumulative: {PASS} passed, {FAIL} failed")'''

UNIVARIATE = r'''section("Univariate — loc_scale_m & m_scale")
display(Markdown("Run each **loss family** on `flour` (1-D) and compare to R."))

flour = rpm.datasets.flour()
x = flour.iloc[:, 0].to_numpy(dtype=float)
ro.globalenv["x_flour"] = x

for psi in ["bisquare", "huber", "mopt"]:
    for eff in [0.90, 0.95]:
        py = rpm.loc_scale_m(x, psi=psi, eff=eff)
        ro.r(f'r_fit <- locScaleM(x_flour, psi="{psi}", eff={eff})')
        parity_scalar(py.mu, "r_fit$mu", f"loc_scale_m mu {psi} e={eff}")
        parity_scalar(py.disper, "r_fit$disper", f"loc_scale_m disper {psi} e={eff}")

# m_scale on a short vector
y = np.array([1., 2., 2.5, 3., 100.], dtype=float)
ro.globalenv["y_ms"] = y
for fam in ["bisquare", "mopt"]:
    py_s = rpm.m_scale(y, family=fam, delta=0.5)
    ro.r(f'r_s <- scaleM(y_ms, family="{fam}", delta=0.5)')
    parity_scalar(py_s, "r_s", f"m_scale {fam}")

print(f"\nUnivariate block cumulative: {PASS} passed, {FAIL} failed")'''

REGRESSION = r'''section("Regression wrappers")
ro.r("data(mineral); data(stackloss)")
mineral = rpm.datasets.mineral()
stackloss = rpm.datasets.stackloss()

# --- lmrobdet_mm (default + custom control) ---
set_seed(42)
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
set_seed(42)
ro.r("set.seed(42); r_mm <- lmrobdetMM(zinc ~ copper, data=mineral)")
parity_array(fit.coefficients, "coef(r_mm)", "lmrobdet_mm coef (default)")
parity_scalar(fit.scale, "r_mm$scale", "lmrobdet_mm scale")

ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
fit_c = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=ctrl)
ro.r('cont <- lmrobdet.control(bb=0.5, efficiency=0.85, family="bisquare")')
ro.r("r_mm_c <- lmrobdetMM(zinc ~ copper, data=mineral, control=cont)")
parity_array(fit_c.coefficients, "coef(r_mm_c)", "lmrobdet_mm custom control")

# S3 methods
parity_array(fit.summary().coefficients_table.to_numpy(), "summary(r_mm)$coefficients", "summary() table")
pred = fit.predict(mineral.iloc[:3])
ro.r("r_pred <- predict(r_mm, newdata=mineral[1:3,])")
parity_array(pred, "r_pred", "predict() newdata")
parity_array(fit.hatvalues(), "hatvalues(r_mm)", "hatvalues()")
parity_scalar(fit.rfpe(), "lmrobdetMM.RFPE(r_mm)", "rfpe()")

# --- lmrobdet_dcml ---
dcml = rpm.lmrobdet_dcml("zinc ~ copper", data=mineral)
ro.r("r_dcml <- lmrobdetDCML(zinc ~ copper, data=mineral)")
parity_array(dcml.coefficients, "coef(r_dcml)", "lmrobdet_dcml")

# --- lmrob_m ---
lm = rpm.lmrob_m("zinc ~ copper", data=mineral, family="bisquare", efficiency=0.85)
ro.r("r_lm <- lmrobM(zinc ~ copper, data=mineral, "
     "control=lmrobM.control(family='bisquare', efficiency=0.85))")
parity_array(lm.coefficients, "coef(r_lm)", "lmrob_m")

# --- step_lmrobdet on stackloss ---
full = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=stackloss, control=ctrl)
step = rpm.step_lmrobdet(full)
ro.r('cont2 <- lmrobdet.control(bb=0.5, efficiency=0.85, family="bisquare")')
ro.r("r_full <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., data=stackloss, control=cont2)")
ro.r("r_step <- step.lmrobdetMM(r_full, trace=FALSE)")
parity_array(step.coefficients, "coef(r_step)", "step_lmrobdet coef")
parity_array(step.anova_rfpe, "r_step$anova$RFPE", "step_lmrobdet RFPE")

# --- drop1 ---
d1 = fit.drop1()
ro.r("r_d1 <- drop1(r_mm, trace=FALSE)")
parity_array(d1.rfpe, "r_d1$RFPE", "drop1 RFPE")

# --- pyinit (external pyinit package) ---
try:
    ro.r("library(pyinit)")
    set_seed(42)
    X_pi = mineral[["copper"]].to_numpy(dtype=float)
    y_pi = mineral["zinc"].to_numpy(dtype=float)
    pinit = rpm.pyinit(X_pi, y_pi)
    set_seed(42)
    ro.r("X_pi <- as.matrix(mineral['copper']); y_pi <- mineral$zinc")
    ro.r("set.seed(42); r_pi <- pyinit::pyinit(x=X_pi, y=y_pi, cc=1.5476, psc_keep=0.5, "
         "resid_keep_prop=0.2, resid_keep_thresh=2)")
    parity_array(pinit.coefficients, "r_pi$coefficients", "pyinit coefficients")
except Exception as e:
    print(f"  SKIP  pyinit — {e}")

# --- rob_linear_test (needs two nested models) ---
set_seed(42)
fit_full = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
fit_null = rpm.lmrobdet_mm("zinc ~ 1", data=mineral)
set_seed(42)
ro.r("set.seed(42); ff <- lmrobdetMM(zinc ~ copper, data=mineral); rr <- lmrobdetMM(zinc ~ 1, data=mineral)")
rlt = rpm.rob_linear_test(fit_full, fit_null)
ro.r("r_rlt <- rob.linear.test(ff, rr)")
parity_scalar(rlt.test, "r_rlt$test", "rob_linear_test")

# --- invtr2 ---
cc = rpm.psi.bisquare(0.95)
py_inv = rpm.invtr2(0.5, "bisquare", cc)
ro.r("cc_b <- bisquare(0.95); r_inv <- INVTR2(0.5, 'bisquare', cc_b)")
parity_scalar(py_inv, "r_inv", "invtr2")

print(f"\nRegression block cumulative: {PASS} passed, {FAIL} failed")'''

COV_PCA = r'''section("Covariance & PCA")
wine = rpm.datasets.wine()
X = wine.to_numpy(dtype=float)
ro.globalenv["wine_mat"] = X

# cov_classic
cc = rpm.cov_classic(X)
ro.r("r_cc <- covClassic(wine_mat)")
parity_array(cc.center, "r_cc$center", "cov_classic center")
parity_array(cc.cov, "r_cc$cov", "cov_classic cov")

# cov_rob_mm (stochastic — seed both sides)
set_seed(11)
cmm = rpm.cov_rob_mm(X)
set_seed(11)
ro.r("set.seed(11); r_cmm <- covRobMM(wine_mat)")
parity_array(cmm.center, "r_cmm$center", "cov_rob_mm center")
parity_array(cmm.cov, "r_cmm$cov", "cov_rob_mm cov")

# cov_rob dispatcher
set_seed(11)
cauto = rpm.cov_rob(X)
set_seed(11)
ro.r("set.seed(11); r_ca <- covRob(wine_mat)")
parity_array(cauto.center, "r_ca$center", "cov_rob center")
parity_array(cauto.cov, "r_ca$cov", "cov_rob cov")
check("cov_rob type inferred", cauto.estimator_type in ("MM", "Rocke"), cauto.estimator_type)

# fastmve + kurt_sd_new
set_seed(11)
fm = rpm.fastmve(X)
set_seed(11)
ro.r("set.seed(11); r_fm <- fastmve(wine_mat)")
parity_array(fm.center, "r_fm$center", "fastmve center")

set_seed(11)
ks = rpm.kurt_sd_new(X)
set_seed(11)
ro.r("set.seed(11); r_ks <- KurtSDNew(wine_mat)")
parity_array(ks.center, "r_ks$center", "kurt_sd_new center")

# PCA
set_seed(11)
pc = rpm.prcomp_rob(X, rank=4)
set_seed(11)
ro.r("set.seed(11); r_pc <- prcompRob(wine_mat, rank=4)")
parity_array(pc.sdev, "r_pc$sdev", "prcomp_rob sdev")

set_seed(11)
ps = rpm.pca_rob_s(X, ncomp=3)
set_seed(11)
ro.r("set.seed(11); r_ps <- pcaRobS(wine_mat, ncomp=3)")
parity_array(ps.eigvec, "r_ps$eigvec", "pca_rob_s eigvec")

print(f"\nCov/PCA block cumulative: {PASS} passed, {FAIL} failed")'''

GLM = r'''section("GLM — robust logistic regression")
ro.r("data(skin)")
skin = rpm.datasets.skin()
X = skin[["logVOL", "logRATE"]].to_numpy(dtype=float)
y = skin["vasoconst"].to_numpy(dtype=float)
ro.r("X_skin <- as.matrix(skin[, c('logVOL','logRATE')]); y_skin <- skin$vasoconst")

by = rpm.by_logreg(X, y)
ro.r("r_by <- BYlogreg(X_skin, y_skin)")
parity_array(by.coefficients, "r_by$coefficients", "by_logreg coef")

wby = rpm.wby_logreg(X, y)
ro.r("r_wby <- WBYlogreg(X_skin, y_skin)")
parity_array(wby.coefficients, "r_wby$coefficients", "wby_logreg coef")

wml = rpm.wml_logreg(X, y)
ro.r("r_wml <- WMLlogreg(X_skin, y_skin)")
parity_array(wml.coefficients, "r_wml$coefficients", "wml_logreg coef")

print(f"\nGLM block cumulative: {PASS} passed, {FAIL} failed")'''

EXTERNAL = r'''section("External stretch packages (optional)")
display(Markdown("Skip gracefully if `pense` / `GSE` are not installed."))

import numpy as np
rng = np.random.default_rng(7)
n, p = 60, 6
X = rng.normal(size=(n, p))
beta = np.array([1., 1., 1., 0., 0., 0.])
y = X @ beta + rng.normal(size=n)
y[:6] += 20
df_p = pd.DataFrame(np.column_stack([y, X]), columns=["y"] + [f"x{i}" for i in range(p)])

try:
    pen = rpm.pense(df_p.iloc[:, 1:].to_numpy(), df_p["y"].to_numpy(), alpha=1.0)
    check("pense() runs", pen.coefficients.shape[0] == p + 1)
    _ok("pense optional", f"lambda path len={len(pen.lambda_path)}")
except Exception as e:
    print(f"  SKIP  pense — {e}")

try:
    wine = rpm.datasets.wine().to_numpy(dtype=float)
    g = rpm.gse(wine)
    check("gse() runs", g.cov.shape[0] == wine.shape[1])
    _ok("gse optional", f"mu shape={g.mu.shape}")
except Exception as e:
    print(f"  SKIP  gse — {e}")

print(f"\nExternal block cumulative: {PASS} passed, {FAIL} failed")'''

SUMMARY = r'''section("Final summary")
display(Markdown(
    f"**Total: {PASS} passed, {FAIL} failed.** "
    "Strict tier — every parity check uses `np.testing.assert_array_equal` "
    "(atol=0, rtol=0) against direct R."
))
if FAIL:
    display(Markdown("### Failed checks"))
    for line in LOG:
        if line.startswith("  FAIL"):
            print(line)
else:
    display(Markdown("All automated checks in this notebook **passed**."))'''

TITLE = """# RobStatTM-Py — interactive testing walkthrough

This notebook is a **guided tour of the test suite**: it loads every shipped dataset,
exercises setup utilities, then runs **strict R-parity checks** (`atol=0`, `rtol=0`)
for each wrapper family and each ψ / loss family.

**How to read it**
- Green-path cells print `PASS` / `FAIL` lines (not pytest — interactive diagnostics).
- Each numeric check compares Python output to a **live direct R call** via rpy2.
- Run top-to-bottom; first cell sets up R on Windows if needed.

**Related:** `docs/testing_guide.md`, `pytest tests/`, `pytest exploration/`.
"""


def main() -> None:
    cells = [
        new_markdown_cell(TITLE),
        new_code_cell(BOOTSTRAP),
        new_markdown_cell("## 0 — Test helpers"),
        new_code_cell(HELPERS),
        new_markdown_cell("## 1 — Setup & utilities"),
        new_code_cell(SETUP),
        new_markdown_cell("## 2 — All datasets (load + display)"),
        new_code_cell(DATASETS),
        new_markdown_cell("## 3 — ψ / loss families (all six)"),
        new_code_cell(PSI),
        new_markdown_cell("## 4 — Univariate estimators"),
        new_code_cell(UNIVARIATE),
        new_markdown_cell("## 5 — Regression"),
        new_code_cell(REGRESSION),
        new_markdown_cell("## 6 — Covariance & PCA"),
        new_code_cell(COV_PCA),
        new_markdown_cell("## 7 — GLM (logistic)"),
        new_code_cell(GLM),
        new_markdown_cell("## 8 — External packages (optional)"),
        new_code_cell(EXTERNAL),
        new_markdown_cell("## 9 — Summary"),
        new_code_cell(SUMMARY),
    ]
    nb = new_notebook(cells=cells)
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"wrote {OUT} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
