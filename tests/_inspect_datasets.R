suppressMessages(library(RobStatTM))
ds <- data(package = "RobStatTM")$results[, "Item"]
cat(length(ds), "datasets:\n")
for (d in ds) {
  data(list = d)
  obj <- get(d)
  shape <- if (is.data.frame(obj) || is.matrix(obj)) {
    sprintf("%dx%d", nrow(obj), ncol(obj))
  } else {
    sprintf("len=%d", length(obj))
  }
  cls <- paste(class(obj), collapse = ",")
  cat(sprintf("  %-15s  class=%-25s  shape=%s\n", d, cls, shape))
}
