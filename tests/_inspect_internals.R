library(RobStatTM)
data(mineral)

# ---- lmrobM: how to compute predict and hatvalues by hand ----
cat("===== lmrobM predict via model.matrix * coef =====\n")
fit_m <- lmrobM(zinc ~ copper, data = mineral)
mm <- model.matrix(zinc ~ copper, data = mineral)
pred_manual <- as.numeric(mm %*% coef(fit_m))
cat("first 6:\n"); print(head(pred_manual))
cat("matches fitted.values?\n")
print(all.equal(pred_manual, as.numeric(fit_m$fitted.values)))

cat("\n===== lmrobdetMM predict via model.matrix * coef (for comparison) =====\n")
fit_mm <- lmrobdetMM(zinc ~ copper, data = mineral)
mm2 <- model.matrix(zinc ~ copper, data = mineral)
pred_manual2 <- as.numeric(mm2 %*% coef(fit_mm))
pred_S3 <- predict(fit_mm)
cat("identical()? ", identical(pred_manual2, as.numeric(pred_S3)), "\n")
cat("all.equal()? "); print(all.equal(pred_manual2, as.numeric(pred_S3)))

cat("\n===== lmrob hatvalues formula =====\n")
# robustbase::hatvalues.lmrob source:
#   X <- model.matrix(object); w <- object$rweights; sqW <- sqrt(w)
#   XW <- sqW * X; qr.X <- qr(XW); diag(qr.Q(qr.X) %*% t(qr.Q(qr.X)))
# So hatvalues = diag(Q Q') where Q is the Q-factor of (sqrt(w) * X)
hv_mm <- hatvalues(fit_mm)
mm3 <- model.matrix(zinc ~ copper, data = mineral)
w <- fit_mm$rweights
sqW <- sqrt(w)
XW <- sqW * mm3
qrXW <- qr(XW)
Q <- qr.Q(qrXW)
hv_manual <- diag(Q %*% t(Q))
cat("hatvalues match identical?\n")
print(identical(as.numeric(hv_mm), hv_manual))
print(all.equal(as.numeric(hv_mm), hv_manual))

cat("\n===== summary.lmrobdetMM source, how r.squared is computed =====\n")
# This is the relevant source from RobStatTM:
print(getFromNamespace("summary.lmrobdetMM", "RobStatTM"))
