# Murata BLM15BB chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (7)

| base_mpn | sample_mpn | Length (mm) | Width (mm) | Thickness (mm) | source URL |
|---|---|---:|---:|---:|---|
| BLM15BB050 | BLM15BB050SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB050SH1 |
| BLM15BB100 | BLM15BB100SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB100SH1 |
| BLM15BB121 | BLM15BB121SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB121SH1 |
| BLM15BB220 | BLM15BB220SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB220SH1 |
| BLM15BB221 | BLM15BB221SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB221SH1 |
| BLM15BB470 | BLM15BB470SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB470SH1 |
| BLM15BB750 | BLM15BB750SH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15BB750SH1 |

## Reconstructed Specifications block (representative MPN: BLM15BB050SH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM15BB050SH1>

```
|Shape|SMD|
|Size Code (in inch)|0402|
|Length|1mm|
|Length　Tolerance|±0.05mm|
|Width|0.5mm|
|Width Tolerance|±0.05mm|
|Thickness|0.5mm|
|Thickness　Tolerance|±0.05mm|
|Thickness (max.)|0.55mm|
```
