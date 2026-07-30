"""Reproduce the non-conformable error to isolate the cause."""
import os, sys
if sys.platform == "win32" and "R_HOME" not in os.environ:
    os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"
    os.environ["PATH"] = r"C:\Program Files\R\R-4.5.2\bin\x64;" + os.environ["PATH"]

from robstattm_py._r import r as _r
ro = _r()

print("--- Step 1: create matrix in pure R ---")
ro.r("library(RobStatTM); set.seed(0); X <- matrix(rnorm(50*2), 50, 2)")
print("class(X):", list(ro.r("class(X)")))
print("dim(X):  ", list(ro.r("dim(X)")))
print("is.matrix(X):", list(ro.r("is.matrix(X)")))

print("\n--- Step 2: matrix multiply (should give length-50 vector) ---")
y = ro.r("as.numeric(X %*% c(1,2))")
print("y length:", len(y))

print("\n--- Step 3: full block via one ro.r() call ---")
ro.r("""
    library(RobStatTM)
    set.seed(0)
    X <- matrix(rnorm(50*2), 50, 2)
    print(dim(X))
    y <- as.numeric(X %*% c(1,2)) + rnorm(50)*0.5
    print(length(y))
""")

print("\n--- Step 4: now call refine.sm via rpy2 ---")
ro.r("""
    b   <- bisquare(0.5)
    cc  <- bisquare(0.85)
    b0  <- c(0.9, 1.9)
    print(c(length(b), length(cc), length(b0)))
    print(class(b0))
    res <- refine.sm(x=X, y=y, initial.beta=b0, initial.scale=0.5,
                     b=b, cc=cc, family='bisquare', tol=1e-7)
    print(names(res))
""")
