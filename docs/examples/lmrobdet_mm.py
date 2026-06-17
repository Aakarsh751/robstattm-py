import robstatm_py as rpm

# Load Coleman's school data — 20 obs of school outcomes vs predictors.
coleman = rpm.datasets.load("robustbase", "coleman")

# Fit a robust MM-regression.  ``Y ~ .`` means "regress Y on every
# other column".  The wrapper handles dot formulas correctly.
fit = rpm.lmrobdet_mm("Y ~ .", data=coleman)

print(fit)               # short S3-style summary
print()
print(fit.summary())     # full summary table with std errors / p-values

print(f"\nR² = {fit.r_squared:.4f}   converged after {fit.iter} IRWLS iterations")
print(f"coefficients: {dict(zip(fit.coef_names, fit.coefficients.round(3)))}")
