suppressMessages(library(RobStatTM))
data(bus)
X <- as.matrix(bus[, sapply(bus, is.numeric)])
cat("dim(X):", dim(X), "\n\n")
set.seed(42)
fit <- pcaRobS(X, ncomp = 5)
cat("=== names(fit) ===\n"); print(names(fit))
for (nm in names(fit)) {
  cls <- paste(class(fit[[nm]]), collapse = ",")
  ln <- tryCatch(length(fit[[nm]]), error = function(e) NA)
  cat(sprintf("  %-12s class=%-15s length=%s\n", nm, cls, as.character(ln)))
}
cat("\n=== formals(pcaRobS) ===\n"); print(formals(pcaRobS))
cat("\n=== formals(prcompRob) ===\n"); print(formals(prcompRob))

set.seed(42)
fit2 <- prcompRob(X)
cat("\n=== prcompRob names ===\n"); print(names(fit2))
for (nm in names(fit2)) {
  cls <- paste(class(fit2[[nm]]), collapse = ",")
  ln <- tryCatch(length(fit2[[nm]]), error = function(e) NA)
  cat(sprintf("  %-12s class=%-15s length=%s\n", nm, cls, as.character(ln)))
}
