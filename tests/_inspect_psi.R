suppressMessages(library(RobStatTM))
cat("=== Family identifiers ===\n")
for (fam in c("bisquare", "huber", "mopt", "opt", "moptv0", "optv0")) {
  obj <- get(fam, envir = asNamespace("RobStatTM"))
  cat(sprintf("  %-8s class=%-12s length=%d\n", fam, class(obj)[1], length(obj)))
}
cat("\n=== formals(rho) ===\n");      print(formals(rho))
cat("\n=== formals(rhoprime) ===\n"); print(formals(rhoprime))
cat("\n=== formals(rhoprime2) ===\n");print(formals(rhoprime2))
cat("\n=== sample values ===\n")
u <- c(-2, -1, -0.5, 0, 0.5, 1, 2)
cat("bisquare rho:     ", rho(u, family="bisquare"), "\n")
cat("bisquare rhoprime:", rhoprime(u, family="bisquare"), "\n")
cat("mopt rho:         ", rho(u, family="mopt"), "\n")
