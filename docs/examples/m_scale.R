data(mineral)
zinc <- mineral$zinc           # zinc concentration in 53 mineral samples

# The M-scale is a robust measure of spread; a handful of outliers barely move
# it, unlike the classical standard deviation.
robust    <- scaleM(zinc)
classical <- sd(zinc)

cat("robust M-scale   :", round(robust, 4), "\n")
cat("classical std dev:", round(classical, 4), "\n")
