# Murata BLM18PG chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (8)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM18PG121 | BLM18PG121SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG121SH1 |
| BLM18PG181 | BLM18PG181SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG181SH1 |
| BLM18PG221 | BLM18PG221SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG221SH1 |
| BLM18PG300 | BLM18PG300SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG300SH1 |
| BLM18PG330 | BLM18PG330SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG330SH1 |
| BLM18PG331 | BLM18PG331SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG331SH1 |
| BLM18PG471 | BLM18PG471SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG471SH1 |
| BLM18PG600 | BLM18PG600SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18PG600SH1 |

## Reconstructed Specifications block (representative MPN: BLM18PG121SH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18PG121SH1>

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
