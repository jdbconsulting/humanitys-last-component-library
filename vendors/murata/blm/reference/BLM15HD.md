# Murata BLM15HD chip ferrite beads

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

| base_mpn | sample_mpn | Length (mm) | Width (mm) | Thickness (mm) | source URL |
|---|---|---:|---:|---:|---|
| BLM15HD102 | BLM15HD102BH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15HD102BH1 |
| BLM15HD182 | BLM15HD182BH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15HD182BH1 |
| BLM15HD601 | BLM15HD601BH1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15HD601BH1 |

## Reconstructed Specifications block (representative MPN: BLM15HD102BH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM15HD102BH1>

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
