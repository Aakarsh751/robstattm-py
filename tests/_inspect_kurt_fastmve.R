suppressMessages(library(RobStatTM))
data(wine)
X <- as.matrix(wine[, sapply(wine, is.numeric)])

set.seed(42)
k <- KurtSDNew(X)
cat("=== KurtSDNew names ===\n"); print(names(k))
for (nm in names(k)) {
  cls <- paste(class(k[[nm]]), collapse=",")
  ln <- length(k[[nm]])
  cat(sprintf("  %-12s class=%-15s length=%s\n", nm, cls, ln))
}
cat("\n=== formals(KurtSDNew) ===\n"); print(formals(KurtSDNew))

set.seed(42)
f <- fastmve(X)
cat("\n=== fastmve names ===\n"); print(names(f))
for (nm in names(f)) {
  cls <- paste(class(f[[nm]]), collapse=",")
  ln <- length(f[[nm]])
  cat(sprintf("  %-12s class=%-15s length=%s\n", nm, cls, ln))
}
cat("\n=== formals(fastmve) ===\n"); print(formals(fastmve))
