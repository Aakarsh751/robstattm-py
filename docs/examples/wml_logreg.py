import robstattm_py as rpm

# Skin dataset: 39 obs, 3 cols (3rd col is the binary vasoconst response).
skin = rpm.datasets.load("RobStatTM", "skin")
X = skin.iloc[:, :2].to_numpy()
y = skin["vasoconst"].to_numpy().astype(float)

# Weighted maximum-likelihood logistic regression — a robust ML variant that
# also reports a coefficient covariance matrix.
fit = rpm.wml_logreg(X, y, intercept=True)
print("coefficients      :", fit.coefficients.round(4))
print("standard deviation:", fit.standard_deviation.round(4))
