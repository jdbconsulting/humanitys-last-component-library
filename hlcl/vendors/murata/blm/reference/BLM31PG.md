# Murata BLM31PG chip ferrite beads

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

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM31PG121 | BLM31PG121SH1 |         3.2 |        1.6 |            1.1 | https://www.murata.com/products/productdetail?partno=BLM31PG121SH1 |
| BLM31PG330 | BLM31PG330SH1 |         3.2 |        1.6 |            1.1 | https://www.murata.com/products/productdetail?partno=BLM31PG330SH1 |
| BLM31PG391 | BLM31PG391SH1 |         3.2 |        1.6 |            1.1 | https://www.murata.com/products/productdetail?partno=BLM31PG391SH1 |
| BLM31PG500 | BLM31PG500SH1 |         3.2 |        1.6 |            1.1 | https://www.murata.com/products/productdetail?partno=BLM31PG500SH1 |
| BLM31PG601 | BLM31PG601SH1 |         3.2 |        1.6 |            1.1 | https://www.murata.com/products/productdetail?partno=BLM31PG601SH1 |

## Reconstructed Specifications block (representative MPN: BLM31PG121SH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM31PG121SH1>

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
