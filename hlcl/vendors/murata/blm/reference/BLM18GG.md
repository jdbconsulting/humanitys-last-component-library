# Murata BLM18GG chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (1)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM18GG471 | BLM18GG471SN1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18GG471SN1 |

## Reconstructed Specifications block (representative MPN: BLM18GG471SN1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18GG471SN1>

```
|Shape|SMD|
|Size Code (in inch)|0603|
|Length|1.6mm|
|Length　Tolerance|±0.1mm|
|Width|0.8mm|
|Width Tolerance|±0.1mm|
|Thickness|0.8mm|
|Thickness　Tolerance|±0.1mm|
|Thickness (max.)|0.9mm|
```
