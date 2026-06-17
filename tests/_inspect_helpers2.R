library(RobStatTM)

# 1) lmrobM.control formals
cat("===== lmrobM.control =====\n")
print(formals(lmrobM.control))

# 2) DCML formals + return shape
cat("\n===== DCML =====\n")
print(formals(DCML))
cat("DCML help (Description+Args):\n")
print(help("DCML", package="RobStatTM"))
cat("---\n")
# Look at how lmrobdetDCML calls DCML to understand z/z0
print(getFromNamespace("lmrobdetDCML", "RobStatTM"))

# 3) cov.dcml
cat("\n===== cov.dcml =====\n")
print(formals(cov.dcml))

# 4) MMPY
cat("\n===== MMPY =====\n")
print(formals(MMPY))

# 5) SMPY
cat("\n===== SMPY =====\n")
print(formals(SMPY))

# 6) refine.sm
cat("\n===== refine.sm =====\n")
print(formals(refine.sm))
