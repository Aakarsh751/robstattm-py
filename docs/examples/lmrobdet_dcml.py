import robstattm_py as rpm

mineral = rpm.datasets.mineral()

# DCML ("Distance Constrained Maximum Likelihood") blends a robust and a
# classical fit, giving high efficiency while staying robust to outliers.
fit = rpm.lmrobdet_dcml("zinc ~ copper", data=mineral)

print("coefficients:", dict(zip(fit.coef_names, fit.coefficients.round(4))))
print("residual scale:", round(fit.scale, 4))
# DCML has no canonical robust R²; use the classical least-squares R² instead.
print("classical R²:", round(fit.r_squared_classic(), 4))
