import robstattm_py as rpm

# invtr2 is the inverse transform used to turn a target robust R-squared into
# the corresponding value on the M-scale objective. The tuning argument `cc`
# is family-dependent: a scalar for "bisquare".
value = rpm.invtr2(0.5, "bisquare", 4.685)
print(f"invtr2(RR2=0.5, family='bisquare', cc=4.685) = {value:.6f}")
