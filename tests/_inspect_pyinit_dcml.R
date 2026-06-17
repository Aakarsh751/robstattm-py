suppressMessages(library(RobStatTM))
suppressMessages(library(pyinit))
data(mineral)
X <- as.matrix(mineral["copper"]); y <- mineral$zinc
cat("=== formals(pyinit::pyinit) ===\n"); print(formals(pyinit::pyinit))
set.seed(42)
p <- pyinit::pyinit(x=X, y=y, cc=1.5476, psc_keep=0.5,
                    resid_keep_prop=0.2, resid_keep_thresh=2)
cat("\n=== names(pyinit result) ===\n"); print(names(p))
for (nm in names(p)) cat(sprintf("  %-15s class=%-20s length=%s\n", nm, paste(class(p[[nm]]),collapse=","), length(p[[nm]])))

cat("\n=== formals(lmrobdetDCML) ===\n"); print(formals(lmrobdetDCML))
set.seed(42)
d <- lmrobdetDCML(zinc ~ copper, data=mineral)
cat("\n=== names(lmrobdetDCML) ===\n"); print(names(d))
for (nm in names(d)) cat(sprintf("  %-15s class=%-20s length=%s\n", nm, paste(class(d[[nm]]),collapse=","), length(d[[nm]])))

cat("\n=== formals(lmrobM) ===\n"); print(formals(lmrobM))
set.seed(42)
m <- lmrobM(zinc ~ copper, data=mineral)
cat("\n=== names(lmrobM) ===\n"); print(names(m))
for (nm in names(m)) cat(sprintf("  %-15s class=%-20s length=%s\n", nm, paste(class(m[[nm]]),collapse=","), length(m[[nm]])))
