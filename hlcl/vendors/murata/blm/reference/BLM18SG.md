# Murata BLM18SG chip ferrite beads

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
value-prefixes — observed nominal thicknesses: 0.5mm, 0.8mm.

## Bases (6)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM18SG121 | BLM18SG121TN1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18SG121TN1 |
| BLM18SG221 | BLM18SG221TN1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18SG221TN1 |
| BLM18SG260 | BLM18SG260TN1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18SG260TN1 |
| BLM18SG330 | BLM18SG330SN1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18SG330SN1 |
| BLM18SG331 | BLM18SG331TN1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18SG331TN1 |
| BLM18SG700 | BLM18SG700TN1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18SG700TN1 |

## Reconstructed Specifications block (representative MPN: BLM18SG121TN1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18SG121TN1>

```
|Shape|SMD|
|Size Code (in inch)|0603|
|Length|1.6mm|
|Length　Tolerance|±0.15mm|
|Width|0.8mm|
|Width Tolerance|±0.15mm|
|Thickness|0.5mm|
|Thickness　Tolerance|±0.15mm|
|Thickness (max.)|0.65mm|
```
