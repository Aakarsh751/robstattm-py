# lmrobM.control

## 1. Statistical purpose
Tuning parameter container for `lmrobM`. Mirrors `lmrobdet.control` but with fewer keys (no S-init parameters).

## 2. R implementation
File: `lmrobdet.R` line 1468. Returns a named list.

## 3. Python wrapper design
```python
@dataclass(frozen=True, slots=True)
class LmrobMControl:
    bb: float = 0.5
    # ... full list from man/lmrobM.control.Rd
```
Function `lmrobm_control(**kwargs) -> LmrobMControl`.

## 4. Validation strategy
Same as `lmrobdet.control.md §7`: kwarg count test + round-trip strict-tier.
