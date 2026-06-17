library(tools)
db <- Rd_db("RobStatTM")
cat("=== Names of all Rd files (57) ===\n")
cat(paste(sort(names(db)), collapse="\n"), "\n")

# Show structure of a representative Rd
rd <- db[["lmrobdetMM.Rd"]]
cat("\n=== lmrobdetMM.Rd structure ===\n")
print(rd)
