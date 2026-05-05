# Murata BLM18KG chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

Note: this subseries has body-thickness variation across its
value-prefixes — observed nominal thicknesses: 0.6mm, 0.8mm.

## Bases (10)

| base_mpn | sample_mpn | Length (mm) | Width (mm) | Thickness (mm) | source URL |
|---|---|---:|---:|---:|---|
| BLM18KG101 | BLM18KG101JH1 | 1.6 | 0.8 | 0.6 | https://www.murata.com/products/productdetail?partno=BLM18KG101JH1 |
| BLM18KG102 | BLM18KG102BH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18KG102BH1 |
| BLM18KG121 | BLM18KG121JH1 | 1.6 | 0.8 | 0.6 | https://www.murata.com/products/productdetail?partno=BLM18KG121JH1 |
| BLM18KG221 | BLM18KG221BH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18KG221BH1 |
| BLM18KG260 | BLM18KG260JH1 | 1.6 | 0.8 | 0.6 | https://www.murata.com/products/productdetail?partno=BLM18KG260JH1 |
| BLM18KG300 | BLM18KG300JH1 | 1.6 | 0.8 | 0.6 | https://www.murata.com/products/productdetail?partno=BLM18KG300JH1 |
| BLM18KG331 | BLM18KG331BH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18KG331BH1 |
| BLM18KG471 | BLM18KG471BH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18KG471BH1 |
| BLM18KG601 | BLM18KG601BH1 | 1.6 | 0.8 | 0.8 | https://www.murata.com/products/productdetail?partno=BLM18KG601BH1 |
| BLM18KG700 | BLM18KG700JH1 | 1.6 | 0.8 | 0.6 | https://www.murata.com/products/productdetail?partno=BLM18KG700JH1 |

## Reconstructed Specifications block (representative MPN: BLM18KG101JH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18KG101JH1>

```
|Shape|SMD|
|Size Code (in inch)|0603|
|Length|1.6mm|
|Length　Tolerance|±0.15mm|
|Width|0.8mm|
|Width Tolerance|±0.15mm|
|Thickness|0.6mm|
|Thickness　Tolerance|±0.15mm|
|Thickness (max.)|0.75mm|
```
