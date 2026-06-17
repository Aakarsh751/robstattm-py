library(RobStatTM)
data(wine)
X <- as.matrix(wine)

cat("===== covRob formals =====\n")
print(formals(covRob))

cat("\n===== Multirobu formals =====\n")
print(formals(Multirobu))

cat("\n===== Are they the same function? =====\n")
cat("identical(covRob, Multirobu):", identical(covRob, Multirobu), "\n")

cat("\n===== covRob(wine[,1:5]) type=auto (p<10 -> MM) =====\n")
set.seed(42)
fit_mm <- covRob(as.matrix(wine[,1:5]))
cat("class:", class(fit_mm), "\n")
cat("names:", names(fit_mm), "\n")
str(fit_mm, max.level=1)

cat("\n===== covRob(wine, p=13) type=auto (p>=10 -> Rocke) =====\n")
set.seed(42)
fit_rk <- covRob(as.matrix(wine))
cat("class:", class(fit_rk), "\n")
cat("names:", names(fit_rk), "\n")
str(fit_rk, max.level=1)

cat("\n===== covRob with explicit type=MM =====\n")
set.seed(42)
fit_mm2 <- covRob(as.matrix(wine[,1:5]), type="MM")
cat("class:", class(fit_mm2), "\n")
