import numpy as np
import pandas as pd
import rpy2.robjects as ro

import robstattm_py as rpm

# step_lmrobdet runs robust *backward* model selection, dropping terms by their
# Robust Final Prediction Error (RFPE). This mirrors the R man-page example: a
# 6-column design where only the first three columns carry signal
# (beta = [1, 1, 1, 0, 0, 0]) and rows 1-6 are gross outliers, so a good robust
# selector should drop the three noise terms (V5, V6, V7).
#
# The data is generated with R's RNG so the fit matches R bit-for-bit; for your
# own analysis just build a DataFrame directly.
ro.r('''
set.seed(300)
X <- matrix(rnorm(50*6), 50, 6); beta <- c(1, 1, 1, 0, 0, 0)
y <- as.vector(X %*% beta) + 1 + rnorm(50); y[1:6] <- seq(30, 55, 5)
for (i in 1:6) X[i, ] <- c(X[i, 1:3], i/2, i/2, i/2)
Z <- as.data.frame(cbind(y, X))
''')
Z = pd.DataFrame(np.asarray(ro.r('as.matrix(Z)'), dtype=float),
                 columns=['y', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7'])

# Tuning knobs, breakdown point `bb`, target Gaussian `efficiency`, and the loss
# `family`, go through lmrobdet_control, the Python equivalent of R's
# lmrobdet.control(). Pass it to lmrobdet_mm via `control=`.
ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
full = rpm.lmrobdet_mm("y ~ .", data=Z, control=ctrl)
step = rpm.step_lmrobdet(full)

print("full model    : y ~ .")
print("selected model:", step.final_formula)   # drops the noise terms V5, V6, V7
print("coefficients  :", dict(zip(step.coef_names, step.coefficients.round(3))))
