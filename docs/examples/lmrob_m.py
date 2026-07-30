import robstattm_py as rpm

mineral = rpm.datasets.mineral()

# lmrob_m fits an M-estimator of regression (a simpler robust fit than the
# full MM-estimator). Good when you want a fast, bounded-influence fit.
fit = rpm.lmrob_m("zinc ~ copper", data=mineral)

print(fit)                       # short summary
print()
print("coefficients:", dict(zip(fit.coef_names, fit.coefficients.round(4))))
print("robust scale:", round(fit.scale, 4))
