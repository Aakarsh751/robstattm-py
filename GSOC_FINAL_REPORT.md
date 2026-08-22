# RobStatTM-Py: Google Summer of Code 2026 Final Report

**Project:** RobStatTM-Py, Python wrappers for modern robust statistical estimation

**Contributor:** Aakarsh Gupta \
**Organization:** The R Project for Statistical Computing \
**Mentors:** Professor Doug Martin (University of Washington), Professor Matias Salibian-Barrera (University of British Columbia), Brian Peterson \
**Code:** https://github.com/Aakarsh751/robstattm-py \
**Documentation:** https://aakarsh751.github.io/robstattm-py/  \
**Upstream R package:** https://github.com/msalibian/RobStatTM  

---

## 1. Introduction

RobStatTM-Py makes the robust statistics estimators from the R package
[RobStatTM](https://cran.r-project.org/package=RobStatTM) usable from Python. It does this by calling the original, published R
routines underneath through [rpy2](https://rpy2.github.io/), rather than
re-writing the math in Python. Because the same R code runs underneath, every
number that comes back is identical to R, and the test suite proves it by
comparing field by field at zero tolerance. Over the summer the project grew
from a proof of concept into an installable, documented, continuously tested
Python package that covers essentially the whole RobStatTM function set plus
several companion estimators, ships one runnable Python example for every
example script in the R package, and builds cleanly on Linux, Windows, and
macOS.

## 2. Background: the problem this solves

Robust statistics answers a simple question: what happens to your estimates
when a fraction of your data is wrong, contaminated, or extreme? Classical
methods such as ordinary least squares can be moved arbitrarily far by a single
bad point. Robust methods resist that. RobStatTM is the R package that
accompanies the 2019 Wiley textbook *Robust Statistics: Theory and Methods (with
R)* by Maronna, Martin, Yohai, and Salibian-Barrera. It is the reference
implementation of the estimators taught in that book.

The catch is that a large part of the working data science world utilise
Python, and those estimators were not available there in a clean, trustworthy
form. A Python user who wanted MM-regression, robust covariance, robust PCA, or
robust logistic regression either had to switch to R or hope that a scattered
third-party reimplementation matched the textbook. The goal of this project was
to remove that gap and bring RobStatTM to Python users with no R knowledge
required.

## 3. Project goals

The accepted proposal set out to deliver:

1. A complete rpy2 wrapper layer over RobStatTM whose outputs match R
   numerically, covering univariate M-estimators, robust regression, robust
   covariance, and robust PCA.
2. A rigorous, automated evaluation that each wrapper is numerically identical
   to a direct R call, function by function and field by field.
3. Ergonomic, Pythonic result objects (formula interface, pandas and numpy implementation, summaries, prediction, diagnostics).
4. Documentation modelled on the R manual pages, tutorial notebooks that
   reproduce textbook figures, and a cross-platform installation guide.
5. Packaging and distribution so a Python user can install it and get a working
   R underneath without configuring anything by hand.
6. Stretch goals: companion estimators from outside RobStatTM that the book
   recommends (robust logistic regression, penalized robust regression, robust
   covariance from other packages), and a comparison layer that lines up a
   classical fit next to a robust fit.

Every one of these was delivered. The sections below describe what was built
and the state of each.

## 4. What was built

### 4.1 The wrapper layer and its coverage

The core deliverable is the wrapper layer. Import once and call the estimators
with Python names, pandas frames, and numpy arrays:

```python
import robstattm_py as rpm

mineral = rpm.datasets.mineral()                       # a pandas DataFrame
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)   # robust MM-regression
print(fit.summary())                                   # coefficients, scale, robust R-squared
fit.predict(mineral)                                   # prediction
fit.hatvalues()                                        # diagnostics

cov = rpm.cov_rob(rpm.datasets.wine())                 # robust covariance
pca = rpm.prcomp_rob(rpm.datasets.bus())               # robust PCA
```

Coverage against the RobStatTM package, tracked in the repository's coverage
matrix:

| Group | Status |
|---|---|
| Core RobStatTM callables (the package NAMESPACE) | 43 of 47 wrapped and tested; the other 4 are internal helpers, documented as such |
| S3 methods (summary, print, predict, hatvalues, drop1, and so on) | 13 of 13 |
| Textbook datasets | 20 of 20, returned as pandas DataFrames with R column names preserved |
| psi-function family helpers | 9 of 9 |
| Stretch estimators from companion packages | robust logistic regression (BYlogreg, WBYlogreg, WMLlogreg), penalized robust regression (pense, pense_cv), robust covariance (GSE, TSGS), robust GLM (glmrob), robust ARIMA (arima.rob), robust variance components (varComprob), and cubinf |

Both the Python-style names and the original R names are available. If you know
R, `import robstattm_py.compat_r as rtm` gives you `lmrobdetMM`, `covRobMM`,
`BYlogreg`, and the rest under their exact R identifiers, so book and paper code
translates almost line for line.

### 4.2 Comparison layer (classical next to robust)

A late addition, in direct response to mentor feedback, is a comparison layer
that answers the everyday question "how different is my robust fit from the
classical one?" `compare()` bundles two or more fits of the same data and lines
up their coefficient tables and diagnostics side by side, using R's own
`fit.models` machinery underneath:

```python
ls  = rpm.comparison.lm("zinc ~ copper", data=mineral)     # classical least squares
rob = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)       # robust MM
rpm.compare(LS=ls, Robust=rob).summary()                   # columns line up
```

This works for regression, for classical versus robust GLM, and for classical
versus robust covariance.

### 4.3 Plotting

The package includes a native plotting suite for the standard robust
diagnostics: residuals, robust QQ plots, distance-distance plots for
covariance, scree and score plots for PCA, and side by side classical versus
robust panels. Plots can be produced natively in Python or drawn by R for an
exact match to the book figures.

### 4.4 One runnable example for every R example script

The `examples/` folder holds 25 Python scripts, one for each example script that
ships inside the RobStatTM R package, covering Chapters 2 and 4 through 8 of the
textbook plus both package vignettes. Each script keeps the structure, example
numbers, and figure numbers of the R original, so a reader can hold the book in
one hand and the Python script in the other. Every one of these is executed end
to end by the test suite on every continuous integration run, so an example that
stops working becomes a failing build.

### 4.5 Documentation

The documentation site at https://aakarsh751.github.io/robstattm-py/ is live and
built from the repository. It includes a getting-started guide, an API reference
generated from docstrings that are themselves modelled on the R manual pages, a
"coming from R" translation page, cross-platform installation and
troubleshooting guides, and reproductions of textbook figures. The same pages
are written so they read cleanly both on the website and directly on GitHub.

### 4.6 Installation and setup that does not ask the user to configure R

A Python user should not have to become an R system administrator. The package
finds an existing R on its own (Windows registry, PATH, an active conda
environment, or the standard install location for the operating system) and
refuses an R built for the wrong CPU architecture before it can crash Python. If
there is no R, a `robstattm-py setup` command can provision one, and a
`robstattm-py doctor` command reports exactly what is present and, when
something is wrong, the exact command that fixes it. Installation is documented
and tested for pip, conda, and Docker.

### 4.7 Continuous integration

The GitHub Actions workflow runs the test suite and linting on Linux, Windows,
and macOS on every push. This is what keeps the "identical to R" promise honest
over time and across platforms, and it is currently green.

## 5. How the numbers come out identical to R

The package does not reimplement the statistics. When you call
`rpm.lmrobdet_mm(...)`, the actual fitting is done by the same
`RobStatTM::lmrobdetMM` R function that the textbook uses. The Python layer's job
is to hand the data across to R, run the R routine, and hand the
results back, converting R vectors, matrices, and data frames to numpy arrays
and pandas frames without losing precision. Because the computation is the
published R computation, the output is the R output, not an approximation of it.

Three things make that trustworthy rather than merely plausible:

1. **Strict-tier parity tests.** Every wrapper is checked field by field against
   a direct R call on the same data, at `atol=0, rtol=0`, meaning zero allowed
   difference. Coefficients, scale, residuals, weights,
   fitted values, summary tables, and diagnostics all have to match exactly. The
   suite has grown to over 1,100 automated tests, combining these strict parity
   tests with data-pipeline, edge-case, example, and notebook-execution tests.

2. **Careful marshalling.** Passing values between Python and R is where silent
   corruption hides. The wrappers never build R code out of Python values as
   text. They pass native objects across the rpy2 bridge, which avoids a whole
   class of formatting and rounding bugs. Randomness is handled by setting the
   seed on both sides so that the stochastic estimators (the ones that use random
   subsampling) reproduce the same result in Python as in R.

3. **The examples and notebooks are tests.** Reproducing the book's own example
   scripts, one to one, exercises the exact code paths a real reader would take.
   That process alone surfaced four real defects that the unit tests had missed,
   because the unit tests were written by someone who already knew the intended
   API, while the example scripts follow the book paths. All
   four were fixed and now have regression tests.

The practical result: a Python user gets textbook-correct robust estimates, and
can point to a zero-tolerance test as the reason to believe it.

## 6. Current state of the project

The project is in a finished, usable state.

- The package installs and runs on Linux, Windows, and macOS.
- Continuous integration is green across all three operating systems.
- Documentation is published and live.
- The current version is 0.2.0.
- All coding-period work has landed on the `main` branch of the repository, so
  the repository as it stands is the deliverable, not a work-in-progress branch.

## 7. Code that was merged

The repository history is the record of the work. The larger pieces landed as
reviewed pull requests on top of the steady day to day commits, including:

- **Production-readiness pass** (PR #9): repository restructure into
  user-facing versus contributor-facing docs, an
  interactive setup that offers to use an existing R rather than always
  downloading one, and verification of the pip, uv, pipx, conda, and Docker
  install paths.
- **Comparison models** (PR #10): native wrappers for the classical baselines
  (`lm`, `glm`, `rlm`, `ltsReg`, `lmrob`) and the `compare()`.
- **Robust logistic regression test fidelity** (PR #11): made the parity tests
  for the stochastic robust logistic regressions order independent.
- **Classical versus robust GLM comparison** (PR #12): extended `compare()` to
  GLMs and turned the comparison tests on in continuous integration; this is the
  0.2.0 release.

No coding-period work is stranded on an unmerged branch. Everything described in
this report is on `main`.

## 8. What is left to do

The library is complete and works today. The remaining items are about
distribution, not about missing functionality.

1. **Publish to the major installers.** The package is not yet on PyPI or
   conda-forge. Today it installs from source in one command straight from
   GitHub, which is fully supported and documented:

   ```bash
   git clone https://github.com/Aakarsh751/robstattm-py.git
   pip install ./robstattm-py
   robstattm-py setup            # provisions R if you do not have it
   ```

   The only thing standing between this and `pip install robstattm-py` is the
   one-time publishing step (creating the PyPI trusted publisher and pushing a
   release tag). The release machinery, metadata, and license form are already
   in place; the distribution artifacts have been built and checked. A draft
   conda-forge recipe is included in the repository.

2. **More testing breadth.** The strict parity suite is thorough on the
   estimators, but there is always room for more edge-case coverage, wider
   platform and version combinations, and more of the benchmark comparisons
   (robust versus classical timing and accuracy) written up as a standalone
   notebook.

3. **Optional native Python track.** The proposal listed, as a secondary
   stretch, native Python reimplementations of a few estimators to sit next to
   the R-backed wrappers for benchmarking. The R-backed path is the product; the
   native track remains an open, optional direction for future contributors.

## 9. How to install and try it

```bash
# 1. Get the code and install it
git clone https://github.com/Aakarsh751/robstattm-py.git
pip install ./robstattm-py

# 2. Make sure R and the R packages are present (provisions R if needed)
robstattm-py setup
robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov

# 3. Confirm everything is wired up
robstattm-py doctor
```

```python
# 4. Use it
import robstattm_py as rpm

mineral = rpm.datasets.mineral()
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
print(fit.coefficients)      # numpy array, identical to R
print(fit.summary())
```

Full instructions, including a beginner guide that assumes nothing and a page
for R users, are in the [documentation](https://aakarsh751.github.io/robstattm-py/).

## 10. Challenges and lessons learned

- **A green test suite is not the same as a working package.** The single most
  useful lesson. Porting the R package's own example scripts, one to one, found
  four real bugs that more than a thousand passing tests had not, because tests
  are written by someone who already knows the API and unconsciously avoids its
  rough edges.
- **Cross-platform R discovery is hard.** R can live in a dozen places,
  can be built for the wrong CPU, and on Windows can hide behind the registry or
  a path with a space in it. A large part of the "just works" experience was
  detecting and handling these cases so the user never sees them.
- **The bridge is where precision dies.** Marshalling values between Python and R
  by formatting them into text is a silent accuracy bug.
  Passing native objects across the bridge, and setting seeds on both sides for
  the stochastic estimators, is what made zero-tolerance agreement achievable.
- **You cannot debug a platform you cannot reproduce.** Some issues only appeared
  in specific installer and operating system combinations. The reliable path was
  to reproduce the user's exact environment rather than reason about it from a
  distance.
- **Documentation that must read well in two places is worth the effort.** Pages
  written to render cleanly both on the website and directly on GitHub is the better approach.

## 11. Links

- Source code: https://github.com/Aakarsh751/robstattm-py
- Documentation: https://aakarsh751.github.io/robstattm-py/
- Changelog: https://github.com/Aakarsh751/robstattm-py/blob/main/CHANGELOG.md
- Example scripts (one per R example): https://github.com/Aakarsh751/robstattm-py/tree/main/examples
- Upstream R package (RobStatTM): https://github.com/msalibian/RobStatTM
- The textbook: Maronna, Martin, Yohai, and Salibian-Barrera, *Robust Statistics:
  Theory and Methods (with R)*, 2nd edition, Wiley, 2019.

## 12. Acknowledgements

Thank you to my mentors, Professor Doug Martin, Professor Matias
Salibian-Barrera, and Brian Peterson, for their guidance, quick feedback, and
patience over the summer, and to the R Project for Statistical Computing for
hosting the project.

---

*GSoC 2026 contributor, The R Project for Statistical Computing.*
