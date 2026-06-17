import numpy as np
import robstatm_py as rpm

# Skin dataset: 39 obs, 3 cols (3rd col is the binary vasoconst response).
skin = rpm.datasets.load("RobStatTM", "skin")

X = skin.iloc[:, :2].to_numpy()
y = skin["vasoconst"].to_numpy().astype(float)

# Bianco-Yohai robust logistic regression.
fit = rpm.by_logreg(X, y, intercept=True)

print(f"coefficients:       {fit.coefficients.round(4)}")
print(f"standard deviation: {fit.standard_deviation.round(4)}")
print(f"converged:          {fit.converged}")
print(f"method:             {fit.method}")
