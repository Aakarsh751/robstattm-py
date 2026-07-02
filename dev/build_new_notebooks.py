"""Build/extend the D-024 example-script notebooks (ch8 TS, ch6 autism, ch7 epilepsy).

Run from the repo root:  python dev/build_new_notebooks.py
"""
import pathlib

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = pathlib.Path(__file__).resolve().parent.parent
GALLERY = ROOT / "notebooks" / "gallery"

BOOT = '''import os, sys, pathlib

# Windows R_HOME setup (skip if already configured)
if sys.platform == "win32" and "R_HOME" not in os.environ:
    os.environ["R_HOME"] = r"C:\\Program Files\\R\\R-4.5.2"
    os.environ["PATH"] = r"C:\\Program Files\\R\\R-4.5.2\\bin\\x64;" + os.environ["PATH"]

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless-safe for CI execution
import matplotlib.pyplot as plt
import robstatm_py as rpm
from robstatm_py import set_seed
from robstatm_py._r import r as _r

ro = _r()
ro.r("suppressMessages(library(RobStatTM))")
ro.r("suppressMessages(library(robustarima))")
FIG_DIR = pathlib.Path("figures"); FIG_DIR.mkdir(exist_ok=True)
print(f"robstatm_py {rpm.__version__}")'''

KSPEC = {"display_name": "Python 3", "language": "python", "name": "python3"}


def write(nb, path):
    nb["metadata"]["kernelspec"] = KSPEC
    nb["metadata"]["language_info"] = {"name": "python"}
    nbf.write(nb, str(path))
    print("wrote", path)


# ---------------------------------------------------------------------------
# ch8_timeseries.ipynb  (resex, ar3, identAR2, identMA1, MA1-AO, ar1)
# ---------------------------------------------------------------------------
def build_ch8():
    cells = [
        new_markdown_cell(
            "# Chapter 8 gallery — robust ARIMA (`arima_rob`)\n\n"
            "Reproduces the six Chapter-8 time-series scripts via "
            "`rpm.arima_rob` → `robustarima::arima.rob` (the *filtered "
            "tau-estimate*):\n\n"
            "| Script | Example | Call |\n|---|---|---|\n"
            "| `resex.R` | 8.6 | `arima.rob(resex~1, p=2, sd=1, sfreq=12)` |\n"
            "| `ar3.R` | Table 8.1 | `arima.rob(ar3~1, p=3)` |\n"
            "| `identAR2.R` | 8.3 | `arima.rob(y~1, auto.ar=TRUE)` |\n"
            "| `identMA1.R` | 8.4 | `arima.rob(y~1, auto.ar=TRUE)` |\n"
            "| `MA1-AO.R` | 8.5 | `arima.rob(mac~1, q=1)` |\n"
            "| `ar1.R` | 8.6 (fig) | simulation/plot only |\n\n"
            "`arima.rob` is **deterministic** given its input series; the "
            "scripts seed `arima.sim` upstream. All numeric claims are checked "
            "**strict-tier** (`atol=0, rtol=0`) against direct R."
        ),
        new_code_cell(BOOT),
        # --- resex ---
        new_markdown_cell(
            "## RESEX — robust seasonal ARIMA (Example 8.6, Figs 8.12–8.13, Table 8.5)"
        ),
        new_code_cell(
            'resex = rpm.datasets.resex()["resex"].to_numpy()\n'
            'fit = rpm.arima_rob(y=resex, p=2, sd=1, sfreq=12)\n'
            'print("AR coefficients:", dict(zip(fit.ar_names, np.round(fit.ar, 6))))\n'
            'print("mean (regcoef):  ", np.round(fit.regcoef, 6))\n'
            'intercept = fit.regcoef * (1 - fit.ar.sum())\n'
            'print("intercept:       ", np.round(intercept, 6))\n\n'
            '# strict-tier check vs direct R\n'
            'ro.r("data(resex, package=\'RobStatTM\'); rref <- arima.rob(resex~1, p=2, sd=1, sfreq=12)")\n'
            'assert np.array_equal(fit.ar, np.asarray(ro.r("as.numeric(rref$model$ar)"), float))\n'
            'assert np.array_equal(fit.regcoef, np.asarray(ro.r("as.numeric(rref$regcoef)"), float))\n'
            'assert np.array_equal(fit.y_robust, np.asarray(ro.r("as.numeric(rref$y.robust)"), float))\n'
            'print("strict-tier vs R: OK")'
        ),
        new_code_cell(
            '# Figure 8.12 analogue: observed series + robustly cleaned series\n'
            'fig, ax = plt.subplots(figsize=(7, 4))\n'
            'ax.plot(np.arange(1, 90), resex, "-", color="0.5", label="RESEX")\n'
            'ax.plot(np.arange(1, 90), fit.y_robust, "o", ms=3, label="y.robust")\n'
            'ax.set_xlabel("index"); ax.set_ylabel("RESEX"); ax.legend()\n'
            'ax.set_title("RESEX — observed vs robustly cleaned")\n'
            'fig.savefig(FIG_DIR / "ch8_resex.png", dpi=110, bbox_inches="tight"); plt.close(fig)\n'
            '# Figure 8.13 analogue: sorted |innovations| (TAU) vs LS\n'
            'innov_tau = np.sort(np.abs(fit.innov[14:89]))\n'
            'fig, ax = plt.subplots(figsize=(6, 4))\n'
            'ax.plot((np.arange(1, 73)-0.5)/72, innov_tau[:72], "-", label="TAU")\n'
            'ax.set_xlabel("probability"); ax.set_ylabel("quantiles"); ax.legend()\n'
            'ax.set_title("RESEX — sorted |innovations| (TAU)")\n'
            'fig.savefig(FIG_DIR / "ch8_resex_innov.png", dpi=110, bbox_inches="tight"); plt.close(fig)\n'
            'print("figures saved")'
        ),
        # --- ar3 ---
        new_markdown_cell(
            "## AR(3) — robust vs LS/MM comparison (Table 8.1)\n\n"
            "Simulated AR(3) (`set.seed(600)`), true φ = (4/3, −5/6, 1/6). We "
            "reproduce the seeded series in R, then fit `arima.rob(., p=3)` and "
            "compare to `lm` / `lmrobdetMM` (already wrapped)."
        ),
        new_code_cell(
            'ro.r("set.seed(600); n.innov<-300; n<-200; phi<-c(4/3,-5/6,1/6); '
            'innov<-rnorm(n.innov); ar3<-arima.sim(model=list(ar=phi), n, innov=innov, n.start=n.innov-n)")\n'
            'ar3 = np.asarray(ro.r("as.numeric(ar3)"), float)\n'
            'fit3 = rpm.arima_rob(y=ar3, p=3)\n'
            'ro.r("rref3 <- arima.rob(ar3~1, p=3)")\n'
            'assert np.array_equal(fit3.ar, np.asarray(ro.r("as.numeric(rref3$model$ar)"), float))\n'
            'print("AR(3) tau coefficients:", np.round(fit3.ar, 5), "  (true:", [round(4/3,3), round(-5/6,3), round(1/6,3)], ")")\n'
            '# MM comparator (already wrapped): regress ar3[4:200] on its lags\n'
            'set_seed(1)\n'
            'X = np.column_stack([ar3[2:199], ar3[1:198], ar3[0:197]])\n'
            'mm = rpm.lmrobdet_mm("y ~ x1 + x2 + x3", data=pd.DataFrame({"y": ar3[3:200], "x1": X[:,0], "x2": X[:,1], "x3": X[:,2]}))\n'
            'print("MM slope coefficients:", np.round(mm.coefficients[1:], 5))'
        ),
        # --- identAR2 / identMA1 ---
        new_markdown_cell(
            "## Automatic AR identification (Examples 8.3 / 8.4)\n\n"
            "`arima.rob(y~1, auto.ar=TRUE)` selects the AR order on an outlier-"
            "contaminated AR(2) (`identAR2`) and MA(1) (`identMA1`) series. A "
            "benign non-convergence warning may appear; the numbers still match R."
        ),
        new_code_cell(
            'import warnings\n'
            'ro.r("set.seed(700); n.innov<-300; n<-200; phi<-c(4/3,-5/6); innov<-rnorm(n.innov); '
            'x<-arima.sim(model=list(ar=phi), n, innov=innov, n.start=n.innov-n); '
            'ao<-ifelse(runif(n)>.1,0,rnorm(n,4,1)); ao<-sign(runif(n,-1,1))*ao; y<-x+ao")\n'
            'y2 = np.asarray(ro.r("as.numeric(y)"), float)\n'
            'with warnings.catch_warnings():\n'
            '    warnings.simplefilter("ignore")\n'
            '    fa = rpm.arima_rob(y=y2, auto_ar=True)\n'
            'ro.r("rrefA <- suppressWarnings(arima.rob(y~1, auto.ar=TRUE))")\n'
            'assert np.array_equal(fa.ar, np.asarray(ro.r("as.numeric(rrefA$model$ar)"), float))\n'
            'print(f"identAR2: selected AR order = {fa.ar.shape[0]}")\n'
            'print("AR coefficients:", np.round(fa.ar, 4))'
        ),
        new_code_cell(
            'ro.r("set.seed(600); n.innov<-300; n<-200; theta<-0.8; innov<-rnorm(n.innov); '
            'x<-arima.sim(model=list(ma=theta), n, innov=innov, n.start=n.innov-n); '
            'ao<-ifelse(runif(n)>.1,0,rnorm(n,6,1)); ao<-sign(runif(n,-1,1))*ao; y<-x+ao")\n'
            'ym = np.asarray(ro.r("as.numeric(y)"), float)\n'
            'with warnings.catch_warnings():\n'
            '    warnings.simplefilter("ignore")\n'
            '    fm = rpm.arima_rob(y=ym, auto_ar=True)\n'
            'ro.r("rrefM <- suppressWarnings(arima.rob(y~1, auto.ar=TRUE))")\n'
            'assert np.array_equal(fm.ar, np.asarray(ro.r("as.numeric(rrefM$model$ar)"), float))\n'
            'print(f"identMA1: selected AR order = {fm.ar.shape[0]}")'
        ),
        # --- MA1-AO ---
        new_markdown_cell(
            "## MA(1) with additive outliers (Example 8.5, Fig 8.11, Table 8.4)"
        ),
        new_code_cell(
            'ro.r("set.seed(200); n.innov<-300; n<-200; theta<--0.8; innov<-rnorm(n.innov); '
            'ma1<-arima.sim(model=list(ma=theta), n=n, innov=innov, n.start=n.innov-n); '
            'mac<-ma1; mac[20*(1:10)]<-ma1[20*(1:10)]+4")\n'
            'mac = np.asarray(ro.r("as.numeric(mac)"), float)\n'
            'fma = rpm.arima_rob(y=mac, q=1)\n'
            'ro.r("rrefMA <- arima.rob(mac~1, q=1)")\n'
            'assert np.array_equal(fma.ma, np.asarray(ro.r("as.numeric(rrefMA$model$ma)"), float))\n'
            'assert np.array_equal(fma.y_robust, np.asarray(ro.r("as.numeric(rrefMA$y.robust)"), float))\n'
            'print("MA(1) coefficient:", dict(zip(fma.ma_names, np.round(fma.ma, 6))))\n'
            'fig, ax = plt.subplots(figsize=(7, 4))\n'
            'ax.plot(np.arange(1, 201), mac, "-", color="0.5", label="series (mac)")\n'
            'ax.plot(np.arange(1, 201), fma.y_robust, "-", lw=1.2, label="y.robust")\n'
            'ax.plot(np.arange(20, 201, 20), mac[np.arange(19, 200, 20)], "o", ms=4)\n'
            'ax.set_xlabel("index"); ax.set_ylabel("series"); ax.legend()\n'
            'ax.set_title("MA(1) with additive outliers — robust filtering (Fig 8.11)")\n'
            'fig.savefig(FIG_DIR / "ch8_ma1ao.png", dpi=110, bbox_inches="tight"); plt.close(fig)\n'
            'print("figure saved")'
        ),
        # --- ar1 simulation ---
        new_markdown_cell(
            "## AR(1) with AO and IO — simulation only (Fig 8.6)\n\n"
            "`ar1.R` loads `robustarima` but only *simulates* and plots — no "
            "`arima.rob` fit. We reproduce the three-panel figure."
        ),
        new_code_cell(
            'ro.r("set.seed(1000); n.innov<-200; n<-100; phi<-0.9; innov<-rnorm(n.innov); '
            'x<-arima.sim(model=list(ar=phi), n, innov=innov, n.start=n.innov-n); '
            'ao<-rep(0,n); tt<-seq(10,100,10); ao[tt]<-4; xAO<-x+ao; '
            'xIO<-x; xIO[50]<-phi*xIO[49]+10; u<-rnorm(50); '
            'for (i in 51:100) xIO[i]<-phi*xIO[i-1]+u[i-50]")\n'
            'x = np.asarray(ro.r("as.numeric(x)"), float)\n'
            'xAO = np.asarray(ro.r("as.numeric(xAO)"), float)\n'
            'xIO = np.asarray(ro.r("as.numeric(xIO)"), float)\n'
            'tt = np.arange(10, 101, 10)\n'
            'fig, axes = plt.subplots(3, 1, figsize=(7, 8), sharex=True)\n'
            'axes[0].plot(x); axes[0].set_title("Gaussian AR(1), no outliers")\n'
            'axes[1].plot(xAO); axes[1].plot(tt, xAO[tt-1], "o"); axes[1].set_title("AR(1) with 10% additive outliers")\n'
            'axes[2].plot(xIO); axes[2].plot(50, xIO[49], "o"); axes[2].set_title("AR(1) with one innovation outlier")\n'
            'fig.tight_layout(); fig.savefig(FIG_DIR / "ch8_ar1.png", dpi=110, bbox_inches="tight"); plt.close(fig)\n'
            'print("Fig 8.6 saved — all six Chapter-8 scripts reproduced.")'
        ),
    ]
    nb = new_notebook(cells=cells)
    write(nb, GALLERY / "ch8_timeseries.ipynb")


# ---------------------------------------------------------------------------
# ch6_autism.ipynb  (robust variance components)
# ---------------------------------------------------------------------------
AUTISM_PREP = '''ro.r("""
suppressMessages(library(robustvarComp))
data(autism, package='WWGbook')
autism <- autism[complete.cases(autism),]
completi <- table(autism$childid)==5
completi <- names(completi[completi])
indici <- as.vector(unlist(sapply(completi, function(x) which(autism$childid==x))))
ind <- rep(FALSE, nrow(autism)); ind[indici] <- TRUE
autism <- subset(autism, subset=ind)
sicdegp <- autism$sicdegp; age <- autism$age
age.2 <- age - 2
sicdegp2 <- sicdegp
sicdegp2[sicdegp == 3] <- 0; sicdegp2[sicdegp == 2] <- 2; sicdegp2[sicdegp == 1] <- 1
sicdegp2.f <- factor(sicdegp2)
autism.updated <- subset(data.frame(autism, sicdegp2.f, age.2), !is.na(vsae))
p <- 5; n <- 41
z1 <- rep(1, p); z2 <- c(0,1,3,7,11); z3 <- z2^2
K <- list(tcrossprod(z1,z1), tcrossprod(z2,z2), tcrossprod(z3,z3),
          tcrossprod(z1,z2)+tcrossprod(z2,z1), tcrossprod(z1,z3)+tcrossprod(z3,z1),
          tcrossprod(z3,z2)+tcrossprod(z2,z3))
names(K) <- c("Int","age","age2","Int:age","Int:age2","age:age2")
groups <- cbind(rep(1:p, each=n), rep((1:n), p))
""")

# Rebuild the prepared frame column-by-column (whole-frame auto-conversion is
# fragile); verified to give a bit-identical model matrix.
vsae = np.asarray(ro.r("as.numeric(autism.updated$vsae)"), float)
age2 = np.asarray(ro.r("as.numeric(autism.updated[[\\'age.2\\']])"), float)
codes = np.asarray(ro.r("as.integer(autism.updated[[\\'sicdegp2.f\\']])"), int) - 1
levels = [str(x) for x in ro.r("levels(autism.updated[[\\'sicdegp2.f\\']])")]
sic = pd.Categorical.from_codes(codes, categories=levels)
autism_df = pd.DataFrame({"vsae": vsae, "age.2": age2, "sicdegp2.f": sic})

# K kernels + groups matrix (exactly as autism.R)
p, n = 5, 41
z1 = np.ones(p); z2 = np.array([0.,1.,3.,7.,11.]); z3 = z2**2
K = [np.outer(z1,z1), np.outer(z2,z2), np.outer(z3,z3),
     np.outer(z1,z2)+np.outer(z2,z1), np.outer(z1,z3)+np.outer(z3,z1),
     np.outer(z3,z2)+np.outer(z2,z3)]
Knames = ("Int","age","age2","Int:age","Int:age2","age:age2")
groups = np.column_stack([np.repeat(np.arange(1,p+1), n), np.tile(np.arange(1,n+1), p)])
FIXED = "vsae ~ age.2 + I(age.2^2) + sicdegp2.f + age.2:sicdegp2.f + I(age.2^2):sicdegp2.f"
print(f"autism: {autism_df.shape[0]} obs, {p} time-points x {n} children")'''


def build_ch6_autism():
    cells = [
        new_markdown_cell(
            "# Chapter 6 — robust variance components (`var_comprob`)\n\n"
            "Reproduces `autism.R` (Example 6.7, Tables 6.8–6.9): a robust "
            "linear mixed / variance-component model for autism `vsae` growth "
            "across `childid` groups, via `rpm.var_comprob` → "
            "`robustvarComp::varComprob`.\n\n"
            "`varComprob` is **stochastic** (`lmrob.S` / `TSGS` initials), so we "
            "`set_seed` before each fit and check **strict-tier** against direct R."
        ),
        new_code_cell(BOOT.replace(
            'ro.r("suppressMessages(library(robustarima))")',
            'ro.r("suppressMessages(library(robustvarComp))")')),
        new_markdown_cell("## Data preparation (complete cases, 41 children × 5 time-points)"),
        new_code_cell(AUTISM_PREP),
        new_markdown_cell(
            "## Composite Tau estimator (Table 6.8)\n\n"
            "Default method (`compositeTau`, `psi='optimal'`) with the lower bounds "
            "the script uses."
        ),
        new_code_cell(
            'ctrl = rpm.var_comprob_control(lower=[0.01, 0.01, 0.01, -np.inf, -np.inf, -np.inf])\n'
            'set_seed(2468)\n'
            'ct = rpm.var_comprob(FIXED, autism_df, groups=groups, varcov=K, varcov_names=Knames, control=ctrl)\n'
            'print(ct)\n'
            'tau_table = pd.DataFrame({"coef": ct.beta, "SE": np.sqrt(np.diag(ct.vcov_beta))}, index=ct.beta_names)\n'
            'print("\\nFixed effects (Composite Tau):"); print(tau_table.round(4))\n'
            'print("\\nvariance components (eta):", dict(zip(ct.eta_names, np.round(ct.eta, 4))))\n'
            'print("error variance (sigma2):", round(ct.sigma2, 5))\n\n'
            '# strict-tier check vs direct R\n'
            'ro.r("ctrlR <- varComprob.control(lower=c(0.01,0.01,0.01,-Inf,-Inf,-Inf))")\n'
            'ro.r(f"set.seed(2468L); rCT <- varComprob({FIXED}, groups=groups, data=autism.updated, varcov=K, control=ctrlR)")\n'
            'assert np.array_equal(ct.beta, np.asarray(ro.r("as.numeric(rCT$beta)"), float))\n'
            'assert np.array_equal(ct.eta, np.asarray(ro.r("as.numeric(rCT$eta)"), float))\n'
            'assert ct.sigma2 == float(ro.r("as.numeric(rCT$sigma2)")[0])\n'
            'print("\\nstrict-tier vs R: OK")'
        ),
        new_markdown_cell(
            "## Classic S estimator (Table 6.9)\n\n"
            "`method='S'`, `psi='rocke'`, `cov.init='covOGK'`."
        ),
        new_code_cell(
            'ctrlS = rpm.var_comprob_control(method="S", psi="rocke", cov_init="covOGK",\n'
            '                                lower=[0.01, 0.01, 0.01, -np.inf, -np.inf, -np.inf])\n'
            'set_seed(2468)\n'
            'cs = rpm.var_comprob(FIXED, autism_df, groups=groups, varcov=K, varcov_names=Knames, control=ctrlS)\n'
            'print(cs)\n'
            's_table = pd.DataFrame({"coef": cs.beta, "SE": np.sqrt(np.diag(cs.vcov_beta))}, index=cs.beta_names)\n'
            'print("\\nFixed effects (Classic S):"); print(s_table.round(4))\n'
            'ro.r("ctrlSR <- varComprob.control(method=\'S\', psi=\'rocke\', cov.init=\'covOGK\', lower=c(0.01,0.01,0.01,-Inf,-Inf,-Inf))")\n'
            'ro.r(f"set.seed(2468L); rS <- varComprob({FIXED}, groups=groups, data=autism.updated, varcov=K, control=ctrlSR)")\n'
            'assert np.array_equal(cs.beta, np.asarray(ro.r("as.numeric(rS$beta)"), float))\n'
            'print("\\nstrict-tier vs R: OK — autism.R reproduced.")'
        ),
    ]
    nb = new_notebook(cells=cells)
    write(nb, GALLERY / "ch6_autism.ipynb")


# ---------------------------------------------------------------------------
# Extend ch7_glm.ipynb with the epilepsy section
# ---------------------------------------------------------------------------
def extend_ch7():
    path = GALLERY / "ch7_glm.ipynb"
    nb = nbf.read(str(path), as_version=4)
    new_cells = [
        new_markdown_cell(
            "## epilepsy — robust Poisson GLM (Example 7.3, Breslow data)\n\n"
            "`epilepsy.R` fits the seizure-count model with several robust "
            "estimators. We reproduce **RQL/Mqle** and **MT** "
            "(`robustbase::glmrob`) and **CUBIF** (`robcbi::cubinf`), plus the ML "
            "`glm` baseline. The MATLAB-only **MP** estimator (no R code) is shown "
            "as the book's documented constants. Comparators only "
            "(`quantreg`, `robust::glmRob`) are omitted."
        ),
        new_code_cell(
            'ro.r("suppressMessages(library(robustbase)); data(breslow.dat, package=\'robust\')")\n'
            'ro.r("yy<-breslow.dat[,10]; xx1<-breslow.dat[,11]; xx2<-breslow.dat[,12]; '
            'xx3<-breslow.dat[,8]==\'progabide\'; xx4<-xx2*xx3; '
            'XX<-cbind(rep(1,59),xx1,xx2,xx3,xx4); '
            'colnames(XX)<-c(\'intercept\',\'Age10\',\'Base4\',\'Progabide\',\'interac.Base4-Progabide\')")\n'
            'epi = pd.DataFrame({\n'
            '    "yy": np.asarray(ro.r("as.numeric(yy)"), float),\n'
            '    "xx1": np.asarray(ro.r("as.numeric(xx1)"), float),\n'
            '    "xx2": np.asarray(ro.r("as.numeric(xx2)"), float),\n'
            '    "xx3": np.asarray(ro.r("as.logical(xx3)"), bool),\n'
            '    "xx4": np.asarray(ro.r("as.numeric(xx4)"), float),\n'
            '})\n'
            'FORM = "yy ~ xx1 + xx2 + xx3 + xx4"\n'
            'print(epi.head())'
        ),
        new_code_cell(
            '# RQL / Mqle (deterministic) and MT (stochastic -> seed)\n'
            'rql = rpm.glmrob(FORM, epi, family="poisson")\n'
            'set_seed(11)\n'
            'mt = rpm.glmrob(FORM, epi, family="poisson", method="MT")\n'
            '# CUBIF on the explicit-intercept design\n'
            'XX = np.asarray(ro.r("XX"), float)\n'
            'yy = np.asarray(ro.r("as.numeric(yy)"), float)\n'
            'Xdf = pd.DataFrame(XX, columns=[str(c) for c in ro.r("colnames(XX)")])\n'
            'cub = rpm.cubinf(Xdf, yy, family="poisson", intercept=False, null_dev=False, ufact=1.1)\n'
            '# ML baseline via R glm (comparator; no new Python wrapper)\n'
            'ml_coef = np.asarray(ro.r("as.numeric(glm(yy~xx1+xx2+xx3+xx4, family=poisson)$coefficients)"), float)\n'
            '# MATLAB MP estimator: documented constants (no R/Python code exists)\n'
            'mp_coef = np.array([2.0078, 0.0707, 0.1346, -0.4898, 0.0476])\n\n'
            'table = pd.DataFrame({\n'
            '    "ML": ml_coef, "CUBIF": cub.coefficients, "MT": mt.coefficients,\n'
            '    "RQL": rql.coefficients, "MP(MATLAB)": mp_coef,\n'
            '}, index=["intercept","Age10","Base4","Progabide","Base4:Prog"])\n'
            'print("Table 7.3 — coefficient estimates:"); print(table.round(4))'
        ),
        new_code_cell(
            '# strict-tier checks vs direct R\n'
            'ro.r("rRQL <- glmrob(yy~xx1+xx2+xx3+xx4, family=poisson)")\n'
            'assert np.array_equal(rql.coefficients, np.asarray(ro.r("as.numeric(rRQL$coefficients)"), float))\n'
            'ro.r("set.seed(11L); rMT <- glmrob(yy~xx1+xx2+xx3+xx4, family=poisson, method=\'MT\')")\n'
            'assert np.array_equal(mt.coefficients, np.asarray(ro.r("as.numeric(rMT$coefficients)"), float))\n'
            'ro.r("rCUB <- robcbi::cubinf(XX, yy, family=poisson(), null.dev=FALSE, control=robcbi::cubinf.control(ufact=1.1))")\n'
            'assert np.array_equal(cub.coefficients, np.asarray(ro.r("as.numeric(rCUB$coefficients)"), float))\n'
            'print("strict-tier vs R (RQL, MT, CUBIF): OK")'
        ),
        new_code_cell(
            '# Figure 7.6 analogue: boxplots of absolute deviance residuals\n'
            'def dev_resid(y, fitted):\n'
            '    return np.sign(y - fitted) * np.sqrt(2*(y*np.log(np.maximum(y,1)) - y - y*np.log(fitted) + fitted))\n'
            'ml_fitted = np.asarray(ro.r("as.numeric(glm(yy~xx1+xx2+xx3+xx4, family=poisson)$fitted)"), float)\n'
            'mp_fitted = np.exp(XX @ mp_coef)\n'
            'devs = {"ML": dev_resid(yy, ml_fitted), "MT": dev_resid(yy, mt.fitted_values),\n'
            '        "QL": dev_resid(yy, rql.fitted_values), "MP": dev_resid(yy, mp_fitted)}\n'
            'fig, ax = plt.subplots(figsize=(6, 4))\n'
            'ax.boxplot([np.abs(v) for v in devs.values()], labels=list(devs.keys()))\n'
            'ax.set_ylabel("Absolute deviance residuals"); ax.set_title("epilepsy — robust GLM deviances (Fig 7.6)")\n'
            'fig.savefig(FIG_DIR / "ch7_epilepsy_dev.png", dpi=110, bbox_inches="tight"); plt.close(fig)\n'
            'print("Figure 7.6 saved — epilepsy.R reproduced.")'
        ),
    ]
    nb["cells"].extend(new_cells)
    nbf.write(nb, str(path))
    print("extended", path)


if __name__ == "__main__":
    build_ch8()
    build_ch6_autism()
    extend_ch7()
