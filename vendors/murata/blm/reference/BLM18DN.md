# Murata BLM18DN chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (4)

| base_mpn | sample_mpn | Length (mm) | Width (mm) | Thickness (mm) | source URL |
|---|---|---:|---:|---:|---|
| BLM18DN151 | BLM18DN151SH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18DN151SH1 |
| BLM18DN221 | BLM18DN221SH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18DN221SH1 |
| BLM18DN381 | BLM18DN381SH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18DN381SH1 |
| BLM18DN601 | BLM18DN601SH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18DN601SH1 |

## Reconstructed Specifications block (representative MPN: BLM18DN151SH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18DN151SH1>

```
|Shape|SMD|
|Size Code (in inch)|0603|
|Length|1.6mm|
|Length　Tolerance|±0.15mm|
|Width|0.8mm|
|Width Tolerance|±0.15mm|
|Thickness|0.8mm|
|Thickness　Tolerance|±0.15mm|
|Thickness (max.)|0.95mm|
```
