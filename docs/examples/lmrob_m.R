data(mineral)

# lmrobM fits an M-estimator of regression (a simpler robust fit than the full
# MM-estimator). Good when you want a fast, bounded-influence fit.
fit <- lmrobM(zinc ~ copper, data = mineral)

print(round(coef(fit), 4))
print(round(fit$scale, 4))
