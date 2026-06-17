import robstatm_py as rpm

mineral = rpm.datasets.mineral()

# pyinit produces the deterministic Pena-Yohai starting points that
# lmrobdet_mm uses internally. Each column of `coefficients` is one robust
# candidate coefficient vector.
res = rpm.pyinit(
    X=mineral[["copper"]].to_numpy(),
    y=mineral["zinc"].to_numpy(),
)
print("candidate matrix shape (p x k):", res.coefficients.shape)
print("first candidate:", res.coefficients[:, 0].round(4))
