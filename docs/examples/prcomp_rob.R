data(bus)                    # 218 obs, 18 image-shape features
X <- as.matrix(bus)

# Robust principal-components decomposition.
pc <- prcompRob(X)

print(round(pc$sdev[1:5], 3))
