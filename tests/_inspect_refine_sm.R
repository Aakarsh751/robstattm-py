library(RobStatTM)
set.seed(0)
n <- 50; p <- 2
X <- matrix(rnorm(n*p), n, p)
y <- as.numeric(X %*% c(1,2)) + rnorm(n)*0.5
b  <- bisquare(0.5)
cc <- bisquare(0.85)
beta0 <- c(0.9, 1.9)
res <- refine.sm(x=X, y=y, initial.beta=beta0, initial.scale=0.5,
                 b=b, cc=cc, family="bisquare", tol=1e-7)
cat("class:\n"); print(class(res))
cat("names:\n"); print(names(res))
cat("str:\n"); str(res)
