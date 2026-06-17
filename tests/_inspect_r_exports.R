library(RobStatTM)
exp <- getNamespaceExports("RobStatTM")
cat("Total exported objects:", length(exp), "\n\n")
# Filter to callables
is_fn <- sapply(exp, function(n) {
  obj <- tryCatch(get(n, envir = asNamespace("RobStatTM")), error = function(e) NULL)
  !is.null(obj) && is.function(obj)
})
fns <- sort(exp[is_fn])
cat("Functions (", length(fns), "):\n", sep="")
cat(paste(fns, collapse="\n"))
