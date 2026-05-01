# The Be-Done-With-It-Passives Footprint Library

Are you tired of messing around with passive footprints? Want to get an Altium footprint library that does it correctly? This library is for you!

![Coupon board screenshot](docs/coupon-board-screenshot.png)

## Limitations

This library is limited to chip resistors and chip capacitors between 01005 (metric 0402) and 1210 (metric 3225). To calculate 3D model and landing pad dimensions, certain dimensions are needed from the chip, such as terminal width, height, and tolerances. So it isn't possible to make a truly generic footprint library. No highly optimized footprint library can really be generic.

## The Philosophy

IPC-SM-782 was one of the original standards documents to define Printed Circuit Board (PCB) land patterns for Surface Mount Devices (SMD). Originally published in 1996, it was later superseded by IPC-7351 in 2005. IPC-7351 was then revised in 2007 and 2010. This library is based on the IPC-7351 2010 guidelines.

However, the guidelines do not fully define land pads. Rather, they specify three classes of PCB fabrication and assembly tolerances and corresponding solder fillets *given* component tolerances. These component tolerances must come from the designer.

So, what component tolerances do we use? The JEDEC standardization body defines a list of standardized two-terminal chips.

....

### On the Question of 3D Tolerances

When mechanical engineers are taking a 3D model of a printed circuit board for enclosure or heatsink design, they'll often ask if the component dimensions are nominal or max. If they're designing a compression thermal pad, they need to know the minimum and maximum component dimensions. Having 3D bodies that represent the maximum dimensions as provided by the manufacturer can be useful to ensure clearances to adjacent components are guaranteed, but this is not the only use case. Designing a thermal pad is an example where having maximum dimensions can lead to a lack of thermal contact. Therefore, this library uses the nominal component dimensions in its 3D models.

## The Library

Different organizations make different layer, drafting, solder mask, paste mask, courtyard, and 3D-body choices. This library intentionally uses a minimal footprint artwork set:

1. Pads
    a. Land dimensions calculated from IPC-7351B (2010) solder-joint goals for the selected density level.
    b. Paste mask expansion is rule-based and defined at the PCB document level.
    c. Solder mask expansion is manually set to 0.05 mm (1.97 mil).
    d. SMD pads use rounded-rectangle geometry with a 25% corner radius.
    e. Component body length, body width, and height tolerance inputs are set to ±0% unless otherwise stated.
    f. Terminal/band length assumptions are family-specific: RESC uses Panasonic ERJ-family dimensions; CAPC uses Samsung CL-family dimensions.

2. Component outline on Mechanical 15.
3. Component centroid/origin mark on Mechanical 15.
4. 3D model on Mechanical 1.

The IPC-calculated pad dimensions are used except for `CAPC0402*`, `CAPC0603*`, and `RESC0402*`, where the pads are adjusted to preserve at least 0.10 mm solder-mask web between adjacent pads.

Footprints are named using the IPC-7351B land-pattern naming convention for chip resistors and chip capacitors:

```text
RESC{LL}{WW}X{H}{D}
CAPC{LL}{WW}X{H}{D}
```

where:

- `RESC` / `CAPC`: IPC package-family prefix for chip resistors / chip capacitors.
- `LL`: nominal component body length in 0.1 mm units, encoded with one digit on each side of the decimal point.
- `WW`: nominal component body width in 0.1 mm units, encoded with one digit on each side of the decimal point.
- `H`: nominal component height in 0.01 mm units. The value is encoded by formatting the height with two decimal places, removing the decimal point, and removing leading zeros before the decimal point only. Therefore `0.05 mm -> X05`, `0.65 mm -> X65`, `1.00 mm -> X100`, and `2.50 mm -> X250`.
- `D`: IPC density-level suffix: `L` for least, `N` for nominal, or `M` for most.
## Structure

Every vendor `.xls` workbook in this repository follows the same column schema, captured canonically in [`resistor_template.xlsx`](resistor_template.xlsx). Columns are split into five groups; the first two groups carry the human-facing identity of the part, the third carries electrical parameters used for filtering / BOM, and the last two tell Altium where to fetch the schematic symbol and PCB footprints when the part is placed. Example values below show one row for `ERJ-XGNF10R0`:

![Database row schema, one row per MPN](docs/database-example.png)

Notes:

- `Comment` is the row's key field — it's what the `*.DbLib` binds as its `Single key lookup` database field (see [Regenerating the Databases](#regenerating-the-databases) for the gotcha that tripped us up here). Keeping `Comment = MPN` is the simplest convention and what every script in this repo does.
- `Description` follows the form `<CONSTRUCTION> <VALUE> <TOLERANCE> <CASE>` (e.g. `RESISTOR THICK FILM 10 OHM 1% 01005`) so it's human-scannable at BOM time without a schematic.
- The three `Footprint Path` / `Footprint Ref` pairs hold the three IPC-7351 density variants for the same physical part. This library follows IPC-7351B's **L**/**N**/**M** suffix convention (**L**east / **N**ominal / **M**ost), which is the same concept the older IPC-SM-782 "A/B/C" labels referred to. Which variant the PCB actually uses is a board-level choice made via Altium PCB rules, not encoded here.
- `Library Path` and `Footprint Path` are resolved by Altium relative to the `*.DbLib` file's location (put a `.\` prefix in front of a bare filename to force Altium into "relative path" resolution mode, otherwise it falls through to `LibrarySearchPath` lookup). Current vendor scripts write `.\house.SchLib` / `.\house.PcbLib` — the `panasonic.SchLib` / `panasonic.PcbLib` values shown in the template are legacy illustrative values from before the shared `house.*` libraries landed.
- Columns in **Required** and **Highly recommended** groups should never be blank for a row. **Optional** fields may be blank on a per-MPN basis when the datasheet doesn't quote the value (e.g. non-automotive parts legitimately have a blank `Qual`).


## Setup

The build has two host-side prerequisites:

1. **Python 3.11+** — the per-vendor generator scripts, the `house-footprints` merge, and the parametric STEP generator are all Python; 3.11 is the floor because the merge reads `settings.toml` via the stdlib `tomllib`. The only third-party dep pinned in [`requirements.txt`](requirements.txt) is `xlwt` (writes the database `.xls` files Altium's DbLib reads). Everything else — the per-vendor footprints JSONs, the merge, and the STEP geometry engine — is pure stdlib.
2. **.NET 8 SDK** — the `house-pcblib` target runs a small C# project under [`house/HouseLibGenerator/`](house/HouseLibGenerator) that consumes the merged JSON sidecar and writes `build/house.PcbLib` directly (using the [`OriginalCircuit.AltiumSharp`](https://www.nuget.org/packages/OriginalCircuit.AltiumSharp) NuGet package). This replaces the older "feed the .xls into Altium's IPC Compliant Footprints Batch Generator and hand-tweak every footprint" workflow.

### Python virtualenv

**Linux / macOS / WSL** — replace `python3.12` below with whatever ≥3.11 interpreter you have on `PATH` (`python3.11`, `python3.13`, …):

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

> On Debian/Ubuntu (WSL included) the `venv` module ships in a separate apt package per minor version. If `python3.X -m venv` errors with `No module named ensurepip`, install the matching package: `sudo apt install python3.12-venv` (or `python3.11-venv`, etc.).

**Windows (PowerShell or cmd)**

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Once the venv is activated, plain `python` resolves to the venv's interpreter, so the default `make` recipes work without any override.

### .NET 8 SDK

`make house-pcblib` (and therefore `make all`) requires the .NET 8 SDK on `PATH`. The project file pins `<TargetFramework>net8.0</TargetFramework>` because the published `OriginalCircuit.AltiumSharp 1.0.2` NuGet package targets `net6.0` and we run it from a `net8.0` exe; .NET 9 or newer also works as long as `net6.0` runtime compatibility is preserved.

**Linux / macOS / WSL — official install script (no sudo, installs into `~/.dotnet`):**

```bash
curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
chmod +x /tmp/dotnet-install.sh
/tmp/dotnet-install.sh --channel 8.0 --install-dir "$HOME/.dotnet"
export PATH="$HOME/.dotnet:$PATH"   # add this to ~/.bashrc / ~/.zshrc to persist
```

Verify with `dotnet --info` (should report `8.0.x`).

If you'd rather use your distro's package manager: on recent Ubuntu/Debian `sudo apt install dotnet-sdk-8.0` works, on macOS `brew install --cask dotnet-sdk`, and on Fedora `sudo dnf install dotnet-sdk-8.0`.

**Windows** — install the [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) from the official Microsoft page (the installer adds it to `PATH` automatically). Verify with `dotnet --info` in a new shell.

The first `make all` after a clean checkout will pull `OriginalCircuit.AltiumSharp` from NuGet on demand; subsequent builds are offline.

### One-shot

After both prerequisites are installed and the Python venv is activated:

```bash
make all
```

If you'd rather not activate the venv (or you want to use a system Python or a non-`PATH` dotnet), pass overrides to `make` — see [Building with make](#building-with-make) below.

> **WSL note — `Permission denied` on `make clean`**
>
> When the project lives on a Windows drive (e.g. `/mnt/d/...`) and any of the `build/*.xls` database workbooks or `build/house.PcbLib` are open on the Windows side (Excel on the workbooks, Altium on the .PcbLib), `rm` from inside WSL can't delete them and `make clean` aborts. Close the offending app and re-run.

## Building with make

Use the project `Makefile` to run generators consistently:

- `make` or `make all` - build everything (vendor `.xls`s + per-vendor footprint JSONs + merged JSON + 3D STEP models + `build/house.PcbLib`)
- `make panasonic` - build `build/panasonic-resistors.{xls,DbLib}` + `build/footprints/panasonic-resistors-footprints.json`
- `make tdk-capacitors` - build `build/tdk-capacitors.{xls,DbLib}` + matching footprints JSON
- `make samsung-capacitors` - build `build/samsung-capacitors.{xls,DbLib}` + matching footprints JSON
- `make murata-capacitors` - build `build/murata-capacitors.{xls,DbLib}` + matching footprints JSON
- `make murata-ferrites` - run the placeholder Murata ferrite generator
- `make house-footprints` - merge per-vendor footprints JSONs into `build/footprints/house-footprints.json`
- `make house-step-models` - generate parametric 3D STEP models in `build/step/*.step` via `house/stepgen/`
- `make house-pcblib` - autogenerate `build/house.PcbLib` from the merged JSON + STEP models (calls into `house/HouseLibGenerator/`)
- `make clean` - remove every procedurally-generated file from `build/` plus the C# `bin/`/`obj/` caches

You can override the tool launchers if needed (useful when you don't want to activate the venv created in [Setup](#setup), or when the system `python` isn't 3.11+, or when `dotnet` isn't on `PATH`):

- `make PYTHON=py all` (Windows Python launcher)
- `make PYTHON=python3.12 all` (Linux/macOS without an activated venv)
- `make PYTHON=.venv/bin/python all` (point directly at a non-activated venv)
- `make DOTNET=$HOME/.dotnet/dotnet all` (when `dotnet` isn't on `PATH`)

# Regenerating the Databases

Each vendor has a Python script under `vendors/<name>/` (e.g. `vendors/panasonic/panasonic-resistors.py`, `vendors/tdk/tdk-capacitors.py`) that emits two artifacts per script:

1. `build/<vendor>.xls` — the database workbook the vendor's `*.DbLib` binds to (one row per MPN). Excel 97-2003 BIFF8 written via `xlwt`.
2. `build/footprints/<vendor>-footprints.json` — the per-vendor footprint specification: one entry per unique CAPC / RESC footprint × density variant (`L`, `N`, `M`) the database above references. Each entry carries body geometry (`L × W × H`, terminal length `T`), a `kind` field (C / R / I / FB), and a `drawingNote` source attribution (e.g. _"Dimensions from Panasonic ERJ-XGN (01005 thick film)"_). The schema is defined and validated in [`vendors/_common.py`](vendors/_common.py).

Once every per-vendor script has run, `house/build_house_footprints.py` (wired into `make all` via the `house-footprints` target) merges every `build/footprints/*-footprints.json` into a single `build/footprints/house-footprints.json` — the canonical input for both the STEP 3D model generator and the .PcbLib autogenerator. When two vendor JSONs define a row with the same `name` (e.g. Samsung CL and TDK CGA both define `CAPC1005X50N`), the merge breaks ties using the priority list in [`settings.toml`](settings.toml) at the repo root — the vendor that appears first wins. The merge logs every conflict it resolves on stderr.

> **Adding a new vendor.** Drop a script under `vendors/<vendor>/` that calls `_common.write_footprints_json` with the unique CAPC/RESC/INDC footprints it requires (the existing scripts are good templates). Add the JSON path to the Makefile's `VENDOR_FOOTPRINT_JSON` list and the merge step picks it up automatically. Add the vendor key to `settings.toml`'s `house_footprints.priority` to control tie-break behaviour.

## Autogenerating 3D STEP models (`build/step/*.step`)

`make house-step-models` (in `make all`) runs [`house/build_step_models.py`](house/build_step_models.py) which delegates to the geometry engine in [`house/stepgen/`](house/stepgen). The IPC-7351B density variants (`L` / `N` / `M`) only change the pad geometry — the component body itself is identical — so the generator deduplicates by *footprint root* (FootprintName minus its trailing density letter) and emits **one STEP per unique chip body**:

```
build/step/CAPC0402X20.step    ← shared by CAPC0402X20{L,N,M}
build/step/RESC0402X13.step    ← shared by RESC0402X13{L,N,M}
...
```

The C# .pcblib autogenerator strips the same density suffix when looking up each footprint's STEP file, so all three density variants in `build/house.PcbLib` reference (and zlib-embed) the same STEP body. After `make all`, no external STEP files are required for the .PcbLib to render in Altium — but the on-disk copies are kept for inspection in any STEP viewer.

The generator is intentionally **pure-stdlib Python** — no CadQuery, no FreeCAD, no OpenCASCADE bindings — for two reasons:

1. The whole module can run unmodified in [Pyodide](https://pyodide.org/) so a future browser-based UI can let engineers drag dimensions around and watch the 3D model update live.
2. A clean checkout has no native-binary CAD dependencies to install: just CPython 3.11+ and the two pure-Python deps in [`requirements.txt`](requirements.txt).

Per-family layering today:

| Family | Pieces | Edges | Body colour | Terminal colour |
|---|---|---|---|---|
| CAPC | dielectric body + 2 terminals | filleted (`r=0.05 mm`) | MLCC tan `#B7860B` | Sn silver `#CCCCCC` |
| INDC, FB | ferrite body + 2 terminals | filleted (`r=0.05 mm`) | ferrite blue `#264D94` | Sn silver `#CCCCCC` |
| RESC | alumina substrate + passivation cover + 2 C-shaped terminals (3 sub-pieces each) | sharp | substrate `#9E9E9E` / passivation `#171717` | darker grey `#808080` |

CAPC and INDC bodies use a 26-face filleted-box B-rep (6 main planes + 12 cylindrical edge fillets + 8 spherical corner octants), matching the Altium IPC LP Wizard output style. The fillet radius is clamped to `min(L, W, H) / 4` per box so it never eats more than 1/4 of any dimension — on tiny CAPC0402X20 footprints (W=0.2 mm) the fillet shrinks gracefully to 0.05 mm and remains visible.

RESC stays sharp-edged (no fillets) and instead uses a layered geometry that mirrors a real chip resistor: each "C"-shaped terminal is built from three flush sub-boxes (end-cap + top wrap + bottom wrap) so the terminal wraps around the substrate; the alumina substrate sits between the two C-terminals raised off the floor by the metallisation thickness; the passivation cover fills the top sandwich slot, flush with the terminal tops.

## Autogenerating `build/house.PcbLib`

`make house-pcblib` (also wired into `make all`) runs [`house/HouseLibGenerator/`](house/HouseLibGenerator), a small C# project that turns the JSON sidecar plus the parametric STEP files into `build/house.PcbLib` directly — no Altium IPC Batch Generator round-trip and no manual per-footprint tweaks. The generator applies:

- **IPC-7351B Tables 3-5/3-6 pad math** — toe `J_T`, heel `J_H`, side `J_S`, and round-off granularity per density level (L/N/M); fab tolerance `F = 0.10 mm` and placement tolerance `P = 0.05 mm` per IPC-7351B §3.1.3. The component-tolerance term `C` is zero by repo policy (the JSON sidecar enforces `Lmin == Lmax` etc. before the C# program ever runs). See [`house/HouseLibGenerator/IpcRules.cs`](house/HouseLibGenerator/IpcRules.cs) and [`PadCalculator.cs`](house/HouseLibGenerator/PadCalculator.cs).
- **DDL-001 drawing standards** — rounded-rectangle pads with 25% corner radius on Top Layer; manual 0.05 mm solder mask expansion per pad; outline + centroid on Mechanical 15 with 0.1 mm line width; embedded parametric 3D model (zlib-compressed STEP) on Mechanical 1 at the nominal `L × W × H`; no silkscreen, no courtyard. See [`docs/standards/DDL-001.tex`](docs/standards/DDL-001.tex) and [`house/HouseLibGenerator/DdlConventions.cs`](house/HouseLibGenerator/DdlConventions.cs).
- **Minimum solder mask sliver enforcement** — DDL-001 §11.2.5 requires ≥ 0.1 mm solder mask sliver between adjacent pad apertures. When IPC's calculated `G` falls below `0.1 + 2 × 0.05 = 0.20 mm`, the generator shrinks the pads inward (keeping the centre spacing fixed, only pulling the toe back) and prints a "pad shrunk" diagnostic to stderr so the deviation is auditable. The families that hit this in the current dataset are CAPC0402, CAPC0603, RESC0402, and RESC0603 — the same families the previous hand-tuned library carried adjustments for.

Two implementation notes worth flagging:

1. **The library used is `OriginalCircuit.AltiumSharp 1.0.2`** (the v1 release on NuGet). The v2 rewrite at [github.com/issus/AltiumSharp](https://github.com/issus/AltiumSharp) has a much more complete primitive model but is `2.0.0-alpha.1 (Unreleased)` and isn't published; if a future iteration of this library needs custom-shape solder mask apertures or other features missing from v1, switching to v2 (consumed as a git submodule) is the planned escape hatch.
2. **Two v1 writer-vs-reader parity bugs are worked around in the body emission**: v1's `ParameterCollection.Add(string, Coord)` and `Add(string, double)` write a bare key with no value when the value is `0`, but the matching `AsCoord()` / `AsDouble()` reader paths strict-parse and throw on the empty value. To keep the file friendly to round-tripping tools (and to defend against any other parser that strict-parses the same fields), the chip-body emitter sets every otherwise-zero `Coord` and `double` to a sub-display-precision value. See the comment block in [`ChipFootprintBuilder.cs`](house/HouseLibGenerator/ChipFootprintBuilder.cs) for the gory details.

To regenerate just the .PcbLib (after a vendor `.xls` change has already propagated):

```bash
make house-pcblib
```

Or invoke the generator directly:

```bash
dotnet run --project house/HouseLibGenerator -- \
    --input build/footprints/house-footprints.json \
    --output build/house.PcbLib
```

> **Known quirk — resave the `.xls` in Microsoft Excel after every regeneration.**
>
> Altium's DbLib OLE DB reader cannot open the `.xls` files that `xlwt` produces directly. The workbook looks fine in Excel and the data is correct, but Altium fails to load it (symptom: the DbLib opens but the tables are empty, or tables load but placed components don't resolve their symbols/footprints even when the field mappings are correct).
>
> **Workaround:** after running the generator script, open the produced `build/<vendor>.xls` in Microsoft Excel and save it (File → Save, keeping the `.xls` Excel 97-2003 format). Excel rewrites the file with whatever internal structure the ACE OLE DB provider expects, and Altium then reads it without complaint. This needs to happen every time the script is re-run.
>
> (The root cause appears to be a long-standing incompatibility between `xlwt`'s BIFF8 output and the ACE OLE DB driver Altium uses — the TL;DR being that `xlwt` writes a technically-valid-but-minimal BIFF8 stream that Excel normalizes on save. LibreOffice Calc's "Save As → Excel 97-2003" has been reported to work as a free substitute for the Excel round-trip, but isn't verified here.)

# Vendor Library Details

- Panasonic resistor family rationale and inclusion matrix: [`vendors/panasonic/README.md`](vendors/panasonic/README.md)
- TDK capacitor notes: [`vendors/tdk/README.md`](vendors/tdk/README.md)
- Samsung capacitor notes: [`vendors/samsung/README.md`](vendors/samsung/README.md)
- Murata capacitor/ferrite notes: [`vendors/murata/README.md`](vendors/murata/README.md)

# Database Standards

See `docs/standards`

# Additional References

## Imperial to Metric Footprint Size Conversion

| Imperial Inch (EIA) | Metric (JEITA) <- used by this library |
|----------|-------------------------------|
| 01005    | 0402                          |
| 0201     | 0603                          |
| 0402     | 1005                          |
| 0603     | 1608                          |
| 0805     | 2012                          |
| 1206     | 3216                          |
