# Per-function research reports

One Markdown file per target function. Each report covers:

1. **Statistical purpose** — what problem does it solve
2. **Mathematical background** — short pointer to the underlying theory
3. **R implementation** — file path, exported names, internal helpers
4. **Inputs / Outputs / Return structure**
5. **Dependencies** — RobStatTM + external CRAN packages
6. **Python wrapper design** — recommended API, conversions, edge cases
7. **Validation strategy** — which cases from `docs/validation_strategy.md §3` apply

| File | Wraps | Book § | Priority |
|------|-------|--------|----------|
| `locScaleM.md` | `locScaleM` / `MLocDis` | 2.3, 2.7 | Core / Phase 1 |
| `mScale.md` | `mScale` (also `scaleM`, `mscale` in `DCML.R`) | 2.5, 2.6 | Core / Phase 1 |
| `lmrobdet.control.md` | `lmrobdet.control` | 5 | Core / Phase 1–2 |
| `lmrobM.md` | `lmrobM` | 4.4 | Core / Phase 1–2 |
| `rob.linear.test.md` | `lsRobTestMM` / `rob.linear.test` | 4.7 | Core / Phase 2 |
| `lmrobdetMM.md` | `lmrobdetMM` | 5.3, 5.9 | **Critical / Phase 2** |
| `pyinit.md` | `pyinit::pyinit` (external) | 5.7 | Core / Phase 2 |
| `step.lmrobdet.md` | `step.lmrobdet` | 5.6 | Core / Phase 2 |
| `lmrobdetDCML.md` | `lmrobdetDCML` | 5.9 | Core / Phase 2 |
| `pense.md` | `pense::pense` (external) | 5.1 | Stretch / Phase 6 |
| `covRobMM.md` | `covRobMM` / `MMultiSHR` | 6.5 | **Critical / Phase 3** |
| `covRobRocke.md` | `covRobRocke` / `RockeMulti` | 6.4 | **Critical / Phase 3** |
| `KurtSDNew.md` | `KurtSDNew` / `initPP` | 6.9.2 | Core / Phase 3 |
| `pcaRobS.md` | `pcaRobS` / `SMPCA` | 6.11.2 | **Critical / Phase 3** |
| `GSE.md` | `GSE::GSE` (external) | 6.12.2 | Stretch / Phase 6 |
| `TSGS.md` | `GSE::TSGS` (external) | 6.13 | Stretch / Phase 6 |
| `BYlogreg.md` | `BYlogreg` / `logregBY` | 7.2 | Stretch / Phase 6 |
| `WBYlogreg.md` | `WBYlogreg` / `logregWBY` | 7.2 | Stretch / Phase 6 |
| `WMLlogreg.md` | `WMLlogreg` / `logregWML` | 7.2 | Stretch / Phase 6 |

## Added 2026-06-10 (full-library expansion — see `docs/coverage_gap_analysis.md`)

| File | Wraps | Phase |
|------|-------|-------|
| `covClassic.md` | `covClassic` | Phase 3 |
| `covRob.md` | `covRob` (dispatcher) | Phase 3 |
| `Multirobu.md` | `Multirobu` (dispatcher) | Phase 3 |
| `prcompRob.md` | `prcompRob` | Phase 3 |
| `fastmve.md` | `fastmve` | Phase 3 |
| `DCML.md` | `DCML` (low-level) | Phase 2 |
| `cov.dcml.md` | `cov.dcml` | Phase 2 |
| `MMPY.md` | `MMPY` | Phase 2 |
| `SMPY.md` | `SMPY` | Phase 2 |
| `INVTR2.md` | `INVTR2` (robust R²) | Phase 2 |
| `lmrobdetMM.RFPE.md` | `lmrobdetMM.RFPE` | Phase 2 |
| `refine.sm.md` | `refine.sm` | Phase 2 |
| `lmrobM.control.md` | `lmrobM.control` | Phase 1–2 |
| `psi_families.md` | `bisquare`, `huber`, `mopt`, `moptv0`, `opt`, `optv0`, `rho`, `rhoprime`, `rhoprime2` | Phase 1 |
| `datasets.md` | All 20 RobStatTM datasets | Bonding + per-phase |

> **Note on detail level.** These reports are *design-time* documents. Field-by-field R `str()` captures are deferred to the start of each wrapper's implementation week per `docs/implementation_rules.md §2`. The reports below contain enough detail to plan the wrapper but the canonical field list comes from running R at implementation time.
