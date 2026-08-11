# Draft bug report for msalibian/RobStatTM

**Not filed.** Ready to paste at
<https://github.com/msalibian/RobStatTM/issues/new>, or to send to Doug Martin
and Matias Salibián-Barrera directly.

---

**Title:** `covRob` fails on a fresh R session: `KurtSDNew` reads `.Random.seed`
without checking it exists

---

### Summary

`initPP` / `KurtSDNew` reads `.Random.seed` unconditionally. R does not create
that variable until the random number generator is first used, so calling
`covRob` (or `covRobRocke`) as the **first** operation in a fresh R session
fails.

### Reproducing

In a brand-new R session, with nothing run beforehand:

```r
library(RobStatTM)
data(wine)
covRob(wine)
#> Error in get(".Random.seed", mode = "numeric", envir = globalenv()) :
#>   object '.Random.seed' of mode 'numeric' was not found
```

It succeeds if *anything* has already used the RNG:

```r
library(RobStatTM)
data(wine)
runif(1)          # or set.seed(1), or any random draw
covRob(wine)      # now fine
```

### Cause

`R/KurtSDNew.R:42`:

```r
initPP <- KurtSDNew <- function(X, muldirand=20, muldifix=10, dirmin=1000) {

  oldSeed <- get(".Random.seed", mode="numeric", envir=globalenv())
  on.exit(assign(".Random.seed", oldSeed, envir=globalenv()))
```

The `get()` has no `exists()` guard. `covRob` and `covRobRocke` reach it via
`R/Multirobu.R:123` and `R/Multirobu.R:359`.

The same save-and-restore is done correctly elsewhere in the package —
`R/lmrob.MM.R:690`:

```r
if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
    seed.keep <- get(".Random.seed", envir = .GlobalEnv, ...)
    on.exit(assign(".Random.seed", seed.keep, envir = .GlobalEnv))
}
```

### Suggested fix

Mirror the guarded form already used in `lmrob.MM.R`:

```r
if (exists(".Random.seed", envir = globalenv(), inherits = FALSE)) {
  oldSeed <- get(".Random.seed", mode = "numeric", envir = globalenv())
  on.exit(assign(".Random.seed", oldSeed, envir = globalenv()))
}
```

### Why this has stayed hidden

Interactive users rarely hit it, because almost anything done first in a
session touches the RNG. It shows up reliably in two situations:

- a non-interactive `Rscript` that calls `covRob` immediately, and
- an **embedded** R session, which is always pristine.

We found it in [robstattm-py](https://github.com/Aakarsh751/robstattm-py), a
Python interface to RobStatTM via rpy2, where every user session starts clean.
`cov_rob()` failed for *every* user whose first call it was — including the
example in our own README.

Our test suite had missed it, because the covariance tests call `set.seed()`
first for reproducibility, which creates `.Random.seed` as a side effect. It
only surfaced when running a plain first fit from a clean environment.

### Workaround in use downstream

We run this once when the embedded R session starts:

```r
if (!exists(".Random.seed", envir = globalenv())) set.seed(NULL)
```

`set.seed(NULL)` re-initialises from the clock and process ID, so results stay
random and a later `set.seed(n)` is still fully determining.

### Environment

- RobStatTM 1.0.11 (also present in the current GitHub source)
- R 4.5.2 and 4.5.3
- Reproduced on Windows; the cause is platform-independent
