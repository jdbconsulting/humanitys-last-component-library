# Murata BLM15PX chip ferrite beads

Subseries body dimensions extracted from Murata's PIM
(`https://pimapi.murata.com/public/api/pim/v1/products/search/part-numbers`,
the same backend the productdetail SPA reads). Length and Width
nominal+tolerance values come directly from the PIM dump; the
Thickness nominal value is back-calculated from `Thickness(max.)`
by subtracting the Width tolerance (Murata uses the same
+/- tolerance band for Width and Thickness on chip ferrite beads).

This reconstruction matches the Murata-page-inspected nominal
for the cross-check part BLM18BB050SN1 (1.6 / 0.8 / 0.8 mm).

## Bases (9)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM15PX121 | BLM15PX121BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX121BH1 |
| BLM15PX181 | BLM15PX181BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX181BH1 |
| BLM15PX221 | BLM15PX221BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX221BH1 |
| BLM15PX330 | BLM15PX330BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX330BH1 |
| BLM15PX331 | BLM15PX331BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX331BH1 |
| BLM15PX471 | BLM15PX471BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX471BH1 |
| BLM15PX600 | BLM15PX600BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX600BH1 |
| BLM15PX601 | BLM15PX601BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX601BH1 |
| BLM15PX800 | BLM15PX800BH1 |           1 |        0.5 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM15PX800BH1 |

## Reconstructed Specifications block (representative MPN: BLM15PX121BH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM15PX121BH1>

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
