suppressMessages(library(RobStatTM))
data(mineral)
fit <- lmrobdetMM(zinc ~ copper, data = mineral)

cat("=== class(fit) ===\n"); print(class(fit))
cat("=== names(fit) ===\n"); print(names(fit))
cat("=== element classes ===\n")
for (nm in names(fit)) {
  cls <- paste(class(fit[[nm]]), collapse = ",")
  ln <- tryCatch(length(fit[[nm]]), error = function(e) NA)
  cat(sprintf("  %-20s class=%-30s length=%s\n", nm, cls, as.character(ln)))
}
cat("\n=== coefficients ===\n"); print(coef(fit))
cat("\n=== fit$scale ===\n"); print(fit$scale)
cat("=== formals(lmrobdet.control) ===\n"); print(names(formals(lmrobdet.control)))
