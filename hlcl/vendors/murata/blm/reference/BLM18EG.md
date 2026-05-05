# Murata BLM18EG chip ferrite beads

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

## Bases (8)

| base_mpn   | sample_mpn    | Length (mm) | Width (mm) | Thickness (mm) | source URL                                                         |
| ---------- | ------------- | ----------: | ---------: | -------------: | ------------------------------------------------------------------ |
| BLM18EG101 | BLM18EG101TH1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18EG101TH1 |
| BLM18EG121 | BLM18EG121SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18EG121SH1 |
| BLM18EG181 | BLM18EG181SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18EG181SH1 |
| BLM18EG221 | BLM18EG221SN1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18EG221SN1 |
| BLM18EG331 | BLM18EG331TH1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18EG331TH1 |
| BLM18EG391 | BLM18EG391TH1 |         1.6 |        0.8 |            0.5 | https://www.murata.com/products/productdetail?partno=BLM18EG391TH1 |
| BLM18EG471 | BLM18EG471SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18EG471SH1 |
| BLM18EG601 | BLM18EG601SH1 |         1.6 |        0.8 |            0.8 | https://www.murata.com/products/productdetail?partno=BLM18EG601SH1 |

## Intra-base dimension variation

Some bases have variants (different tolerance/temperature/packaging
suffixes) with physically different bodies despite sharing the same
first 10 MPN characters. Per task convention, the dimensions emitted
to `blm_dimensions.csv` are those of the alphabetically-first
variant of each base; the other variants are listed here so a
reviewer can cross-check before encoding the IPC-7351B height.

- `BLM18EG221` (sample `BLM18EG221SN1`): observed (L, W, T_max) tuples in PIM = [(1.6, 0.8, 0.65), (1.6, 0.8, 0.95)]

## Reconstructed Specifications block (representative MPN: BLM18EG101TH1)

Source URL (for human verification in a real browser):
<https://www.murata.com/products/productdetail?partno=BLM18EG101TH1>

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
