# Datasets

RobStatTM-Py ships the **20 datasets** from RobStatTM and `robustbase` used
throughout the textbook, each returned as a pandas `DataFrame` with the original
R column names preserved.

```python
import robstattm_py as rpm

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

R column names containing dots (`stack.loss`, `Air.Flow`) are **renamed** on the
way in — a dot is not usable in a Python attribute. Dots become underscores, and
the originals are kept on the frame:

```python
df = rpm.datasets.stackloss()
list(df.columns)
# ['Obs', 'Air_Flow', 'Water_Temp', 'Acid_Conc_', 'stack_loss']

df.attrs["r_columns"]
# ('Obs', 'Air.Flow', 'Water.Temp', 'Acid.Conc.', 'stack.loss')
```

**Either spelling works in a formula**, and both give the same fit:

```python
rpm.lmrobdet_mm("stack_loss ~ Air_Flow + Water_Temp", data=df)   # what df.columns shows
rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp", data=df)   # what the book shows
```

Use the underscored names when working from the DataFrame, and the dotted ones
when transcribing a formula out of the textbook or porting an R script. The
frame is handed to R under its original names, so coefficient labels come back
in R's spelling either way.

> Until recently only the dotted form worked. The underscored one — the spelling
> `df.columns` shows you, and therefore the one everybody tries first — failed
> with R's `object 'stack_loss' not found`, naming something you could not see
> anywhere.
