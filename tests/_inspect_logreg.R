library(RobStatTM)
data(skin)
X <- as.matrix(skin[, c("logVOL", "logRATE")])
y <- skin$vasoconst

cat("--- BYlogreg formals ---\n")
print(formals(BYlogreg))
cat("\n--- WBYlogreg formals ---\n")
print(formals(WBYlogreg))
cat("\n--- WMLlogreg formals ---\n")
print(formals(WMLlogreg))

cat("\n--- BYlogreg names ---\n")
fit_by <- BYlogreg(X, y)
print(names(fit_by))

cat("\n--- WBYlogreg names ---\n")
fit_wby <- WBYlogreg(X, y)
print(names(fit_wby))

cat("\n--- WMLlogreg names ---\n")
fit_wml <- WMLlogreg(X, y)
print(names(fit_wml))

cat("\n--- WMLlogreg str ---\n")
str(fit_wml)

cat("\n--- BY fitted.values dim ---\n")
print(dim(fit_by$fitted.values))
print(class(fit_by$fitted.values))
