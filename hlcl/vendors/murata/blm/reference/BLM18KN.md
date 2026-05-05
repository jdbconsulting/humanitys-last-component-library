# Murata BLM18KN chip ferrite beads

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

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM18KN101 | BLM18KN101EH1 |         1.6 |        0.8 |            0.6 | https://www.murata.com/products/productdetail?partno=BLM18KN101EH1 |
| BLM18KN102 | BLM18KN102EH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18KN102EH1 |
| BLM18KN121 | BLM18KN121EH1 |         1.6 |        0.8 |            0.6 | https://www.murata.com/products/productdetail?partno=BLM18KN121EH1 |
| BLM18KN221 | BLM18KN221EH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18KN221EH1 |
| BLM18KN260 | BLM18KN260EH1 |         1.6 |        0.8 |            0.6 | https://www.murata.com/products/productdetail?partno=BLM18KN260EH1 |
| BLM18KN300 | BLM18KN300EH1 |         1.6 |        0.8 |            0.6 | https://www.murata.com/products/productdetail?partno=BLM18KN300EH1 |
| BLM18KN331 | BLM18KN331EH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18KN331EH1 |
| BLM18KN471 | BLM18KN471EH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18KN471EH1 |
| BLM18KN601 | BLM18KN601EH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18KN601EH1 |
| BLM18KN700 | BLM18KN700EH1 |         1.6 |        0.8 |            0.6 | https://www.murata.com/products/productdetail?partno=BLM18KN700EH1 |

## Reconstructed Specifications block (representative MPN: BLM18KN101EH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18KN101EH1>

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
