# Murata BLM18HB chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (3)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM18HB121 | BLM18HB121SN1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18HB121SN1 |
| BLM18HB221 | BLM18HB221SN1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18HB221SN1 |
| BLM18HB331 | BLM18HB331SN1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18HB331SN1 |

## Reconstructed Specifications block (representative MPN: BLM18HB121SN1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18HB121SN1>

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
