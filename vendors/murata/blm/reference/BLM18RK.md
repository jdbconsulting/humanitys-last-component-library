# Murata BLM18RK chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (5)

| base_mpn | sample_mpn | Length (mm) | Width (mm) | Thickness (mm) | source URL |
|---|---|---:|---:|---:|---|
| BLM18RK102 | BLM18RK102SN1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18RK102SN1 |
| BLM18RK121 | BLM18RK121SN1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18RK121SN1 |
| BLM18RK221 | BLM18RK221SN1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18RK221SN1 |
| BLM18RK471 | BLM18RK471SN1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18RK471SN1 |
| BLM18RK601 | BLM18RK601SN1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18RK601SN1 |

## Reconstructed Specifications block (representative MPN: BLM18RK102SN1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18RK102SN1>

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
