suppressMessages(library(RobStatTM))
data(mineral)
set.seed(42)
fit <- lmrobdetMM(zinc ~ copper, data=mineral)

cat("=== formals(step.lmrobdetMM) ===\n"); print(formals(step.lmrobdetMM))
set.seed(42)
sfit <- step.lmrobdetMM(fit)
cat("\n=== names after step.lmrobdetMM ===\n"); print(names(sfit))
cat("\n=== class(sfit) ===\n"); print(class(sfit))

cat("\n=== formals(rob.linear.test) ===\n"); print(formals(rob.linear.test))

cat("\n=== formals(lsRobTestMM) ===\n"); print(formals(lsRobTestMM))
# rob.linear.test typically tests a subset of coefficients = 0
# Try: drop a variable from a multi-variable fit
data(stackloss)
set.seed(42)
ff_full <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., data=stackloss)
set.seed(42)
ff_red <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp, data=stackloss)
# Try the call
res <- tryCatch(rob.linear.test(ff_full, ff_red), error = function(e) e$message)
cat("\n=== rob.linear.test result ===\n"); print(res)
cat("class:", paste(class(res), collapse=","), "\n")
if (is.list(res)) {
  for (nm in names(res)) cat(sprintf("  %-12s class=%-15s length=%s\n", nm, paste(class(res[[nm]]),collapse=","), length(res[[nm]])))
}
