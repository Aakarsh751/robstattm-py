suppressMessages(library(RobStatTM))
data(wine)
X <- as.matrix(wine[, sapply(wine, is.numeric)])
cat("dim(X):", dim(X), "\n\n")

c1 <- covClassic(X)
cat("=== covClassic names ===\n"); print(names(c1))
cat("=== covClassic classes ===\n")
for (nm in names(c1)) cat(sprintf("  %-12s class=%-15s length=%s\n", nm, paste(class(c1[[nm]]),collapse=","), length(c1[[nm]])))

set.seed(42)
c2 <- covRobMM(X)
cat("\n=== covRobMM names ===\n"); print(names(c2))
for (nm in names(c2)) cat(sprintf("  %-12s class=%-15s length=%s\n", nm, paste(class(c2[[nm]]),collapse=","), length(c2[[nm]])))

set.seed(42)
c3 <- covRobRocke(X)
cat("\n=== covRobRocke names ===\n"); print(names(c3))
for (nm in names(c3)) cat(sprintf("  %-12s class=%-15s length=%s\n", nm, paste(class(c3[[nm]]),collapse=","), length(c3[[nm]])))

cat("\n=== formals ===\n")
cat("covClassic:  "); print(names(formals(covClassic)))
cat("covRobMM:    "); print(names(formals(covRobMM)))
cat("covRobRocke: "); print(names(formals(covRobRocke)))
