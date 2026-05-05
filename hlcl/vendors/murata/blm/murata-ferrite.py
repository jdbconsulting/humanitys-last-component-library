#!/usr/bin/env python
"""
Generate build/output/murata-ferrite.xls from vendors/murata/blm/blm_parts.csv,
using per-base-MPN body dimensions cached in
vendors/murata/blm/blm_dimensions.csv.

Inputs (both checked into git):

* vendors/murata/blm/blm_parts.csv -- 1 row per orderable Murata
  BLM-series ferrite bead we carry. Columns:

      MPN, Package, DCR, Current, Impedance

  The MPN's first 5 characters select the worksheet name:

      BLM15* -> sheet 'BLM15'  (0402 imperial / 1005 metric body)
      BLM18* -> sheet 'BLM18'  (0603 imperial / 1608 metric body)
      BLM31* -> sheet 'BLM31'  (1206 imperial / 3216 metric body)

* vendors/murata/blm/blm_dimensions.csv -- per-base-MPN body dimensions
  scraped from Murata's productdetail pages by
  vendors/murata/blm/fetch_blm_datasheets.py. Columns:

      base_mpn, sample_mpn, length_mm, width_mm, thickness_mm, source_url

  ``base_mpn`` = ``MPN[:10]`` = ``BLM<size:2><subseries:2><value:3>``;
  trailing tolerance / temp-grade / packaging digits don't affect body
  dimensions, so this 10-char key is the unit of dimensional truth.
  Refresh the CSV by running:

      python vendors/murata/blm/fetch_blm_datasheets.py

  See vendors/murata/blm/reference/ for the corresponding
  human-readable per-subseries spec extracts.

Outputs:

* build/output/murata-ferrite.xls -- Excel 97-2003 workbook matching
  the per-row schema documented in the top-level README.md ('Database
  Standards' section), so build/output/murata-ferrite.DbLib can link
  against it. Three worksheets (BLM15 / BLM18 / BLM31), 18 columns
  each. Library Path / Footprint Path columns reference the shared
  build/output/house.SchLib + build/output/house.PcbLib. User-facing.

* build/intermediate/footprints/murata-ferrite-footprints.json -- per-vendor
  footprint specification consumed by:
    - house/build_house_footprints.py (merged into house-footprints.json
      with priority resolution per settings.house_footprints.priority
      in the active BuildConfig);
    - house/build_step_models.py (parametric STEP 3D model generator);
    - house/altium_pcblib/ (.PcbLib autogenerator).

  Footprint roots emitted are determined per-MPN from the dimensions
  CSV, not assumed per-family. Every distinct (size, height_code)
  pair in the dimensions CSV produces one INDC<metric>X<height>
  root x three IPC-7351B density variants (L/N/M), tagged
  ``kind="FB"`` so the STEP generator gives the body the
  ferrite-blue colour palette (per the chip-family colour table in
  the top-level README.md).

Usage:
    python vendors/murata/blm/murata-ferrite.py
"""

import csv
import os
import sys
from collections import Counter

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
# build/ has two subdirs:
#   intermediate/  artifacts the rest of the build chain consumes
#                  (per-vendor footprints JSONs, merged JSON, .step models,
#                  pdflatex aux files); never user-facing.
#   output/        user-facing artifacts (.xls, .DbLib, .PcbLib, .SchLib,
#                  .pdf). Each lives here exactly once -- no duplicates.
BUILD_DIR = os.path.join(REPO_ROOT, "build")
INTERMEDIATE_DIR = os.path.join(BUILD_DIR, "intermediate")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
FOOTPRINTS_DIR = os.path.join(INTERMEDIATE_DIR, "footprints")
INPUT_CSV = os.path.join(HERE, "blm_parts.csv")
DIMENSIONS_CSV = os.path.join(HERE, "blm_dimensions.csv")
OUTPUT_XLS = os.path.join(OUTPUT_DIR, "murata-ferrite.xls")

_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common as _vendor_common
import _dblib as _vendor_dblib

# Catalog / build-target id (plural) -- used for config lookup. The on-disk
# vendor key (singular) is still what shows up in `*-footprints.json`,
# `.xls`, and `.DbLib` basenames; `_config.vendor_key_for` maps between
# the two. See `hlcl/_config.py` docstring for the rationale.
FAMILY_ID = "murata-ferrites"
VENDOR_KEY = "murata-ferrite"
FOOTPRINTS_JSON = os.path.join(FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json")
OUTPUT_DBLIB = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib")

DRAWING_NOTE = "Dimensions from Murata productdetail pages, captured by vendors/murata/blm/fetch_blm_datasheets.py"

SCHLIB = r"house.SchLib"
PCBLIB = r"house.PcbLib"

# --- Per-family geometry ---------------------------------------------------
# These describe the package-family Length and Width (which are uniform
# across every subseries we currently carry) plus the IPC-7351B
# terminal/band length used by the .PcbLib pad-math, and a fallback
# nominal height for the rare case where blm_dimensions.csv is missing
# a base MPN. The per-MPN heights from the dimensions CSV take
# precedence -- the fallback is only used when the CSV hasn't been
# refreshed for a newly-added MPN, and the script logs a warning so
# the gap gets filled.
FAMILY = {
    "BLM15": {
        "imperial":            "0402",
        "metric":              "1005",
        "length_mm":           1.0,
        "width_mm":            0.5,
        "terminal_mm":         0.30,
        "fallback_height_mm":  0.5,
    },
    "BLM18": {
        "imperial":            "0603",
        "metric":              "1608",
        "length_mm":           1.6,
        "width_mm":            0.8,
        "terminal_mm":         0.35,
        "fallback_height_mm":  0.8,
    },
    "BLM31": {
        "imperial":            "1206",
        "metric":              "3216",
        "length_mm":           3.2,
        "width_mm":            1.6,
        "terminal_mm":         0.50,
        "fallback_height_mm":  1.6,
    },
}

# Sheet ordering in the output workbook (also dictates the .DbLib's
# Table1/Table2/Table3 mapping order).
SHEET_ORDER = ["BLM15", "BLM18", "BLM31"]

# Column headers on every sheet. The build/output/murata-ferrite.DbLib written
# by vendors/_dblib.py mirrors the standard Comment / Description /
# Library Path / Library Ref / Footprint Path / Footprint Ref (x3
# density variants) FieldMap set, so every column listed here that
# matches one of those names gets explicit Altium handling; the rest
# are auto-discovered by Altium as parameters when the DbLib is loaded.
HEADERS = [
    "Comment", "Description", "MFG", "MPN", "Package",
    "DCR", "Tr", "Qual", "Current", "Impedance",
    "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref",
    "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]


def family_key(mpn):
    """Return the family key (BLM15 / BLM18 / BLM31) for an MPN, or
    None if the MPN doesn't start with a known prefix."""
    prefix = mpn[:5]
    return prefix if prefix in FAMILY else None


def base_mpn_of(mpn):
    """Return the 10-char base MPN (subseries+impedance) that uniquely
    determines body dimensions. Suffix bytes (tolerance, temperature
    grade, packaging) don't change physical dimensions for almost every
    BLM-series part -- the rare exceptions are listed in
    INTRA_BASE_HEIGHT_OVERRIDES below."""
    return mpn[:10]


# Intra-base dimension overrides for the rare cases where Murata builds
# physically different bodies under the same 10-char base MPN, switching
# only on the trailing tolerance / temperature / packaging digits.
#
# Keys are the 11-char prefix ``(base + tolerance_char)``. When an MPN
# matches one of these prefixes, the height in the value dict overrides
# whatever blm_dimensions.csv has for the base. Length and Width never
# need overriding -- they're set by the package family and Murata
# never differs on those across a base.
#
# Currently populated overrides:
#
# * BLM18EG221: Murata's PIM dump exposes two ``Thickness(max.)``
#   builds for this base -- ``S``-tolerance variants are 0.8 mm tall,
#   ``T``-tolerance variants are 0.5 mm tall (max 0.65 -> nominal 0.5
#   after subtracting the +/-0.15 mm width-and-thickness band). The
#   blm_dimensions.csv row was sampled from the alphabetically-first
#   ``S`` variant (`BLM18EG221SN1`), so we need to override the three
#   `T*1` variants down to 0.5 mm. See
#   ``vendors/murata/blm/reference/BLM18EG.md`` for the full anomaly note.
#
# Add new entries here as future scrapes uncover more of these.
INTRA_BASE_HEIGHT_OVERRIDES = {
    "BLM18EG221T": 0.5,  # 'T'-tolerance build is 0.5 mm tall, not 0.8
}


def format_height_code(h_mm):
    """Encode a nominal height in mm as the IPC-7351B-style code used
    in this repo's footprint names: integer hundredths-of-mm with no
    decimal point and no leading zeros before what was the decimal
    point.

        0.05 mm -> '05'      0.50 mm -> '50'      1.00 mm -> '100'
        0.65 mm -> '65'      0.85 mm -> '85'      1.60 mm -> '160'
        2.00 mm -> '200'     2.50 mm -> '250'

    See the 'Footprints are named using the IPC-7351B land-pattern
    naming convention' section of the top-level README.md for the full
    spec."""
    val = round(h_mm * 100)
    if val < 0:
        raise ValueError(f"height must be non-negative (got {h_mm!r})")
    if val >= 100:
        return str(val)
    return f"{val:02d}"


def load_dimensions(path):
    """Read vendors/murata/blm/blm_dimensions.csv into a dict keyed on the
    10-char base MPN. Returns {} if the file is missing -- in that
    case the script will fall through to family-default heights and
    print a warning per fallback (so a forgotten fetch run is loud
    but not fatal)."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"base_mpn", "length_mm", "width_mm", "thickness_mm"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"{path}: missing required columns: {sorted(missing)}"
            )
        for row in reader:
            base = row["base_mpn"].strip()
            if not base:
                continue
            out[base] = (
                float(row["length_mm"]),
                float(row["width_mm"]),
                float(row["thickness_mm"]),
            )
    return out


def build_description(impedance_str, current_str, imperial_pkg):
    """'120-Ohm @ 100MHz', '2A', '0402' -> 'FERRITE BEAD 120-OHM 2A 0402'.

    Drops the '@ 100MHz' tail from the Impedance string and uppercases
    the resistance value (matches the hand-maintained workbook this
    script replaces, so existing BOMs grep cleanly)."""
    z = impedance_str.split("@", 1)[0].strip().upper()
    return f"FERRITE BEAD {z} {current_str} {imperial_pkg}"


def build_row(mpn, package, dcr, current, impedance, dimensions):
    """Decode one CSV row into (sheet_name, workbook_row_values, fp_root,
    height_code, used_fallback).

    On success returns ``(sheet_name, row, fp_root, height_code, used_fallback)``.
    On failure returns ``(None, reason, None, None, None)`` so the caller can
    collect undecodable parts in the diagnostic report.

    ``fp_root`` is the IPC root (e.g. ``INDC1005X50``) without the
    density suffix; the caller derives the per-density footprint
    names by suffixing the resolved density codes from
    :func:`vendors._common.density_codes` to it.

    ``dimensions`` is the result of ``load_dimensions``. If ``mpn``'s
    base isn't in there, falls back to the FAMILY default body-LxW
    plus the family's most common height (a fallback that should
    never fire if blm_dimensions.csv is up-to-date).

    Returns ``(None, "disabled by config", ...)`` when the row's
    package size has been turned off in the active BuildConfig
    (caller treats this as an expected skip, not an error)."""
    sheet = family_key(mpn)
    if sheet is None:
        return None, "MPN does not start with a known BLM family prefix", None, None, None

    fam = FAMILY[sheet]
    if package != fam["imperial"]:
        return None, (
            f"Package={package!r} disagrees with family {sheet} "
            f"(expected {fam['imperial']!r})"
        ), None, None, None

    if package not in _vendor_common.enabled_sizes(FAMILY_ID):
        return None, "disabled by config", None, None, None

    base = base_mpn_of(mpn)
    if base in dimensions:
        L, W, H = dimensions[base]
        used_fallback = False
    else:
        # Fallback when blm_dimensions.csv doesn't cover this base.
        # Stay buildable, but mark used_fallback so the diagnostic
        # report nags the caller to refresh the CSV.
        L = fam["length_mm"]
        W = fam["width_mm"]
        H = fam["fallback_height_mm"]
        used_fallback = True

    # Intra-base override: a few Murata BLM bases ship with two
    # physically different bodies switching only on the tolerance
    # character (MPN[10]). Apply that override now, after the CSV
    # lookup but before the IPC code is computed, so the right
    # INDC<metric>X<height> name is emitted.
    intra_key = mpn[:11]
    if intra_key in INTRA_BASE_HEIGHT_OVERRIDES:
        H = INTRA_BASE_HEIGHT_OVERRIDES[intra_key]

    height_code = format_height_code(H)
    fp_root = f"INDC{fam['metric']}X{height_code}"
    fp_cells = _vendor_common.xls_footprint_columns(PCBLIB, fp_root, FAMILY_ID)

    description = build_description(impedance, current, package)

    row = [
        mpn,                          # Comment
        description,                  # Description
        "MURATA",                     # MFG
        mpn,                          # MPN
        package,                      # Package
        dcr,                          # DCR
        "-55:125",                    # Tr -- BLM family is uniformly -55..+125 C
        "",                           # Qual (BLM is commercial; no auto/MIL grade)
        current,                      # Current
        impedance,                    # Impedance
        SCHLIB, "FERRITE",            # Library Path / Ref
    ] + fp_cells
    return sheet, row, fp_root, height_code, used_fallback


def write_footprints(path, family_height_pairs, dimensions):
    """Emit one INDC entry per resolved density code for every (family,
    height_code) pair observed when iterating the parts CSV. Within a
    family, multiple heights produce multiple INDC roots, all sharing
    the family's L/W/T but differing in H.

    Densities to emit are resolved from the active BuildConfig
    (per-family override-aware) via :func:`vendors._common.density_codes`,
    so a user who disabled e.g. the M variant gets exactly the L+N
    rows here without any per-script branching.

    ``dimensions`` is consulted to recover the underlying H_mm so the
    footprints JSON carries the float, not just the integer code. If a
    given (family, height_code) pair isn't in the dimensions dict
    (because the script fell back to FAMILY['fallback_height_mm']),
    the float is recovered from the height_code itself."""
    height_mm_for = {}
    for base, (L, W, H) in dimensions.items():
        if not base.startswith(("BLM15", "BLM18", "BLM31")):
            continue
        sheet = base[:5]
        height_mm_for[(sheet, format_height_code(H))] = H

    bodies = []
    for sheet, height_code in sorted(family_height_pairs):
        fam = FAMILY[sheet]
        L = fam["length_mm"]
        W = fam["width_mm"]
        T = fam["terminal_mm"]
        H = height_mm_for.get(
            (sheet, height_code),
            int(height_code) / 100.0,  # recovered from the IPC code itself
        )
        bodies.append({
            "root": f"INDC{fam['metric']}X{height_code}",
            "kind": "FB",
            "drawingNote": DRAWING_NOTE,
            "bodyMm": {
                "lengthNominal":         L,
                "widthNominal":          W,
                "heightNominal":         H,
                "terminalLengthNominal": T,
            },
        })

    rows = _vendor_common.expand_footprint_rows(bodies, FAMILY_ID)
    _vendor_common.write_footprints_json(
        path, vendor=VENDOR_KEY, footprints=rows,
    )
    return len(bodies)  # number of unique footprint roots


def main():
    dimensions = load_dimensions(DIMENSIONS_CSV)
    if not dimensions:
        print(
            f"warning: {DIMENSIONS_CSV} not found or empty. Falling back to "
            "FAMILY default heights (BLM15=0.5mm, BLM18=0.8mm, BLM31=1.6mm). "
            "Re-scrape with the procedure documented in "
            "vendors/murata/blm/fetch_blm_datasheets.py to get authoritative "
            "per-base-MPN heights.",
            file=sys.stderr,
        )

    wb = xlwt.Workbook()
    sheets = {name: wb.add_sheet(name) for name in SHEET_ORDER}
    for name in SHEET_ORDER:
        for col, h in enumerate(HEADERS):
            sheets[name].write(0, col, h)

    rows_by_sheet = {name: [] for name in SHEET_ORDER}
    skipped = []
    config_skipped = []  # rows dropped because family/size disabled in BuildConfig
    fallback_bases = set()  # {base_mpn} that fell through to family default H
    family_height_pairs = set()  # {(sheet_name, height_code)}
    pkg_counts = Counter()
    fp_root_counts = Counter()
    height_code_counts = Counter()

    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        expected = {"MPN", "Package", "DCR", "Current", "Impedance"}
        missing = expected - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"{INPUT_CSV} is missing required columns: {sorted(missing)}"
            )
        for csv_row in reader:
            mpn = csv_row["MPN"].strip()
            if not mpn:
                continue

            sheet_name, row, fp_root, height_code, used_fallback = build_row(
                mpn,
                csv_row["Package"].strip(),
                csv_row["DCR"].strip(),
                csv_row["Current"].strip(),
                csv_row["Impedance"].strip(),
                dimensions,
            )
            if sheet_name is None:
                if row == "disabled by config":
                    config_skipped.append(mpn)
                else:
                    skipped.append((mpn, row))
                continue

            rows_by_sheet[sheet_name].append(row)
            pkg_counts[csv_row["Package"].strip()] += 1
            fp_root_counts[fp_root] += 1
            family_height_pairs.add((sheet_name, height_code))
            height_code_counts[(sheet_name, height_code)] += 1
            if used_fallback:
                fallback_bases.add(base_mpn_of(mpn))

    # Sort each sheet's rows by Comment/MPN for determinism, then write.
    total = 0
    for sheet_name in SHEET_ORDER:
        for r_idx, row in enumerate(sorted(rows_by_sheet[sheet_name], key=lambda r: r[0]), start=1):
            for col, cell in enumerate(row):
                sheets[sheet_name].write(r_idx, col, cell)
            total += 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(OUTPUT_XLS)
    _vendor_dblib.write_dblib(OUTPUT_DBLIB, vendor_key=VENDOR_KEY, tables=SHEET_ORDER)
    fp_root_count = write_footprints(FOOTPRINTS_JSON, family_height_pairs, dimensions)

    # --- Diagnostic report ---------------------------------------------
    print(f"Wrote {OUTPUT_XLS}: {total} rows across {len(SHEET_ORDER)} sheet(s).", file=sys.stderr)
    for sheet_name in SHEET_ORDER:
        print(f"  {sheet_name}: {len(rows_by_sheet[sheet_name]):>4} rows", file=sys.stderr)
    densities = _vendor_common.density_codes(FAMILY_ID)
    print(
        f"Wrote {FOOTPRINTS_JSON}: {fp_root_count} unique INDC "
        f"footprints x {len(densities)} density variants ({'/'.join(densities) or '<none>'}).",
        file=sys.stderr,
    )
    if config_skipped:
        print(
            f"  ({len(config_skipped)} parts dropped because the active "
            f"BuildConfig disabled their package size.)",
            file=sys.stderr,
        )
    print(file=sys.stderr)
    print("Emitted by package:", file=sys.stderr)
    for pkg, n in sorted(pkg_counts.items()):
        print(f"  {n:>5}  {pkg}", file=sys.stderr)
    print(file=sys.stderr)
    print("Emitted by INDC root (family x IPC height code):", file=sys.stderr)
    for (sheet, hcode), n in sorted(height_code_counts.items()):
        fam = FAMILY[sheet]
        print(f"  {n:>5}  INDC{fam['metric']}X{hcode}  ({fam['length_mm']} x {fam['width_mm']} x {float(hcode)/100} mm)", file=sys.stderr)

    if fallback_bases:
        print(file=sys.stderr)
        print(
            f"WARNING: {len(fallback_bases)} unique base MPNs fell back to "
            f"family-default height (no entry in {DIMENSIONS_CSV}):",
            file=sys.stderr,
        )
        for base in sorted(fallback_bases)[:20]:
            print(f"  {base}", file=sys.stderr)
        if len(fallback_bases) > 20:
            print(f"  ...and {len(fallback_bases) - 20} more", file=sys.stderr)
        print(
            "  Refresh blm_dimensions.csv for authoritative IPC heights.",
            file=sys.stderr,
        )

    if skipped:
        print(file=sys.stderr)
        print(f"Skipped {len(skipped)} parts (undecodable):", file=sys.stderr)
        for mpn, reason in skipped[:20]:
            print(f"  {mpn}: {reason}", file=sys.stderr)
        if len(skipped) > 20:
            print(f"  ...and {len(skipped) - 20} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
