library(RobStatTM)
data(mineral)
fit <- lmrobdetMM(zinc ~ copper, data = mineral)

cat("===== INVTR2 formals =====\n")
print(formals(INVTR2))

cat("\n===== lmrobdetMM.RFPE formals =====\n")
print(formals(lmrobdetMM.RFPE))

cat("\n===== refine.sm formals =====\n")
print(formals(refine.sm))

cat("\n===== lmrobdetMM.RFPE on the fit =====\n")
rfpe <- lmrobdetMM.RFPE(fit)
cat("class:", class(rfpe), "length:", length(rfpe), "\n")
print(rfpe)

cat("\n===== lmrobdetMM.RFPE with bothVals=TRUE =====\n")
rfpe2 <- lmrobdetMM.RFPE(fit, bothVals=TRUE)
cat("class:", class(rfpe2), "length:", length(rfpe2), "\n")
print(rfpe2)
cat("names:", names(rfpe2), "\n")

cat("\n===== INVTR2 with explicit args =====\n")
r2_val <- INVTR2(RR2=0.5, family="bisquare", cc=4.685)
cat("class:", class(r2_val), "\n")
print(r2_val)
