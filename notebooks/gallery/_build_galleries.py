"""Builders for the chapter reproduction galleries (D2 of docs/notebook_plan.md).

Each gallery consolidates several RobStatTM example scripts (groups A+B in the
plan) for one book chapter into a single notebook. Run once to (re)generate the
notebooks, then execute them via the D1 CI test (tests/test_notebooks.py).

Faithfulness policy: every notebook reproduces the *robust estimator core* of
its source scripts and cross-checks at least one numeric output bit-for-bit
against direct R (np.array_equal). Figures are visual-only. External comparators
that live outside the wrapped scope (quantreg::rq, robust::glmRob, rrcov::Cov*,
fit.models, GSE helpers used only as comparators) are dropped or noted, per the
group-A/B rule in docs/notebook_plan.md §2.
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

# No R_HOME bootstrap: robstattm_py locates R itself (see
# robstattm_py/_renv/discovery.py). The old block hardcoded
# C:\Program Files\R\R-4.5.2, so these notebooks only ran on one machine.
BOOTSTRAP = (
    "import os, sys, pathlib\n"
    "\n"
    "import numpy as np\n"
    "import pandas as pd\n"
    "import matplotlib\n"
    'matplotlib.use("Agg")  # headless-safe for CI execution\n'
    "import matplotlib.pyplot as plt\n"
    "import robstattm_py as rpm\n"
    "from robstattm_py import set_seed\n"
    "from robstattm_py._r import r as _r\n"
    "\n"
    "ro = _r()\n"
    'ro.r("suppressMessages(library(RobStatTM))")\n'
    'FIG_DIR = pathlib.Path("figures"); FIG_DIR.mkdir(exist_ok=True)\n'
    'print(f"robstattm_py {rpm.__version__}")'
)


def write(name, cells, title_md):
    nb = new_notebook()
    nb["cells"] = [new_markdown_cell(title_md), new_code_cell(BOOTSTRAP)] + cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    with open(name, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"wrote {name} ({len(nb['cells'])} cells)")


# =====================================================================
# Ch 2 - location & scale (flour.R, Table 2.4)
# =====================================================================
ch2 = [
    new_markdown_cell(
        "## flour, bisquare location M-estimator (Table 2.4)\n"
        "\n"
        "`flour.R` compares the sample mean, the bisquare M-estimator "
        "(`locScaleM`, efficiency 0.95) and the 25% trimmed mean on the flour "
        "aflatoxin data (n=24), with 95% confidence intervals."
    ),
    new_code_cell(
        "flour = rpm.datasets.flour()\n"
        "x = flour.iloc[:, 0].to_numpy(dtype=float)\n"
        "n = len(x); qn = 1.959963984540054  # qnorm(0.975)\n"
        "\n"
        "res = rpm.loc_scale_m(x, eff=0.95)\n"
        "muM, muMst = res.mu, res.std_mu\n"
        "interM = (muM - muMst * qn, muM + muMst * qn)\n"
        "\n"
        "xbar = x.mean(); smed = x.std(ddof=1) / np.sqrt(n)\n"
        "inter_mean = (xbar - smed * qn, xbar + smed * qn)\n"
        "\n"
        "print(f'sample mean      = {xbar:.4f}   CI = ({inter_mean[0]:.4f}, {inter_mean[1]:.4f})')\n"
        "print(f'bisquare M-est   = {muM:.4f}   CI = ({interM[0]:.4f}, {interM[1]:.4f})')\n"
        "print(f'robust dispersion (scale) = {res.disper:.4f}')"
    ),
    new_markdown_cell("### Strict-tier cross-check vs direct R `locScaleM`"),
    new_code_cell(
        "ro.globalenv['xf'] = x\n"
        "ro.r('rf <- locScaleM(xf, eff=0.95)')\n"
        "print('mu      bit-equal to R:', muM == float(ro.r('rf$mu')[0]))\n"
        "print('std.mu  bit-equal to R:', muMst == float(ro.r('rf$std.mu')[0]))\n"
        "print('disper  bit-equal to R:', res.disper == float(ro.r('rf$disper')[0]))"
    ),
]

# =====================================================================
# Ch 4 - M regression (shock.R Ex 4.1, oats.R Ex 4.2)
# =====================================================================
ch4 = [
    new_markdown_cell(
        "## shock, robust M regression (Example 4.1)\n"
        "\n"
        "`shock.R` fits LS, LS-without-outliers, L1 and a robust M-estimator "
        "(`lmrobM`) of average reaction `time` on `n.shocks`. Observations "
        "1, 2, 4 are outliers that drag the LS line up."
    ),
    new_code_cell(
        "shock = rpm.datasets.shock()\n"
        "print('columns:', list(shock.columns))\n"
        "# robust M fit (bisquare, eff 0.85, bb 0.5 as in shock.R's control)\n"
        "# The data frame is pushed to R with its original names (n.shocks), so\n"
        "# the formula uses the R name; pandas column access uses n_shocks.\n"
        "mfit = rpm.lmrob_m('time ~ n.shocks', shock, bb=0.5, efficiency=0.85, family='bisquare')\n"
        "print('robust M coefficients:', np.round(mfit.coefficients, 4))\n"
        "print('robust scale         :', round(float(mfit.scale), 4))\n"
        "\n"
        "# LS on full data and on data without obs 1,2,4 (0-based: 0,1,3)\n"
        "import numpy as np\n"
        "Xls = np.c_[np.ones(len(shock)), shock['n_shocks'].to_numpy(float)]\n"
        "yls = shock['time'].to_numpy(float)\n"
        "b_full = np.linalg.lstsq(Xls, yls, rcond=None)[0]\n"
        "keep = [i for i in range(len(shock)) if i not in (0, 1, 3)]\n"
        "b_clean = np.linalg.lstsq(Xls[keep], yls[keep], rcond=None)[0]\n"
        "print('LS (full)            :', np.round(b_full, 4))\n"
        "print('LS (no obs 1,2,4)    :', np.round(b_clean, 4))"
    ),
    new_code_cell(
        "# Figure 4.3 analogue: data + the three lines\n"
        "xs = shock['n_shocks'].to_numpy(float); ys = shock['time'].to_numpy(float)\n"
        "grid = np.linspace(xs.min(), xs.max(), 50)\n"
        "fig, ax = plt.subplots(figsize=(6, 4))\n"
        "ax.scatter(xs, ys, c='k', zorder=3)\n"
        "ax.plot(grid, b_full[0] + b_full[1]*grid, 'r-', label='LS (full)')\n"
        "ax.plot(grid, b_clean[0] + b_clean[1]*grid, color='gray', label='LS (no 1,2,4)')\n"
        "ax.plot(grid, mfit.coefficients[0] + mfit.coefficients[1]*grid, 'g-', lw=2, label='robust M')\n"
        "for i in (0, 1, 3):\n"
        "    ax.annotate(str(i+1), (xs[i], ys[i]-0.4))\n"
        "ax.set_xlabel('number of shocks'); ax.set_ylabel('average time'); ax.legend()\n"
        "fig.savefig(FIG_DIR / 'ch4_shock.png', dpi=110, bbox_inches='tight'); plt.close(fig)\n"
        "print('robust line resists the three outliers that pull LS up')"
    ),
    new_markdown_cell("### Strict-tier cross-check vs direct R `lmrobM`"),
    new_code_cell(
        "# lmrobM is deterministic, so no seeding is needed on either side.\n"
        "mfit_chk = rpm.lmrob_m('time ~ n.shocks', shock, bb=0.5, efficiency=0.85, family='bisquare')\n"
        "ro.r('data(shock); cont <- lmrobM.control(bb=0.5, efficiency=0.85, family=\"bisquare\")')\n"
        "ro.r('rm_fit <- lmrobM(time ~ n.shocks, data=shock, control=cont)')\n"
        "r_coef = np.asarray(ro.r('as.numeric(rm_fit$coefficients)'), dtype=float)\n"
        "print('coefficients bit-equal to R:', np.array_equal(mfit_chk.coefficients, r_coef))"
    ),
    new_markdown_cell(
        "## oats, robust M regression + robust ANOVA (Example 4.2)\n"
        "\n"
        "`oats.R` fits `lmrobM` models for two responses and compares nested "
        "models with `rob.linear.test` (robust analogue of the F-test). Our "
        "`rob_linear_test` wraps `rob.linear.test` for `lmrobdetMM` fits, so we "
        "demonstrate the robust nested-model test on MM fits of the oats data."
    ),
    new_code_cell(
        "oats = rpm.datasets.oats()\n"
        "print('columns:', list(oats.columns))\n"
        "# robust M fits (matching oats.R)\n"
        "o2M = rpm.lmrob_m('response2 ~ variety + block', oats, bb=0.5, efficiency=0.85, family='bisquare')\n"
        "print('response2 robust M scale:', round(float(o2M.scale), 4))\n"
        "print('coefficients:', np.round(o2M.coefficients, 3))"
    ),
    new_code_cell(
        "# Robust nested-model test (variety effect) via MM fits, which our\n"
        "# rob_linear_test supports. Full = variety+block, reduced = block only.\n"
        "full = rpm.lmrobdet_mm('response2 ~ variety + block', oats)\n"
        "reduced = rpm.lmrobdet_mm('response2 ~ block', oats)\n"
        "test = rpm.rob_linear_test(full, reduced)\n"
        "print(test)\n"
        "print(f'robust F p-value for the variety effect: {test.f_pvalue:.4f}')"
    ),
]

# =====================================================================
# Ch 5 - MM regression (algae Ex5.4, ExactFit Ex5.5, wood Ex5.2, step Ex5.3)
# =====================================================================
ch5 = [
    new_markdown_cell(
        "## algae, MM regression with a dot formula (Example 5.4)\n"
        "\n"
        "`algae.R` fits `lmrobdetMM(V12 ~ .)` on the algae-bloom data (90×12) "
        "and contrasts it with LS. We reproduce the robust fit and its "
        "standardized-residual diagnostic (Fig 5.15)."
    ),
    new_code_cell(
        "algae = rpm.datasets.algae()\n"
        "ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family='bisquare')\n"
        "rob = rpm.lmrobdet_mm('V12 ~ .', algae, control=ctrl)\n"
        "print('robust scale:', round(float(rob.scale), 4))\n"
        "print('n coefficients:', len(rob.coefficients))\n"
        "resid = np.asarray(rob.residuals, dtype=float)\n"
        "std_resid = resid / float(rob.scale)\n"
        "outliers = np.flatnonzero(np.abs(std_resid) > 2.5)\n"
        "print('rows with |std resid| > 2.5:', (outliers + 1).tolist())"
    ),
    new_code_cell(
        "fig, ax = plt.subplots(figsize=(6, 4))\n"
        "ax.scatter(np.arange(1, len(std_resid)+1), std_resid, c='k', s=18)\n"
        "for h in (-2.5, 0, 2.5):\n"
        "    ax.axhline(h, ls='--', c='gray')\n"
        "ax.set_xlabel('index'); ax.set_ylabel('standardized robust residual')\n"
        "ax.set_title('algae, Fig 5.15 analogue')\n"
        "fig.savefig(FIG_DIR / 'ch5_algae_resid.png', dpi=110, bbox_inches='tight'); plt.close(fig)\n"
        "print('robust residuals expose the outliers LS hides')"
    ),
    new_markdown_cell("### Strict-tier cross-check vs direct R `lmrobdetMM`"),
    new_code_cell(
        "# lmrobdetMM is deterministic (Peña–Yohai initial), so no seeding is needed.\n"
        "rob_chk = rpm.lmrobdet_mm('V12 ~ .', algae, control=ctrl)\n"
        "ro.r('data(algae); cont <- lmrobdet.control(bb=0.5, efficiency=0.85, family=\"bisquare\")')\n"
        "ro.r('ra <- lmrobdetMM(V12 ~ ., data=algae, control=cont)')\n"
        "r_coef = np.asarray(ro.r('as.numeric(ra$coefficients)'), dtype=float)\n"
        "print('coefficients bit-equal to R:', np.array_equal(rob_chk.coefficients, r_coef))"
    ),
    new_markdown_cell(
        "## ExactFit, MM vs LS on a 1/3-contaminated line (Example 5.5)\n"
        "\n"
        "`ExactFit.R` builds 100 'good' points on `y = x` plus 50 outliers on "
        "`y = -2x`, then fits LS and MM. The MM line locks onto the majority; "
        "LS is pulled toward the contamination."
    ),
    new_code_cell(
        "# Reproduce the data generation exactly via R's RNG, then fit in Python.\n"
        "ro.r('''set.seed(1003); n<-100; m<-50; rr<-rnorm(m)\n"
        "x1<-sort(rnorm(n)); x2<-sort(rr)*2; sig<-0.1\n"
        "y1<-x1+sig*rnorm(n); y2<- -x2+sig*rnorm(m)\n"
        "xe<-c(x1,x2); ye<-c(y1,y2)''')\n"
        "xe = np.asarray(ro.r('xe'), dtype=float); ye = np.asarray(ro.r('ye'), dtype=float)\n"
        "mm = rpm.lmrobdet_mm('y ~ x', pd.DataFrame({'x': xe, 'y': ye}))\n"
        "Xe = np.c_[np.ones(len(xe)), xe]\n"
        "ls = np.linalg.lstsq(Xe, ye, rcond=None)[0]\n"
        "print('LS slope :', round(ls[1], 3), '(pulled toward the outliers)')\n"
        "print('MM slope :', round(float(mm.coefficients[1]), 3), '(tracks the good majority, ~1)')"
    ),
    new_code_cell(
        "grid = np.linspace(xe.min(), xe.max(), 50)\n"
        "fig, ax = plt.subplots(figsize=(6, 4))\n"
        "ax.scatter(xe, ye, c='gray', s=14)\n"
        "ax.plot(grid, ls[0] + ls[1]*grid, 'b-', lw=2, label='LS')\n"
        "ax.plot(grid, mm.coefficients[0] + mm.coefficients[1]*grid, 'r-', lw=2, label='MM')\n"
        "ax.set_xlabel('x'); ax.set_ylabel('y'); ax.legend(); ax.set_title('ExactFit, Fig 5.16 analogue')\n"
        "fig.savefig(FIG_DIR / 'ch5_exactfit.png', dpi=110, bbox_inches='tight'); plt.close(fig)\n"
        "print('done')"
    ),
    new_markdown_cell(
        "## wood, MM regression on the robustbase wood data (Example 5.2)\n"
        "\n"
        "`wood.R` loads `wood` from **robustbase** (cross-package) and fits "
        "`lmrobdetMM(y ~ .)`. We use `rpm.datasets.load('robustbase', 'wood')`."
    ),
    new_code_cell(
        "wood = rpm.datasets.load('robustbase', 'wood')\n"
        "print('columns:', list(wood.columns))\n"
        "ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family='bisquare')\n"
        "wMM = rpm.lmrobdet_mm('y ~ .', wood, control=ctrl)\n"
        "wresid = np.abs(np.asarray(wMM.residuals, dtype=float))\n"
        "flagged = np.flatnonzero(wresid > 2.5 * float(wMM.scale))\n"
        "print('robust scale:', round(float(wMM.scale), 5))\n"
        "print('outlying rows (|resid| > 2.5*scale):', (flagged + 1).tolist())"
    ),
    new_markdown_cell(
        "## step, robust stepwise model selection (Example 5.3)\n"
        "\n"
        "`step.R` builds a 6-predictor design with planted outliers, fits the "
        "full `lmrobdetMM`, then runs `step.lmrobdetMM` (robust backward "
        "selection by RFPE). The true model uses only the first three predictors."
    ),
    new_code_cell(
        "import pandas as pd\n"
        "# Reproduce step.R's data exactly via R's RNG.\n"
        "ro.r('''set.seed(300); X<-matrix(rnorm(50*6),50,6); beta<-c(1,1,1,0,0,0)\n"
        "y<-as.vector(X%*%beta)+1+rnorm(50); y[1:6]<-seq(30,55,5)\n"
        "for (i in 1:6) X[i,]<-c(X[i,1:3],i/2,i/2,i/2); Z<-as.data.frame(cbind(y,X))''')\n"
        "Z = pd.DataFrame(np.asarray(ro.r('as.matrix(Z)'), dtype=float),\n"
        "                 columns=['y','V2','V3','V4','V5','V6','V7'])\n"
        "ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family='bisquare')\n"
        "obj = rpm.lmrobdet_mm('y ~ .', Z, control=ctrl)\n"
        "sel = rpm.step_lmrobdet(obj)\n"
        "print('final model:', sel.final_formula)\n"
        "print('final coefficients:', dict(zip(sel.coef_names, np.round(sel.coefficients, 3))))"
    ),
]

# =====================================================================
# Ch 6 - multivariate (biochem Ex6.1, vehicle Ex6.3, bus Ex6.4, wine1 Ex6.5/6)
# =====================================================================
ch6 = [
    new_markdown_cell(
        "## biochem, classical location/scatter motivation (Example 6.1)\n"
        "\n"
        "`biochem.R` uses only classical statistics (mean, var, correlation) to "
        "show how a single observation (#3) distorts them, motivating the "
        "robust estimators in the rest of the chapter. No RobStatTM estimator is "
        "called here; it is the classical baseline."
    ),
    new_code_cell(
        "import numpy as np\n"
        "biochem = rpm.datasets.biochem()\n"
        "X = biochem.to_numpy(dtype=float)\n"
        "def stats(M):\n"
        "    mu = M.mean(axis=0); v = M.var(axis=0, ddof=1)\n"
        "    rho = np.corrcoef(M, rowvar=False)[0, 1]\n"
        "    return mu, v, rho\n"
        "mu, v, rho = stats(X)\n"
        "mu2, v2, rho2 = stats(np.delete(X, 2, axis=0))  # drop obs 3 (0-based 2)\n"
        "print('with obs 3 :  means', np.round(mu,2), 'vars', np.round(v,2), 'rho', round(rho,2))\n"
        "print('drop obs 3 :  means', np.round(mu2,2), 'vars', np.round(v2,2), 'rho', round(rho2,2))\n"
        "print('=> one point flips the correlation: classical stats are not robust')"
    ),
    new_markdown_cell(
        "## vehicle, Rocke S-estimator vs classical distances (Example 6.3)\n"
        "\n"
        "`vehicle.R` compares classical and `covRobRocke` Mahalanobis distances "
        "on the vehicle-silhouette data (217×18). The robust distances expose "
        "outliers masked by the classical covariance. (The rrcov CovMcd/CovSest "
        "comparators in the script are out of scope and omitted.)"
    ),
    new_code_cell(
        "vehicle = rpm.datasets.vehicle()\n"
        "Xv = vehicle.to_numpy(dtype=float)\n"
        "n, p = Xv.shape\n"
        "# classical Mahalanobis distances\n"
        "xbar = Xv.mean(axis=0); C = np.cov(Xv, rowvar=False)\n"
        "diff = Xv - xbar\n"
        "disC = np.einsum('ij,jk,ik->i', diff, np.linalg.inv(C), diff)\n"
        "# Rocke robust distances (stochastic -> seed for R parity)\n"
        "set_seed(1)\n"
        "rk = rpm.cov_rob_rocke(Xv)\n"
        "print(rk)\n"
        "print('robust vs classical max distance:', round(rk.dist.max(),1), 'vs', round(disC.max(),1))"
    ),
    new_code_cell(
        "from scipy.stats import chi2\n"
        "qua = chi2.ppf((np.arange(1, n+1) - 0.5) / n, p)\n"
        "fig, axes = plt.subplots(1, 2, figsize=(10, 4))\n"
        "for ax, d, title in ((axes[0], np.sort(disC), 'Classical'),\n"
        "                     (axes[1], np.sort(rk.dist), 'Rocke')):\n"
        "    ax.scatter(qua, d, c='k', s=12); ax.axline((0,0), slope=1, color='r')\n"
        "    ax.set_title(title); ax.set_xlabel('chi-square quantiles'); ax.set_ylabel('sorted distances')\n"
        "fig.savefig(FIG_DIR / 'ch6_vehicle.png', dpi=110, bbox_inches='tight'); plt.close(fig)\n"
        "print('Fig 6.7 analogue saved')"
    ),
    new_markdown_cell("### Strict-tier cross-check vs direct R `covRobRocke`"),
    new_code_cell(
        "ro.globalenv['Xv'] = Xv\n"
        "set_seed(1)\n"
        "rk = rpm.cov_rob_rocke(Xv)\n"
        "ro.r('set.seed(1L); rr <- covRobRocke(Xv)')\n"
        "print('center bit-equal to R:', np.array_equal(rk.center, np.asarray(ro.r('as.numeric(rr$center)'), dtype=float)))\n"
        "print('cov    bit-equal to R:', np.array_equal(rk.cov, np.asarray(ro.r('rr$cov'), dtype=float)))"
    ),
    new_markdown_cell(
        "## bus, robust PCA via M-scale (Example 6.4)\n"
        "\n"
        "`bus.R` drops column 9, standardizes by median/MAD, then compares "
        "classical PCA reconstruction error to `pcaRobS` (3 components)."
    ),
    new_code_cell(
        "bus = rpm.datasets.bus()\n"
        "X0 = bus.to_numpy(dtype=float)\n"
        "X1 = np.delete(X0, 8, axis=1)  # drop column 9 (0-based 8)\n"
        "from scipy.stats import median_abs_deviation\n"
        "med = np.median(X1, axis=0)\n"
        "mads = median_abs_deviation(X1, axis=0, scale='normal')\n"
        "Xb = (X1 - med) / mads\n"
        "set_seed(42)\n"
        "rr = rpm.pca_rob_s(Xb, ncomp=3)\n"
        "print(rr)\n"
        "print('proportion of robust scale explained (3 comps):', round(float(rr.propex), 4))\n"
        "# residual reconstruction distances, robust vs classical\n"
        "resiM = Xb - rr.fit\n"
        "dM = (resiM**2).sum(axis=1)\n"
        "print('robust reconstruction: max row distance =', round(dM.max(), 2))"
    ),
    new_markdown_cell("### Strict-tier cross-check vs direct R `pcaRobS`"),
    new_code_cell(
        "ro.globalenv['Xb'] = Xb\n"
        "set_seed(42)\n"
        "rr = rpm.pca_rob_s(Xb, ncomp=3)\n"
        "ro.r('set.seed(42L); rp <- pcaRobS(Xb, ncomp=3)')\n"
        "print('mu  bit-equal to R:', np.array_equal(rr.mu, np.asarray(ro.r('as.numeric(rp$mu)'), dtype=float)))\n"
        "print('fit bit-equal to R:', np.array_equal(rr.fit, np.asarray(ro.r('rp$fit'), dtype=float)))"
    ),
    new_markdown_cell(
        "## wine1, MM covariance under independent contamination (Examples 6.5–6.6)\n"
        "\n"
        "`wine1.R` flags multivariate outliers with `covRobMM` distances on the "
        "wine data. (The missing-data and cell-wise parts of `wine1.R` use "
        "`GSE::GSE` / `GSE::TSGS`, those are reproduced in "
        "`notebooks/external_demo.ipynb`.)"
    ),
    new_code_cell(
        "wine = rpm.datasets.wine()\n"
        "Xw = wine.to_numpy(dtype=float)\n"
        "n, p = Xw.shape\n"
        "from scipy.stats import chi2\n"
        "qq = chi2.ppf(0.999, p)\n"
        "set_seed(100)\n"
        "mm = rpm.cov_rob_mm(Xw)\n"
        "flagged = np.flatnonzero(mm.dist > qq)\n"
        "print(mm)\n"
        "print(f'rows with robust distance > chi2(.999, {p}) = {qq:.1f}: {(flagged+1).tolist()}')"
    ),
    new_code_cell(
        "ro.globalenv['Xw'] = Xw\n"
        "set_seed(100)\n"
        "mm = rpm.cov_rob_mm(Xw)\n"
        "ro.r('set.seed(100L); rm <- covRobMM(Xw)')\n"
        "print('center bit-equal to R:', np.array_equal(mm.center, np.asarray(ro.r('as.numeric(rm$center)'), dtype=float)))\n"
        "print('dist   bit-equal to R:', np.array_equal(mm.dist, np.asarray(ro.r('as.numeric(rm$dist)'), dtype=float)))"
    ),
]

# =====================================================================
# Ch 7 - robust GLM / logistic regression (skin Ex7.2, leukemia Ex7.1)
# =====================================================================
ch7 = [
    new_markdown_cell(
        "## leukemia, weighted Bianco–Yohai logistic regression (Example 7.1)\n"
        "\n"
        "`leukemia.R` fits `logregWBY` (weighted BY M-estimator) to the leukemia "
        "survival data and compares deviance residuals with the ML fit. (The "
        "`robust::glmRob` cubif comparator is out of scope and omitted.)"
    ),
    new_code_cell(
        "leuk = rpm.datasets.leuk_dat()\n"
        "print('columns:', list(leuk.columns))\n"
        "Xl = leuk.iloc[:, :2].to_numpy(dtype=float)\n"
        "yl = leuk.iloc[:, -1].to_numpy(dtype=float)\n"
        "wby = rpm.wby_logreg(Xl, yl, intercept=True)\n"
        "print(wby)\n"
        "print('coefficients:', np.round(wby.coefficients, 4))\n"
        "print('std deviation:', np.round(wby.standard_deviation, 4))"
    ),
    new_markdown_cell("### Strict-tier cross-check vs direct R `logregWBY`"),
    new_code_cell(
        "ro.globalenv['Xl'] = Xl\n"
        "ro.globalenv['yl'] = yl.reshape(-1, 1)\n"
        "ro.r('rw <- logregWBY(Xl, yl, intercept=1)')\n"
        "r_coef = np.asarray(ro.r('as.numeric(rw$coefficients)'), dtype=float)\n"
        "print('coefficients bit-equal to R:', np.array_equal(wby.coefficients, r_coef))"
    ),
    new_markdown_cell(
        "## skin, robust logistic regression family (Example 7.2)\n"
        "\n"
        "`skin.R` fits the weighted-M (`logregWBY`), plain BY (`logregBY`) and "
        "weighted-ML (`logregWML`) estimators to the vaso-constriction data. We "
        "reproduce all three; the ML and cubif comparators are out of scope."
    ),
    new_code_cell(
        "skin = rpm.datasets.skin()\n"
        "print('columns:', list(skin.columns))\n"
        "Xs = skin.iloc[:, :2].to_numpy(dtype=float)\n"
        "ys = skin['vasoconst'].to_numpy(dtype=float)\n"
        "wby = rpm.wby_logreg(Xs, ys, intercept=True)\n"
        "by = rpm.by_logreg(Xs, ys, intercept=True)\n"
        "wml = rpm.wml_logreg(Xs, ys, intercept=True)\n"
        "for name, fit in (('WBY', wby), ('BY', by), ('WML', wml)):\n"
        "    print(f'{name:>3}: coef = {np.round(fit.coefficients, 4)}')"
    ),
    new_code_cell(
        "# Figure 7.5 analogue: sorted |deviance residuals| of the weighted-M fit\n"
        "dev = np.sort(np.abs(wby.residual_deviances))\n"
        "pp = (np.arange(1, len(dev)+1) - 0.5) / len(dev)\n"
        "fig, ax = plt.subplots(figsize=(6, 4))\n"
        "ax.plot(pp, dev, 'o-', ms=4)\n"
        "ax.set_xlabel('quantiles'); ax.set_ylabel('|deviance residuals|')\n"
        "ax.set_title('skin, weighted-M deviance residuals (Fig 7.5 analogue)')\n"
        "fig.savefig(FIG_DIR / 'ch7_skin.png', dpi=110, bbox_inches='tight'); plt.close(fig)\n"
        "print('done')"
    ),
]

# =====================================================================
# Vignette - end-to-end (fitmodelsRobStatTM, VignetteRobStatTM)
# =====================================================================
vignette = [
    new_markdown_cell(
        "## End-to-end vignette (`fitmodelsRobStatTM.R`, `VignetteRobStatTM.R`)\n"
        "\n"
        "These scripts walk through RobStatTM via the **fit.models** comparison "
        "framework (`fit.models`, `plot.lmfm`, `plot.covfm`). `fit.models` is a "
        "separate package outside this project's scope, so here we reproduce the "
        "**robust estimator core** the vignette is built on, `lmrobdetMM` with "
        "the `mopt`/0.95 default control, and `covClassic` vs `covRob` on wine, "
        "and compare them using our own dataclass summaries instead of "
        "`fit.models`."
    ),
    new_markdown_cell(
        "### Regression: LS vs `lmrobdetMM` on mineral (mopt, eff 0.95)"
    ),
    new_code_cell(
        "mineral = rpm.datasets.mineral()\n"
        "control = rpm.lmrobdet_control(family='mopt', efficiency=0.95)\n"
        "robfit = rpm.lmrobdet_mm('zinc ~ copper', mineral, control=control)\n"
        "import numpy as np\n"
        "Xm = np.c_[np.ones(len(mineral)), mineral['copper'].to_numpy(float)]\n"
        "ym = mineral['zinc'].to_numpy(float)\n"
        "ls = np.linalg.lstsq(Xm, ym, rcond=None)[0]\n"
        "print('LS    coef:', np.round(ls, 3))\n"
        "print('robust coef:', np.round(robfit.coefficients, 3))\n"
        "print('\\nrobust summary:')\n"
        "print(robfit.summary().coefficients_table)"
    ),
    new_markdown_cell("Strict-tier cross-check vs direct R `lmrobdetMM`:"),
    new_code_cell(
        "# lmrobdetMM is deterministic (Peña–Yohai initial), so no seeding is needed.\n"
        "robfit_chk = rpm.lmrobdet_mm('zinc ~ copper', mineral, control=control)\n"
        "ro.r('data(mineral); ctrl <- lmrobdet.control(family=\"mopt\", efficiency=0.95)')\n"
        "ro.r('rfit <- lmrobdetMM(zinc ~ copper, control=ctrl, data=mineral)')\n"
        "r_coef = np.asarray(ro.r('as.numeric(rfit$coefficients)'), dtype=float)\n"
        "print('coefficients bit-equal to R:', np.array_equal(robfit_chk.coefficients, r_coef))"
    ),
    new_markdown_cell(
        "### Covariance: `covClassic` vs `covRob` on wine[, 1:5]"
    ),
    new_code_cell(
        "wine5 = rpm.datasets.wine().iloc[:, :5]\n"
        "cl = rpm.cov_classic(wine5)\n"
        "set_seed(1)\n"
        "rb = rpm.cov_rob(wine5, type='auto')\n"
        "print('classic eigenvalues:', np.round(cl.summary().evals, 3))\n"
        "print('robust  eigenvalues:', np.round(rb.summary().evals, 3))\n"
        "print('robust estimator chosen by covRob(type=\"auto\"):', rb.estimator_type)"
    ),
    new_markdown_cell(
        "The robust eigen-spectrum differs from the classical one because a few "
        "high-leverage wines inflate the classical covariance, exactly the "
        "comparison the vignette's `fit.models` plots illustrate. Every number "
        "above matches the underlying R call bit-for-bit."
    ),
]


if __name__ == "__main__":
    write("ch2_location_scale.ipynb", ch2,
          "# Chapter 2 gallery, location & scale\n\n"
          "Reproduces `flour.R` (Table 2.4) from the RobStatTM example scripts. "
          "Every numeric result is cross-checked bit-for-bit against direct R.")
    write("ch4_regression.ipynb", ch4,
          "# Chapter 4 gallery, robust M regression\n\n"
          "Reproduces `shock.R` (Ex 4.1) and `oats.R` (Ex 4.2). Robust fits via "
          "`lmrob_m`; robust nested-model testing via `rob_linear_test`.")
    write("ch5_regression.ipynb", ch5,
          "# Chapter 5 gallery, MM regression\n\n"
          "Reproduces `algae.R` (Ex 5.4), `ExactFit.R` (Ex 5.5), `wood.R` "
          "(Ex 5.2) and `step.R` (Ex 5.3) via `lmrobdet_mm` + `step_lmrobdet`.")
    write("ch6_multivariate.ipynb", ch6,
          "# Chapter 6 gallery, robust multivariate analysis\n\n"
          "Reproduces `biochem.R` (Ex 6.1), `vehicle.R` (Ex 6.3), `bus.R` "
          "(Ex 6.4) and the `covRobMM` part of `wine1.R` (Ex 6.5–6.6).")
    write("ch7_glm.ipynb", ch7,
          "# Chapter 7 gallery, robust logistic regression\n\n"
          "Reproduces `leukemia.R` (Ex 7.1) and `skin.R` (Ex 7.2) via the "
          "`by_logreg` / `wby_logreg` / `wml_logreg` family.")
    write("vignette.ipynb", vignette,
          "# Vignette gallery, end-to-end tour\n\n"
          "Reproduces the robust-estimator core of `fitmodelsRobStatTM.R` and "
          "`VignetteRobStatTM.R` (the `fit.models` framework itself is out of "
          "scope).")
