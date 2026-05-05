# Murata BLM15AX chip ferrite beads

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
| BLM15AX100 | BLM15AX100SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX100SN1 |
| BLM15AX102 | BLM15AX102SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX102SN1 |
| BLM15AX121 | BLM15AX121SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX121SN1 |
| BLM15AX221 | BLM15AX221SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX221SN1 |
| BLM15AX300 | BLM15AX300SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX300SN1 |
| BLM15AX601 | BLM15AX601SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX601SN1 |
| BLM15AX700 | BLM15AX700SN1 | 1 | 0.5 | 0.5 | https://www.murata.com/products/productdetail?partno=BLM15AX700SN1 |

## Reconstructed Specifications block (representative MPN: BLM15AX100SN1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM15AX100SN1>

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
