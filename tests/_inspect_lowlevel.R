library(RobStatTM)
set.seed(0)
n <- 50; p <- 3
X <- matrix(rnorm(n*p), n, p); X[,1] <- 1
y <- as.numeric(X %*% c(1,2,3) + rnorm(n))

# Build a model.frame for MMPY / SMPY
df <- data.frame(y=y, X1=X[,2], X2=X[,3])
mf <- model.frame(y ~ X1 + X2, data=df)

# control list as expected by MMPY/SMPY (uses lmrobdet.control output)
ctrl <- lmrobdet.control(family="bisquare", efficiency=0.85)

cat("===== MMPY return =====\n")
mm <- MMPY(X=cbind(1, X[,2:3]), y=y, control=ctrl, mf=mf)
cat("names:\n"); print(names(mm))
cat("str:\n"); str(mm, max.level=1)

cat("\n===== SMPY return =====\n")
sm <- SMPY(mf=mf, y=y, control=ctrl, split=1:50)
cat("names:\n"); print(names(sm))

cat("\n===== DCML return (needs z, z0) =====\n")
# DCML needs LS residuals (z) and a rescaled version (z0) of dimension n
ls_fit <- lm(y ~ X1 + X2, data=df)
zres <- residuals(ls_fit)
z0   <- zres / mad(zres)
d <- try(DCML(x=cbind(1, X[,2:3]), y=y, z=zres, z0=z0, control=ctrl), silent=TRUE)
if (inherits(d, "try-error")) {
  cat("DCML err:\n"); print(attr(d, "condition"))
} else {
  cat("names:\n"); print(names(d))
}

cat("\n===== cov.dcml return =====\n")
res.LS <- residuals(ls_fit)
res.R  <- residuals(ls_fit)  # placeholder
CC     <- crossprod(cbind(1, X[,2:3]))
sig.R  <- mad(res.LS)
t0     <- coef(ls_fit)
cd <- try(cov.dcml(res.LS=res.LS, res.R=res.R, CC=CC, sig.R=sig.R,
                   t0=t0, p=3, n=n, control=ctrl), silent=TRUE)
if (inherits(cd, "try-error")) {
  cat("cov.dcml err:\n"); print(attr(cd, "condition"))
} else {
  cat("class:\n"); print(class(cd))
  cat("dim:\n"); print(dim(cd))
}
