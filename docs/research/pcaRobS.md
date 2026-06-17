# pcaRobS (alias SMPCA)  **(critical)**

## 1. Statistical purpose
**Robust PCA via M-scale minimization** (Maronna et al. 2019, §6.11.2). Finds principal directions that minimize a robust scale of projected residuals, rather than maximizing variance — naturally resistant to point outliers in the data matrix.

## 2. Mathematical background
For desired explained-variance proportion `desprop`, iteratively finds direction $v$ minimizing $s(\{x_i - (x_i^\top v) v\})$ where $s$ is an M-scale with tuning `deltasca`. Initial direction: spherical PCA via `rrcov::PcaLocantore`.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/RobPCA_SM.R` line 40.
- Initial: `rrcov::PcaLocantore` at line 47.
- Companion: `prcompRob` in `prcompRob.R` (line 34) provides a `prcomp`-shaped wrapper.

## 4. Inputs / Outputs / Return structure
**Signature:** `pcaRobS(X, ncomp, desprop=0.9, deltasca=0.5, maxit=100)`

Returns list with: `q` (number of comps chosen), `eigvec` (n_comp × p loadings), `eigval` (eigenvalues), `propex` (proportion explained), `scores` (n × q), `mu` (robust center).

## 5. Dependencies
- RobStatTM
- rrcov

## 6. Python wrapper design

```python
def pca_rob_s(
    X: ArrayLike,
    *,
    ncomp: int | None = None,
    desprop: float = 0.9,
    deltasca: float = 0.5,
    maxit: int = 100,
) -> PcaRobSResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class PcaRobSResult:
    q: int                       # number of retained components
    eigvec: np.ndarray           # (q, p) loadings
    eigval: np.ndarray           # (q,)
    propex: np.ndarray           # cumulative proportion
    scores: np.ndarray           # (n, q)
    mu: np.ndarray               # robust center
```

## 7. Validation strategy
Cases 1–4, 7, 10. Reproduce `bus.R` (Fig 6.10). Sign-ambiguity test: compare absolute values of loadings if a sign flip occurs (rare, but possible across rrcov versions; document the policy when implementing).
