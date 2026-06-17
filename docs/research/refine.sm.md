# refine.sm

## 1. Statistical purpose
**S→M refinement step**: given an initial $\hat\beta$ and scale, perform `k` IRLS refinement iterations toward the MM target. Exported so users can chain custom initial estimators into the standard refinement.

## 2. R implementation
File: `lmrobdet.R` line 720. Signature: `refine.sm(x, y, initial.beta, initial.scale, k=50, conv=1e-7, ...)`.

## 3. Python wrapper design
```python
def refine_sm(
    X: ArrayLike, y: ArrayLike, *,
    initial_beta: ArrayLike, initial_scale: float,
    k: int = 50, conv: float = 1e-7, control: LmrobdetControl | None = None,
) -> RefineSMResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class RefineSMResult:
    coefficients: np.ndarray
    scale: float
    iter: int
    converged: bool
```

## 4. Validation strategy
Cases 1–3, 7, 10.
