# `invtr2`

> **R original:** `INVTR2` &nbsp;·&nbsp; **Python module:** `robstattm_py.regression` &nbsp;·&nbsp; Robust R^2 coefficient of determination

This function computes a robust version of the R^2 coefficient of determination.
It is used internally by ``lmrobdetMM``,
and not meant to be used directly.

This function computes a robust version of the R^2 coefficient.
It is used internally by ``lmrobdetMM``,
and not meant to be used directly.

## Usage

```python
from robstattm_py import invtr2

def invtr2(rr2: 'float', family: 'str', cc: 'float | Sequence[float] | np.ndarray'):
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `rr2` | float | *required* |  |
| `family` | str | *required* | family string specifying the name of the family of loss function to be used (current valid options are "bisquare", "opt" and "mopt"). |
| `cc` | float \| Sequence[float] \| ndarray | *required* | tuning parameters to be computed according to efficiency and / or breakdown considerations. See `lmrobdet.control`, `bisquare`, `mopt` and `opt`. |


> **Note** — handled internally, not exposed in Python: `RR2`. These are constructed for you from the inputs above.


## Returns

Returns `float`.



## Example

```python
import robstattm_py as rpm

# invtr2 is the inverse transform used to turn a target robust R-squared into
# the corresponding value on the M-scale objective. The tuning argument `cc`
# is family-dependent: a scalar for "bisquare".
value = rpm.invtr2(0.5, "bisquare", 4.685)
print(f"invtr2(RR2=0.5, family='bisquare', cc=4.685) = {value:.6f}")
```



## References

<http://www.wiley.com/go/maronna/robust>


## Credits

R implementation by Victor Yohai, <victoryohai@gmail.com>. Python wrapper: RobStatTM-Py.


---

> **Bit-for-bit equivalence.** This wrapper calls the original R `INVTR2`
> through `rpy2`, so every returned value is validated against R at the strict
> tier (`atol=0`, `rtol=0`) — byte-identical given the same inputs and seed.
> See `tests/` for the strict-tier suite.
