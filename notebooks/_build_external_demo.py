"""Builder for notebooks/external_demo.ipynb (D3 of docs/notebook_plan.md).

Run once to (re)generate the notebook, then execute it via the D1 CI test.
Kept in-repo so the notebook is reproducible from source rather than hand-edited
JSON. Safe to delete; the .ipynb is the deliverable.
"""
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()
cells = []

cells.append(new_markdown_cell(
    "# External robust estimators — `pense`, `gse`, `tsgs`\n"
    "\n"
    "The three *stretch* wrappers in `robstatm_py.external` bring estimators that live in "
    "**separate CRAN packages** (`pense`, `GSE`) but are recommended alongside RobStatTM in "
    "Maronna, Martin, Yohai & Salibián-Barrera, *Robust Statistics: Theory and Methods* (2019):\n"
    "\n"
    "| Function | R | What it does | Book |\n"
    "|---|---|---|---|\n"
    "| `rpm.pense` / `rpm.pense_cv` | `pense::pense` | Robust **elastic-net** regression (penalized S/MM) | §5.1 |\n"
    "| `rpm.gse` | `GSE::GSE` | Robust location/scatter with **missing data** | §6.12 |\n"
    "| `rpm.tsgs` | `GSE::TSGS` | Two-step GSE for **cell-wise** outliers | §6.13 |\n"
    "\n"
    "Every numeric result below is **bit-for-bit identical** to the underlying R call "
    "(`atol=0, rtol=0`) — these wrappers fit in R-space and read back the values, they do not "
    "re-implement anything. All three are stochastic, so we call `rpm.set_seed(...)` first for "
    "reproducibility (it seeds Python and R together).\n"
    "\n"
    "> Requires the `pense` and `GSE` R packages. If they are absent, `rpm.check_setup()` reports "
    "them as missing and the relevant cells will raise a clear setup error."
))

cells.append(new_code_cell(
    "import os, sys\n"
    "\n"
    "# Windows R_HOME setup (skip if already configured)\n"
    'if sys.platform == "win32" and "R_HOME" not in os.environ:\n'
    '    os.environ["R_HOME"] = r"C:\\Program Files\\R\\R-4.5.2"\n'
    '    os.environ["PATH"] = r"C:\\Program Files\\R\\R-4.5.2\\bin\\x64;" + os.environ["PATH"]\n'
    "\n"
    "import numpy as np\n"
    "import robstatm_py as rpm\n"
    "from robstatm_py import set_seed\n"
    "\n"
    'print(f"robstatm_py {rpm.__version__}")'
))

# --- pense ---------------------------------------------------------------
cells.append(new_markdown_cell(
    "## 1. `pense` — robust elastic-net regression\n"
    "\n"
    "Penalized S-estimation does variable selection *and* resists outliers. We use a sparse "
    "design — only 3 of 12 predictors are real signal — and inject 5 gross outliers in the "
    "response. A non-robust lasso would chase those outliers; `pense` should recover the sparse "
    "signal regardless."
))

cells.append(new_code_cell(
    "set_seed(7)\n"
    "rng = np.random.RandomState(7)\n"
    "n, p = 80, 12\n"
    "X = rng.randn(n, p)\n"
    "beta_true = np.array([4.0, -3.0, 2.0] + [0.0] * (p - 3))\n"
    "y = X @ beta_true + 0.5 * rng.randn(n)\n"
    "# 5 gross vertical outliers\n"
    "y[rng.choice(n, 5, replace=False)] += 25.0\n"
    "\n"
    'print("true non-zero coefficients:", np.flatnonzero(beta_true))'
))

cells.append(new_markdown_cell(
    "### 1a. Full regularization path (`pense`)"
))

cells.append(new_code_cell(
    "set_seed(7)\n"
    "fit = rpm.pense(X, y, alpha=0.5, nlambda=20)\n"
    "fit  # repr shows shape, alpha, breakdown point"
))

cells.append(new_code_cell(
    "# coefficients is (p+1, n_lambda): row 0 = intercept, one column per lambda.\n"
    "print('coefficient matrix shape:', fit.coefficients.shape)\n"
    "print('lambda path (descending):', np.round(fit.lambda_path[:5], 4), '...')\n"
    "# At the smallest lambda (least penalty) the slopes should track beta_true.\n"
    "slopes_least_penalty = fit.slopes[:, -1]\n"
    "for name, est, true in zip(fit.coef_names[1:], slopes_least_penalty, beta_true):\n"
    "    flag = '  <- signal' if true != 0 else ''\n"
    "    print(f'{name:>4}: {est:+.3f}{flag}')"
))

cells.append(new_markdown_cell(
    "### 1b. Cross-validated fit (`pense_cv`)\n"
    "\n"
    "`pense_cv` picks the penalty by k-fold CV and exposes the coefficients at the optimal "
    "`lambda` via `coef_min` (exactly R's `coef(fit, lambda=\"min\")`)."
))

cells.append(new_code_cell(
    "set_seed(7)\n"
    "cv = rpm.pense_cv(X, y, alpha=0.5, nlambda=20, cv_k=5, cv_repl=1)\n"
    "print(cv)\n"
    "print('lambda_min =', round(cv.lambda_min, 5))\n"
    "print('\\nCV-optimal coefficients (non-negligible):')\n"
    "for name, est in zip(cv.coef_names, cv.coef_min):\n"
    "    if abs(est) > 1e-6:\n"
    "        print(f'  {name:>11}: {est:+.3f}')\n"
    "print('\\ncvres table head:')\n"
    "print(cv.cvres.head())"
))

# --- gse -----------------------------------------------------------------
cells.append(new_markdown_cell(
    "## 2. `gse` — robust scatter with missing data\n"
    "\n"
    "The Generalized S-Estimator handles `NaN` entries natively (most robust covariance "
    "estimators cannot). We load the textbook **wine** dataset (n=59, p=13), knock out 8% of the "
    "cells at random, and estimate location/scatter from the incomplete matrix."
))

cells.append(new_code_cell(
    "wine = rpm.datasets.wine()\n"
    "Xw = wine.to_numpy(dtype=float)\n"
    "\n"
    "rng = np.random.default_rng(0)\n"
    "Xmiss = Xw.copy()\n"
    "k = round(0.08 * Xmiss.size)\n"
    "idx = rng.choice(Xmiss.size, size=k, replace=False)\n"
    "Xmiss.ravel()[idx] = np.nan\n"
    "print(f'wine shape {Xw.shape}; injected {k} missing cells "
    "({np.isnan(Xmiss).mean():.1%})')"
))

cells.append(new_code_cell(
    "set_seed(42)\n"
    "g = rpm.gse(Xmiss)\n"
    "print(g)\n"
    "print('\\nrobust location (first 5 vars):', np.round(g.mu[:5], 4))\n"
    "print('generalized S-scale:', round(g.sc, 5), '| iters:', g.iter)\n"
    "print('imputed matrix has no NaN:', not np.isnan(g.ximp).any())\n"
    "# Largest partial Mahalanobis distances flag the most unusual rows.\n"
    "top = np.argsort(g.pmd)[::-1][:5]\n"
    "print('top-5 rows by partial Mahalanobis distance:', top.tolist())"
))

# --- tsgs ----------------------------------------------------------------
cells.append(new_markdown_cell(
    "## 3. `tsgs` — two-step GSE for cell-wise outliers\n"
    "\n"
    "Cell-wise contamination corrupts *individual entries* (not whole rows). `TSGS` first flags "
    "and filters bad cells, then runs a GSE on the rest. We contaminate 5% of wine's cells with "
    "gross values and recover a clean scatter."
))

cells.append(new_code_cell(
    "rng = np.random.default_rng(1)\n"
    "Xcell = Xw.copy()\n"
    "col_sd = Xcell.std(axis=0, ddof=1)\n"
    "kc = round(0.05 * Xcell.size)\n"
    "ci = rng.choice(Xcell.size, size=kc, replace=False)\n"
    "rows, cols = np.unravel_index(ci, Xcell.shape)\n"
    "Xcell[rows, cols] += 10.0 * col_sd[cols]  # gross cell-wise shifts\n"
    "print(f'contaminated {kc} cells ({kc / Xcell.size:.1%})')"
))

cells.append(new_code_cell(
    "set_seed(42)\n"
    "t = rpm.tsgs(Xcell)\n"
    "print(t)\n"
    "n_flagged = int(np.isnan(t.xf).sum())\n"
    "print('cells flagged + filtered by step 1:', n_flagged)\n"
    "print('robust location (first 5 vars):', np.round(t.mu[:5], 4))\n"
    "\n"
    "# Compare to a classical covariance on the *contaminated* data: the cell-wise\n"
    "# outliers inflate the classical variances; TSGS resists them.\n"
    "classical_var = np.diag(np.cov(Xcell, rowvar=False))\n"
    "tsgs_var = np.diag(t.cov)\n"
    "print('\\nvar(classical) vs var(tsgs), first 5 vars:')\n"
    "for j in range(5):\n"
    "    print(f'  var{j}: classical={classical_var[j]:10.3f}   tsgs={tsgs_var[j]:10.3f}')"
))

cells.append(new_markdown_cell(
    "## Summary\n"
    "\n"
    "- `pense` / `pense_cv` deliver outlier-resistant elastic-net regression with built-in "
    "variable selection.\n"
    "- `gse` estimates robust location/scatter straight from data with missing cells.\n"
    "- `tsgs` adds cell-wise outlier filtering on top of GSE.\n"
    "\n"
    "All three return frozen dataclasses carrying the standard ergonomics (`.to_dict()`, "
    "`.to_r()`, `_repr_html_`) and the raw R fit in `_r_fit`. Numbers match the underlying R "
    "packages exactly — see `tests/external/test_pense.py` and `tests/external/test_gse.py`."
))

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}

with open("external_demo.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("wrote external_demo.ipynb with", len(cells), "cells")
