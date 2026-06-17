data(wine)

# Rocke's S-estimator of multivariate location and scatter — designed to stay
# efficient in higher dimensions where other robust estimators lose power.
set.seed(42)
fit <- covRobRocke(wine)

print(dim(fit$cov))
print(round(fit$center, 2))
