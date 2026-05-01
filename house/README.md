# The House Footprint Library

This folder hosts the code that **autogenerates** the Altium footprint library (`build/house.PcbLib`) which every vendor DbLib in this repository links to (Panasonic, TDK, Samsung, Murata, …). The generated `house.PcbLib`, every intermediate STEP 3D model, and the merged footprint manifest all land in the repo's top-level `build/` directory (which is `.gitignore`d).

The build pipeline is fully automated end-to-end — Altium's IPC Compliant Footprints Batch Generator is **not** in the loop:

1. **Per-vendor footprint specifications.** Each `vendors/<vendor>/` script writes `build/footprints/<vendor>-footprints.json` listing every CAPC / RESC / INDC footprint × density variant (`L`, `N`, `M`) the vendor's database needs. Schema lives in [`vendors/_common.py`](../vendors/_common.py) and carries body geometry (`L × W × H`, terminal length `T`), the chip kind (C / R / I / FB), and a `drawingNote` source attribution traceable to a datasheet.
2. **Merge.** [`build_house_footprints.py`](build_house_footprints.py) consolidates every per-vendor JSON into `build/footprints/house-footprints.json`. When two vendors define a row with the same `name`, the priority list in [`settings.toml`](../settings.toml) at the repo root breaks the tie.
3. **Parametric STEP 3D models.** [`build_step_models.py`](build_step_models.py) reads the merged JSON and calls into the pure-Python geometry engine in [`stepgen/`](stepgen) to write one `build/step/<root>.step` per unique chip body. Because L / N / M density variants share an identical body, the generator dedupes by footprint root (e.g. `build/step/CAPC0402X20.step` is shared by `CAPC0402X20{L,N,M}`).
4. **`.PcbLib` autogeneration.** The pure-Python writer under [`altium_pcblib/`](altium_pcblib) consumes both the merged JSON and the STEP files, applies IPC-7351B pad math + the DDL-001 drawing standards (rounded-rect 25%-radius pads, 0.05 mm solder mask expansion with a bridge region whenever the natural sliver would fall under 0.1 mm, 3D body on Mech 1, outline + centroid on Mech 15, no silkscreen, no courtyard, library default units = mm), and emits `build/house.PcbLib` with each STEP model embedded inline (zlib-compressed). The driver script is [`build_pcblib.py`](build_pcblib.py).

Footprint names follow **IPC-SM-782**:

```
RESCxxyyXzzc
CAPCxxyyXzzc
```

- `xx` — nominal body length in 1/10ths of a millimeter
- `yy` — nominal body width in 1/10ths of a millimeter
- `zz` — nominal body **maximum height** in 1/100ths of a millimeter, rounded half up, zero-padded to a min of two digits (so 0.13 mm → `13`, 0.30 mm → `30`, 0.065 mm → `07`; heights ≥ 1.00 mm spill to three digits naturally, e.g. 1.25 mm → `125`, 2.85 mm → `285`)
- `c` — IPC-7351B density / material condition: **L** = least, **N** = nominal, **M** = most

All three density variants (`L`, `N`, `M`) share the same nominal body dimensions — they differ only in pad/courtyard size.

## Resistor footprints in `house.PcbLib`

| Footprint | EIA (inch) | Nominal L × W × H (mm) | Authoritative dimension source | Families in this library that use it |
| --- | --- | --- | --- | --- |
| `RESC0402X13{L,N,M}` | 01005 | 0.40 × 0.20 × 0.13 | PANASONIC **ERJ-XGN** (01005 thick-film chip datasheet) | PANASONIC ERJ |
| `RESC0603X23{L,N,M}` | 0201 | 0.60 × 0.30 × 0.23 | PANASONIC **ERJ-1GN / ERJ-1GJ / ERA-1A** (0201 thick-film & thin-film chip datasheets) | PANASONIC ERJ / ERA |
| `RESC1005X35{L,N,M}` | 0402 | 1.00 × 0.50 × 0.35 | PANASONIC **ERJ-2 / ERA-2** (0402 chip datasheets) | PANASONIC ERA / ERJ |
| `RESC1608X45{L,N,M}` | 0603 | 1.60 × 0.80 × 0.45 | PANASONIC **ERJ-3 / ERA-3** (0603 chip datasheets) | PANASONIC ERA / ERJ |
| `RESC2012X55{L,N,M}` | 0805 | 2.00 × 1.20 × 0.55 | PANASONIC **ERA-6V / ERA-6K** (0805 thin-film high-stability chip datasheet) | PANASONIC ERA |
| `RESC2012X60{L,N,M}` | 0805 | 2.00 × 1.20 × 0.60 | PANASONIC **ERJ-6** (0805 thick-film chip datasheet; also matches the 0.60 mm **ERA-6A** body) | PANASONIC ERJ |
| `RESC3216X55{L,N,M}` | 1206 | 3.20 × 1.60 × 0.55 | PANASONIC **ERA-8P** (1206 thin-film high-stability chip datasheet; same 0.55 mm body as the ERA-8V / ERA-8K 1206 parts, which we intentionally don't carry — at 1206 we only stock the 500 V ERA-P) | PANASONIC ERA |

## Capacitor footprints in `house.PcbLib`

| Footprint | EIA (inch) | Nominal L × W × H, Tx (mm) | Authoritative dimension source | Families in this library that use it |
| --- | --- | --- | --- | --- |
| `CAPC0603X30{L,N,M}` | 0201 | 0.60 × 0.30 × 0.3, 0.15 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC0603X33{L,N,M}` | 0201 | 0.60 × 0.30 × 0.33, 0.15 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC0603X39{L,N,M}` | 0201 | 0.60 × 0.30 × 0.39, 0.15 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC0603X55{L,N,M}` | 0201 | 0.60 × 0.30 × 0.55, 0.15 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC1005X50{L,N,M}` | 0402 | 1.00 × 0.50 × 0.5, 0.3 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC1005X55{L,N,M}` | 0402 | 1.00 × 0.50 × 0.55, 0.3 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC1005X60{L,N,M}` | 0402 | 1.00 × 0.50 × 0.6, 0.3 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC1005X65{L,N,M}` | 0402 | 1.00 × 0.50 × 0.65, 0.3 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC1005X70{L,N,M}` | 0402 | 1.00 × 0.50 × 0.7, 0.3 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC1608X80{L,N,M}` | 0603 | 1.60 × 0.80 × 0.8, 0.35 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC1608X90{L,N,M}` | 0603 | 1.60 × 0.80 × 0.9, 0.35 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC1608X100{L,N,M}` | 0603 | 1.60 × 0.80 × 1, 0.35 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC2012X60{L,N,M}` | 0805 | 2.00 × 1.25 × 0.6, 0.5 | TDK **CGA** | TDK CGA |
| `CAPC2012X70{L,N,M}` | 0805 | 2.00 × 1.25 × 0.7, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC2012X85{L,N,M}` | 0805 | 2.00 × 1.25 × 0.85, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC2012X95{L,N,M}` | 0805 | 2.00 × 1.25 × 0.95, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC2012X100{L,N,M}` | 0805 | 2.00 × 1.25 × 1, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC2012X125{L,N,M}` | 0805 | 2.00 × 1.25 × 1.25, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC2012X140{L,N,M}` | 0805 | 2.00 × 1.25 × 1.4, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC2012X145{L,N,M}` | 0805 | 2.00 × 1.25 × 1.45, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3216X60{L,N,M}` | 1206 | 3.20 × 1.60 × 0.6, 0.5 | TDK **CGA** | TDK CGA |
| `CAPC3216X85{L,N,M}` | 1206 | 3.20 × 1.60 × 0.85, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC3216X95{L,N,M}` | 1206 | 3.20 × 1.60 × 0.95, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3216X100{L,N,M}` | 1206 | 3.20 × 1.60 × 1, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3216X115{L,N,M}` | 1206 | 3.20 × 1.60 × 1.15, 0.5 | TDK **CGA** | TDK CGA |
| `CAPC3216X125{L,N,M}` | 1206 | 3.20 × 1.60 × 1.25, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3216X160{L,N,M}` | 1206 | 3.20 × 1.60 × 1.6, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC3216X180{L,N,M}` | 1206 | 3.20 × 1.60 × 1.8, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3216X190{L,N,M}` | 1206 | 3.20 × 1.60 × 1.9, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X100{L,N,M}` | 1210 | 3.20 × 2.50 × 1, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X125{L,N,M}` | 1210 | 3.20 × 2.50 × 1.25, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X150{L,N,M}` | 1210 | 3.20 × 2.50 × 1.5, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X160{L,N,M}` | 1210 | 3.20 × 2.50 × 1.6, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC3225X200{L,N,M}` | 1210 | 3.20 × 2.50 × 2, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA / MURATA GCM |
| `CAPC3225X220{L,N,M}` | 1210 | 3.20 × 2.50 × 2.2, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X250{L,N,M}` | 1210 | 3.20 × 2.50 × 2.5, 0.5 | SAMSUNG **CL** + TDK **CGA** (shared geometry in both families) | SAMSUNG CL / TDK CGA |
| `CAPC3225X265{L,N,M}` | 1210 | 3.20 × 2.50 × 2.65, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X270{L,N,M}` | 1210 | 3.20 × 2.50 × 2.7, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC3225X285{L,N,M}` | 1210 | 3.20 × 2.50 × 2.85, 0.5 | MURATA **GCM** (Murata PIM bulk list + `../vendors/murata/reference/murata_gcm.pdf`) | MURATA GCM |
| `CAPC4532X160{L,N,M}` | 1812 | 4.50 × 3.20 × 1.6, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC4532X200{L,N,M}` | 1812 | 4.50 × 3.20 × 2, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC4532X230{L,N,M}` | 1812 | 4.50 × 3.20 × 2.3, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC4532X250{L,N,M}` | 1812 | 4.50 × 3.20 × 2.5, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC4532X320{L,N,M}` | 1812 | 4.50 × 3.20 × 3.2, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC5750X200{L,N,M}` | 2220 | 5.70 × 5.00 × 2, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC5750X230{L,N,M}` | 2220 | 5.70 × 5.00 × 2.3, 0.6 | TDK **CGA** | TDK CGA |
| `CAPC5750X250{L,N,M}` | 2220 | 5.70 × 5.00 × 2.5, 0.6 | TDK **CGA** | TDK CGA |
## Notes

- **Resistors:** **0805** carries two height variants (`RESC2012X55` vs. `RESC2012X60`) because Panasonic's newer high-stability thin-film line (**ERA-V/K**) has a 0.55 mm body, while the **ERJ** thick-film line uses a 0.60 mm body at 0805. **1206** only carries the 0.55 mm variant (`RESC3216X55`) because we don't stock any 1206 thick-film parts; if a 1206 thick-film family (ERJ-8, ERA-8A, etc.) is ever added to the library, append a matching row to `vendors/panasonic/panasonic-resistors.py`'s `RESC_FOOTPRINTS` table and re-run `make all`.
- **Capacitors:** `Tx` above is the terminal/band length stored in `bodyMm.terminalLengthNominal` of each per-vendor JSON. `H` is the body max height (`bodyMm.heightNominal`).
- The data tables above are reference documentation; the canonical list lives in `build/footprints/house-footprints.json` and is rebuilt on every `make all`.
- **Adding a new footprint.** Edit (or add) the relevant `vendors/<vendor>/<vendor>-*.py` script so it emits a row for the new size, then run `make all`. Conflicts on `name` are resolved deterministically by [`settings.toml`](../settings.toml)'s priority list, so adding a duplicate-named footprint with a different geometry under a higher-priority vendor will override the existing one without a silent collision.

