# cov.dcml

## 1. Statistical purpose
**Covariance matrix of the DCML coefficient estimator.** Internal to `lmrobdetDCML`'s standard-error calculation; exported because some advanced users compute SEs separately.

## 2. R implementation
File: `DCML.R` line 112. Signature: `cov.dcml(res.LS, res.R, CC, sig.R, t0, p, n, control)`.

## 3. Python wrapper design
```python
def cov_dcml(
    res_ls: ArrayLike, res_r: ArrayLike, cc: ArrayLike, sig_r: float, t0: float,
    p: int, n: int, control: LmrobdetControl,
) -> np.ndarray: ...
```
Returns the $(p \times p)$ covariance matrix directly (no dataclass needed — single matrix output).

## 4. Validation strategy
Cases 1, 2, 7, 10 + symmetry + PSD. Strict-tier against R.
