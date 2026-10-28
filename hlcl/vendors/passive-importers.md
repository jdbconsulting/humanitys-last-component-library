# Datasheet-backed passive importers

Reviewed 2026-09-17. These additions run offline in both Python and the browser.
Each `parts.csv` is shipped in the browser source archive. The importers emit
an XLS, DbLib, and footprint sidecar; the house build supplies the symbols,
land patterns, embedded STEP models, and PcbLib.

## Initial catalog scope

| Build target          | Initial scope                                                                                                                                                                 |               Rows |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -----------------: |
| `murata-gcd`          | Active GCD188/GCD21B PIM catalog; 0603 paper D and 0805 embossed L packaging; X7R plus one X7S entry                                                                          |                109 |
| `murata-krm`          | KRM55QR72A106KH01, L/K packaging                                                                                                                                              |                  2 |
| `kemet-open-mode`     | Verified automotive open-mode X7R codes, 0603/1210                                                                                                                            |                  2 |
| `kemet-esd-c0g`       | Verified automotive C0G ESD code, 0805                                                                                                                                        |                  1 |
| `kemet-x7r`           | Verified commercial X7R codes, 0402/0805                                                                                                                                      |                  2 |
| `tdk-c`               | Verified commercial X7R C1005/C3225 codes, 0402/1210                                                                                                                          |                  2 |
| `vishay-crcw`         | 1% E24/E96 and 5% E24 in every TCR grade the datasheets list, 1 ohm–10 Mohm (1218: 2.2 Mohm), plus jumpers; 0201–2512; one valid reel format per size; database-standard rows |             10,034 |
| `vishay-tnpw`         | Every TCR (±50/25/15/10 ppm), tolerance (1/0.5/0.1%) and E24/E96/E192 value both datasheets list, 0201–1210; e3 by default, SnPb opt-in; one valid reel format per size       | 58,164 (37,622 e3) |
| `vishay-rcs`          | E24/E96, 1 ohm–10 Mohm, 1%/100 ppm, plus jumpers; 0402–1206; one valid reel format per size                                                                                   |              3,200 |
| `vishay-rcp`          | Two verified wide-terminal codes, 0603/2512; decoder also supports reviewed 1206 geometry                                                                                     |                  2 |
| `vishay-mc-precision` | MC version 0, 0.1%/25 ppm; E24/E96 subset of the published E24/E192 range; 0402–1206                                                                                          |              1,882 |
| `vishay-mc-at`        | MC version M, 0.1%/25 ppm; E24/E96 subset of the published E24/E192 range; 0402–1206                                                                                          |              2,226 |

CRCW, RCS and MC lists describe combinations permitted by their ordering tables;
they are **not distributor stock or availability assertions**. Other new
families start with bounded catalog selections, not every possible combination
of voltage, capacitance, thickness and packing codes. Particularly, the KRM
importer does not assign the KRM55Q geometry to other KRM packages.

Existing importers also gain ERA-2AEB/ERA-2ARB 0402, Samsung's two verified
automotive CL bases, and Yageo AC1210. Samsung packaging alternates remain in
the existing MPN 2/3 fields. AC1210 support is restricted to AC; RC/RT are not
silently expanded using AC geometry. The Everything preset and factory defaults
include the new families and sizes; focused presets retain their selections.

## Sources and decisions

| Source                                                                                                                                                                                                                                                                                                                                                                               | Reviewed details                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Vishay D/CRCW e3, document 20035](https://www.vishay.com/docs/20035/dcrcwe3.pdf), 14-Apr-2026                                                                                                                                                                                                                                                                                       | F/J tolerance with K/N TCR, size-specific packing, jumper current, standard/extended P70 ratings, T1 bottom/T2 top terminals and AEC-Q200.                                                                                                                                                |
| [Vishay CRCW0201 e3, document 20052](https://www.vishay.com/docs/20052/crcw0201e3.pdf), 21-Sep-2022                                                                                                                                                                                                                                                                                  | Commercial 0201: K/N/X TCR grades and their ranges, 0.05 W/30 V, 50 mOhm/1 A jumper, ED/EE/EI packing, T1 bottom/T2 top terminals. No AEC-Q200 claim.                                                                                                                                     |
| [Vishay TNPW e3, document 28758](https://www.vishay.com/docs/28758/tnpw_e3.pdf), 10-Apr-2026                                                                                                                                                                                                                                                                                         | TCR/tolerance/range grid per size, E24/E96 at 1% and E24/E192 tighter, B/D/F and H/E/X/Y codes, ED/EA/EC reels (EC only 25/50 ppm), general/power/advanced P70, Tt = Tb dimensions, AEC-Q200. 2010/2512 appear only in revisions up to 2012. TNPU (ultra precision) is a separate series. |
| [Vishay TNPW SnPb, document 31006](https://www.vishay.com/docs/31006/tnpw.pdf), 18-Feb-2025                                                                                                                                                                                                                                                                                          | Lead-bearing variant, 0402–1210: narrower grade grid, TD/TP/TA/CN reels (TP/CN only 0.1%), P70/Umax, identical dimensions.                                                                                                                                                                |
| [Vishay RCS, document 20065](https://www.vishay.com/docs/20065/rcse3.pdf), 11-Jun-2025                                                                                                                                                                                                                                                                                               | Resistance/tolerance/TCR combinations, size-specific packing, jumper current, P70 ratings, top/bottom terminal dimensions and derating.                                                                                                                                                   |
| [Vishay RCP, document 31098](https://www.vishay.com/docs/31098/rcp.pdf), 10-Aug-2021                                                                                                                                                                                                                                                                                                 | W/B terminal geometry, manufacturer's recommended lands, 10–2,000 ohm range, packing and thermal conditions.                                                                                                                                                                              |
| [Vishay MC Precision, document 28700](https://www.vishay.com/docs/28700/mcx0x0xpre.pdf), 02-Dec-2025                                                                                                                                                                                                                                                                                 | Version 0, resistance-code exponent, 0.1%/25 ppm limits, precision-mode ratings, IECQ-CECC and dimensions.                                                                                                                                                                                |
| [Vishay MC AT, document 28952](https://www.vishay.com/docs/28952/mcr0201at-mca1206at.pdf), 28-May-2026                                                                                                                                                                                                                                                                               | Version M, AEC-Q200, resistance limits, packing and general/power/advanced operating modes.                                                                                                                                                                                               |
| [KEMET X7R](https://content.kemet.com/datasheets/KEM_C1002_X7R_SMD.pdf), [open mode](https://content.kemet.com/datasheets/KEM_C1012_X7R_OPENMODE_SMD.pdf), [ESD C0G](https://content.kemet.com/datasheets/KEM_C1091_C0G_ESD.pdf)                                                                                                                                                     | Ordering-code fields, dielectric, qualification and function. Each CSV also links its exact KEMET part specification, used for dimensions and packing.                                                                                                                                    |
| [Murata GCD188 reference](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GCD188R72A472KA01-01.pdf), [GCD21B reference](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GCD21BR72A104KA01-01A.pdf)                                                                                                                                                             | MLSC construction, package/terminal limits and packing. Electrical data and active status from Murata PIM export acquired 2026-09-17.                                                                                                                                                     |
| [Murata KRM55 reference](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/KRM55_25V-100V_E.pdf), Jul-2025                                                                                                                                                                                                                                                                  | Part list, single-chip Q outline, metal feet, L/K packing; land dimensions on printed p.24.                                                                                                                                                                                               |
| [TDK C1005 exact product](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X7R1H473K050BB), [C3225 characterization](https://product.tdk.com/system/files/dam/doc/product/capacitor/ceramic/mlcc/charasheet/c3225x7r2a225k230ab_200123.pdf), [C mid-voltage catalog](https://product.tdk.com/info/en/catalog/datasheets/mlcc_commercial_midvoltage_en.pdf) | Dimensions, minimum terminations, maximum height, recommended land ranges, commercial qualification and exact AB/BB ordering codes.                                                                                                                                                       |
| `panasonic/era-a/reference/panasonic_era-a.pdf`, 24-Apr-2024                                                                                                                                                                                                                                                                                                                         | ERA-2ARB 200 ohm–47 kohm, 0.1%, 10 ppm; ERA-2AEB 47 ohm–100 kohm, 0.1%, 25 ppm; 0.063 W at 85 C, 50 V limit, Grade 1.                                                                                                                                                                     |
| [Samsung CL10](https://product.samsungsem.com/mlcc/CL10B223KC8WPN.do), [CL31](https://product.samsungsem.com/mlcc/CL31B474KCHWPN.do) and their downloadable reference sheets                                                                                                                                                                                                         | Exact C/D and E/F packing respectively; AEC-Q200; maximum heights 0.9/1.8 mm, bands 0.30/0.50 mm. Reference sheets describe both as open-mode, despite the product page's broad “Normal” label.                                                                                           |
| [Yageo AC1210 exact specification](https://www.yageogroup.com/component-documentation/download/specsheet/AC1210FR-0760R4L)                                                                                                                                                                                                                                                           | 3.10 × 2.60 mm, maximum height 0.65 mm, top/bottom bands 0.45/0.50 mm; 0.5 W at 70 C, 200 V limiting voltage.                                                                                                                                                                             |

The requested TDK `C3225X7R2A225K230DB` is offered by distributors, but an exact
manufacturer specification for its DB suffix could not be verified. The initial
catalog therefore includes the documented `C3225X7R2A225K230AB` as a candidate
substitute. It does not fabricate a DB entry from the AB data. Check reel format
and the delivery specification before making that substitution.

CRCW 0402–0805 use the **standard operation mode** P70/Umax (0.063 W/50 V,
0.1 W/75 V, 0.125 W/150 V). The datasheet's headline table quotes the extended
mode, which permits twice the 1000 h drift. The 1%/200 ppm `FN` grade exists only
for 1–9.76 ohm; the catalog lists it alongside `FK` for those values. CRCW and RCS lands use the bottom terminal T1; the top terminal
T2 only shapes the model. CRCW 1218 and 2010 add those sizes to the global case-size list.

CRCW 0201 comes from a separate commercial datasheet without AEC-Q200, so its
`Qual` is blank. Its grades overlap: `FK` (100 ppm) covers 47 ohm–1 Mohm, `FN`/`JN`
(200 ppm) 10 ohm–10 Mohm, and `FX`/`JX` (-200/+400 ppm) values below 10 ohm. The
catalog lists every grade for every value, so 10 kOhm 1% appears as both
`CRCW020110K0FKED` and `CRCW020110K0FNED`. A unit test checks that the catalog
holds every grade/value the decoder accepts for each size's reel.

The CRCW importer's `select` applies two Libraries-tab options before writing:
`tcr_options` (K = ±100, N = ±200, X = -200/+400 ppm; all by default) and
`lowest_tcr_only`, which keeps the tightest ticked TCR per size, value, tolerance
and reel (8,627 parts with every TCR ticked). Each row lists the size's other
datasheet reels in the opt-in `alternates` columns (MFG/MPN 2-5): 0603 `EA` carries
`EC`, `ED`, `EE` and `EI`; 1218 and 2010 have only one reel.

Every workbook follows the website's database standard (`/docs/database-standards/`),
written through `vendors/_standard.py`: standard columns first, in order, then any
extra columns the family enabled. These importers can add Power (resistors),
Features, Rating Conditions and Datasheet, chosen per family under the Libraries
tab's `extra_parameters` option (none by default). Descriptions read
`RESISTOR THICK FILM 4.7K OHM 5% 0603` or `CAPACITOR CERAMIC 10NF 10% 100V X7R 0402`,
and jumpers `RESISTOR JUMPER 0 OHM 0402`. A row with a non-ASCII field or a malformed
description or parameter fails the build.

TNPW e3 uses the **general operation mode** P70 (0.05–0.33 W, film <=125 C), not
the headline power/advanced figures, which allow more drift; `Tr` is therefore
-55:125. SnPb parts use their own P70/Umax (for example 0402 is 0.063 W/50 V
against 0.07 W/75 V for e3). Both finishes share one geometry per size, so they
share footprints. Its catalog is generated from `TNPW_RANGES` in the decoder; the
importer's `select` applies the Libraries-tab options: `terminations` (e3 by
default, SnPb opt-in), `value_series` (`e192` default, or `e96` for E24/E96
only), and the shared `select_grades` for `tcr_options`, `tolerance_options` and
`lowest_tcr_only`. Alternates list the EC reel for 25/50 ppm e3 parts and the
1,000-piece TP/CN reel for 0.1% SnPb parts.

RCS uses ambient **P70**, not the higher terminal-temperature rating. MC AT uses
the **general operating mode** at P70 and a 125 C film limit; higher-power modes
also permit greater drift and are not silently advertised as precision ratings.
RCP uses **P25 on the standard test board** (1.5 W for 0603 and 3.5 W for 2512),
not the 3.9/22 W actively cooled limits. Its working voltage is derived from
sqrt(P × R), rounded down. For resistors carrying a fixed voltage limit, the
actual operating voltage must also satisfy sqrt(P × R).

KEMET open-mode F is not flexible termination. C0G ESD capability is the
component-level AEC-Q200-002 HBM rating, not an IEC system ESD claim. GCD's
internal series construction is retained in `Features`; ordinary MLCCs should
not be described as equivalent solely because their capacitance matches.

## Geometry contract

New footprint roots may include an uppercase qualifier before the final density
letter: `RESC6332X64_RCPWN`. This prevents different manufacturers or terminal
styles with similar body sizes from being merged into the wrong footprint.
`_common.footprint_root` applies each family's `footprint_names` option when a
footprint is named: vendor-specific (the default) keeps the qualifier or adds the
family tag from `FAMILY_QUALIFIERS`; generic drops it, and fails if that would
merge two different geometries from one family.
New entries use nominal length/width and maximum height. The legacy schema field
is still named `heightNominal`; its conservative use is recorded in `drawingNote`.

`landPatternMm` optionally specifies `padLength`, `padWidth`, and the inner `gap`.
RCP and KRM use the manufacturer lands unchanged for all density selections;
density still controls the courtyard. TDK uses the midpoint of its recommended
land ranges. These are not claimed to be three distinct IPC pad calculations.
GCD terminal lengths use the midpoint of the published e limits.

`model.type = wide-bottom` preserves separate top and bottom terminal bands for
CRCW, RCP/RCS, ERA-2A and AC1210. `model.type = metal-terminal` supplies a raised ceramic
and folded metal feet for KRM55Q. Its overall 6.1 × 5.3 × 3.9 mm envelope and
1.2 mm feet are specification-based; hidden ceramic details, metal thickness,
and standoff are visual approximations. It is an assembly model, not a tooling
model. STEP solids and Altium body heights remain in millimetres with explicit
unit conversion in the Altium writer.

## Extending and verifying

For a capacitor, add an exact supported code to the family's `parts.csv`, with
the electrical data, nominal/max dimensions, terminal data, source URL and a
geometry identifier. Reuse a geometry identifier only when **all** geometry and
provenance fields agree. Obtain dimensions from the exact specification; a
capacitance/voltage prefix alone does not establish thickness. Unsupported
code families require a reviewed decoder change, not a guessed CSV entry.

For Vishay, add an exact supported MPN to `parts.csv`. The decoder supplies the
reviewed size/rating/geometry tables and rejects unsupported ranges/packing.
The initial CRCW/RCS/MC lists use the union of the repository's E24/E96 values,
scaled by decades and clipped to the datasheet limits. CRCW and RCS use embedded R/K/M
decimal codes; MC always uses three significant figures and an exponent
(9 = -1, 8 = -2 where applicable). ERA-A retains its separate E24/E96 convention.

Each new `importer.py` accepts `--input PATH` for a reviewed alternative catalog.
Network fetching is not part of a build. For another Murata PIM snapshot, the
existing `murata/fetch_gcm_pim.py --part-prefix GCD --output PATH` tool can retrieve
the source data; normalize it into the explicit schema only after reviewing
new geometries, controls and packing codes.

```sh
npm run regen
python -m unittest discover -s tests -v
python hlcl/build.py all
python tests/audit_passive_artifacts.py
npm run check
npm run build
```

The unit suite checks datasheet examples, malformed inputs, ERA-A mixed codes,
Samsung packing/qualification, and manufacturer lands through the PcbLib
generator. The artifact audit checks requested coverage, all workbook footprint
references, embedded-model files, and STEP coordinate bounds. Optional Open
Cascade validation can additionally check solid topology without adding a CAD
dependency to production builds.
