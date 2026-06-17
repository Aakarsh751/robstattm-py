# Datasets

RobStatTM-Py ships the **20 datasets** from RobStatTM and `robustbase` used
throughout the textbook, each returned as a pandas `DataFrame` with the original
R column names preserved.

```python
import robstatm_py as rpm

mineral = rpm.datasets.mineral()      # -> pandas DataFrame
print(mineral.head())
print(rpm.datasets.available())       # list every built-in dataset name
```

## Built-in datasets

| Loader | Notes |
|---|---|
| `rpm.datasets.alcohol()` | Solubility of alcohols. |
| `rpm.datasets.algae()` | Algae blooms vs. river chemistry. |
| `rpm.datasets.biochem()` | Biochemistry measurements. |
| `rpm.datasets.breslow_dat()` | Breslow seizure-count data. |
| `rpm.datasets.bus()` | Vehicle (bus) silhouette shape features. |
| `rpm.datasets.flour()` | Copper content of flour samples. |
| `rpm.datasets.glass()` | Glass composition spectra. |
| `rpm.datasets.hearing()` | Hearing-test data. |
| `rpm.datasets.image()` | Image segmentation features. |
| `rpm.datasets.leuk_dat()` | Leukemia survival data. |
| `rpm.datasets.mineral()` | Zinc & copper in 53 mineral samples (classic regression demo). |
| `rpm.datasets.neuralgia()` | Neuralgia treatment outcomes. |
| `rpm.datasets.oats()` | Agricultural oats yield trial. |
| `rpm.datasets.resex()` | Residential electricity demand. |
| `rpm.datasets.shock()` | Shock-experiment response. |
| `rpm.datasets.skin()` | Skin vaso-constriction (logistic-regression demo). |
| `rpm.datasets.stackloss()` | Stack-loss process data (stepwise-regression demo). |
| `rpm.datasets.vehicle()` | Vehicle silhouette classification features. |
| `rpm.datasets.waste()` | Solid-waste vs. land-use predictors. |
| `rpm.datasets.wine()` | 13 chemical measurements on 59 wines (covariance/PCA demo). |

## Loading any R dataset

To load a dataset from any installed R package, use `datasets.load`:

```python
coleman = rpm.datasets.load("robustbase", "coleman")
skin    = rpm.datasets.load("RobStatTM", "skin")
```

## R column names

R column names containing dots (e.g. `stack.loss`, `Air.Flow`) are kept as-is so
that formulas read exactly like the textbook:

```python
df = rpm.datasets.stackloss()
fit = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)
```
