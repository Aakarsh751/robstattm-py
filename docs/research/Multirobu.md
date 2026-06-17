# Multirobu

## 1. Statistical purpose
Top-level **multivariate robust dispatcher** (same role as `covRob`): picks Rocke for $p\ge 10$, MM SHR otherwise. Exported because some textbook scripts call it by name.

## 2. R implementation
File: `Multirobu.R` — same dispatch logic at top of file as `covRob`.

## 3. Python wrapper
Same signature and return as `cov_rob`. The Python wrapper can re-export: `multirobu = cov_rob` (single source of truth).

## 4. Validation
Trivial — same tests as `cov_rob`.
