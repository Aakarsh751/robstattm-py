suppressMessages(library(RobStatTM))
data(stackloss)
set.seed(42)
ff_full <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp + Acid.Conc., data=stackloss)
set.seed(42)
ff_red <- lmrobdetMM(stack.loss ~ Air.Flow + Water.Temp, data=stackloss)
res <- rob.linear.test(ff_full, ff_red)
cat("class:", paste(class(res), collapse=","), "\n")
cat("names:\n"); print(names(res))
if (is.list(res)) {
  for (nm in names(res)) {
    obj <- res[[nm]]
    cat(sprintf("  %-12s class=%-15s length=%s\n", nm, paste(class(obj),collapse=","), length(obj)))
  }
}
cat("\nprint:\n"); print(res)
