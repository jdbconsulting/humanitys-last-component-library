# Murata BLM31SN chip ferrite beads

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
| BLM31SN500 | BLM31SN500BH1 |         3.2 |        1.6 |            1.1 | https://www.murata.com/products/productdetail?partno=BLM31SN500BH1 |

## Reconstructed Specifications block (representative MPN: BLM31SN500BH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM31SN500BH1>

```
|Shape|SMD|
|Size Code (in inch)|1206|
|Length|3.2mm|
|Length　Tolerance|±0.2mm|
|Width|1.6mm|
|Width Tolerance|±0.2mm|
|Thickness|1.1mm|
|Thickness　Tolerance|±0.2mm|
|Thickness (max.)|1.3mm|
```
