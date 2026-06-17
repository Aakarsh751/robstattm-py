data(mineral)
zinc <- mineral$zinc          # zinc concentration in 53 mineral samples

# Robust M-estimators of location AND scale, in one call.
est <- locScaleM(zinc, psi = "bisquare", eff = 0.95)

cat("robust location:", round(est$mu, 4), "\n")
cat("robust scale:   ", round(est$disper, 4), "\n")
cat("std-err of mu:  ", round(est$std.mu, 4), "\n")
