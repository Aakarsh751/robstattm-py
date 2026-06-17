data(mineral)

# DCML ("Distance Constrained Maximum Likelihood") blends a robust and a
# classical fit, giving high efficiency while staying robust to outliers.
fit <- lmrobdetDCML(zinc ~ copper, data = mineral)

print(round(coef(fit), 4))
print(round(fit$scale, 4))
