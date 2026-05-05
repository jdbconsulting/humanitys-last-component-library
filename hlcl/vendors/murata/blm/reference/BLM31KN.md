# Murata BLM31KN chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (6)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM31KN102 | BLM31KN102BH1 |         3.2 |        1.6 |            1.6 | https://www.murata.com/products/productdetail?partno=BLM31KN102BH1 |
| BLM31KN121 | BLM31KN121BH1 |         3.2 |        1.6 |            1.6 | https://www.murata.com/products/productdetail?partno=BLM31KN121BH1 |
| BLM31KN271 | BLM31KN271BH1 |         3.2 |        1.6 |            1.6 | https://www.murata.com/products/productdetail?partno=BLM31KN271BH1 |
| BLM31KN471 | BLM31KN471BH1 |         3.2 |        1.6 |            1.6 | https://www.murata.com/products/productdetail?partno=BLM31KN471BH1 |
| BLM31KN601 | BLM31KN601BH1 |         3.2 |        1.6 |            1.6 | https://www.murata.com/products/productdetail?partno=BLM31KN601BH1 |
| BLM31KN801 | BLM31KN801BH1 |         3.2 |        1.6 |            1.6 | https://www.murata.com/products/productdetail?partno=BLM31KN801BH1 |

## Reconstructed Specifications block (representative MPN: BLM31KN102BH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM31KN102BH1>

```
|Shape|SMD|
|Size Code (in inch)|1206|
|Length|3.2mm|
|Length　Tolerance|±0.2mm|
|Width|1.6mm|
|Width Tolerance|±0.2mm|
|Thickness|1.6mm|
|Thickness　Tolerance|±0.2mm|
|Thickness (max.)|1.8mm|
```
