#!/usr/bin/env python
"""
Generate build/samsung-capacitors.xls from vendors/samsung/filtered_samsung_mlcc.csv.

Input: a one-MPN-per-line CSV (we only consume the second column) listing
the Samsung CL-series MLCCs we carry. Each MPN encodes its electrical and
mechanical parameters in fixed character positions per Samsung's CL-series
naming guide (see vendors/samsung/reference/* and the CL part numbering tables
mirrored at the top of this file).

Outputs (both go to build/):

* samsung-capacitors.xls -- Excel 97-2003 workbook matching the per-row
  schema documented in the top-level README.md ("Database Standards"
  section), so that build/samsung-capacitors.DbLib can link against it.
  One worksheet named 'CL'. Library Path / Footprint Path columns
  reference the shared build/house.SchLib + build/house.PcbLib (every
  vendor in this repo binds to the same `house.*` libraries; see
  house/README.md).
* build/footprints/samsung-capacitors-footprints.json -- per-vendor
  footprint specification consumed by:
    - house/build_house_footprints.py (merged into house-footprints.json
      with priority resolution per settings.toml);
    - house/build_step_models.py (parametric STEP 3D model generator);
    - house/HouseLibGenerator/ (.PcbLib autogenerator).

After regenerating the database .xls, open it once in Microsoft Excel
and re-save (keeping the .xls / Excel 97-2003 format) before Altium
will read it -- see the "Regenerating the Databases" note in the
top-level README.md.

Usage:
    python vendors/samsung/samsung-capacitors.py
"""

import os
import sys
from collections import Counter

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
BUILD_DIR = os.path.join(REPO_ROOT, "build")
FOOTPRINTS_DIR = os.path.join(BUILD_DIR, "footprints")
INPUT_CSV = os.path.join(HERE, "filtered_samsung_mlcc.csv")
OUTPUT_XLS = os.path.join(BUILD_DIR, "samsung-capacitors.xls")

# Make the shared `vendors/_common.py` helper importable regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(HERE, ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common as _vendor_common

VENDOR_KEY = "samsung-capacitors"
FOOTPRINTS_JSON = os.path.join(FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json")

# Written to the drawingNote field of every row in the per-vendor
# footprints JSON so a downstream reviewer can see which datasheet the
# body geometry came from.
DRAWING_NOTE = "Dimensions from Samsung CL series datasheet"

SCHLIB = r".\house.SchLib"
PCBLIB = r".\house.PcbLib"

# --- Samsung CL-series part-number decode tables ---------------------------
# Position layout for the standard CLxxYzzzVVTHWFG... part number used by
# the parts in filtered_samsung_mlcc.csv:
#
#   CL  ss  d  ccc  t  v  h  ...
#       ^^   ^   ^^^   ^  ^  ^
#       |    |   |     |  |  +-- thickness code
#       |    |   |     |  +----- voltage code
#       |    |   |     +-------- tolerance code
#       |    |   +-------------- 3-digit capacitance (NN-exp or N R N)
#       |    +------------------ dielectric / temperature character.
#       +----------------------- chip body size

# Body-size code -> EIA inch / metric (mm-tenths) packaging code.
SIZE_TO_EIA = {
    '02': '01005', '03': '0201', '05': '0402', '10': '0603',
    '21': '0805', '31': '1206', '32': '1210',
}
SIZE_TO_METRIC = {
    '02': '0402', '03': '0603', '05': '1005', '10': '1608',
    '21': '2012', '31': '3216', '32': '3225',
}

# Dielectric character -> EIA-RS-198 / IEC 60384-21 temperature code.
DIELECTRIC_MAP = {
    'C': 'C0G', 'G': 'X8G', 'A': 'X5R', 'X': 'X6S', 'W': 'X6T',
    'B': 'X7R', 'K': 'X7R(S)', 'Y': 'X7S', 'Z': 'X7T', 'F': 'Y5V',
    'M': 'X8M', 'E': 'X8L', 'J': 'JIS-B',
}

TEMPERATURE_RANGE = {
    'C0G': '-55:125', 'X8G': '-55:150', 'X5R': '-55:85',
    'X6S': '-55:105', 'X6T': '-55:105', 'X7R': '-55:125',
    'X7R(S)': '-55:125', 'X7S': '-55:125', 'X7T': '-55:125',
    'Y5V': '-30:85', 'X8M': '-55:150', 'X8L': '-55:150',
    'JIS-B': '-25:85',
}

TEMPERATURE_COEFFICIENT = {
    'C0G': '+/-30', 'X8G': '+/-30', 'X5R': '+/-15%',
    'X6S': '+/-22%', 'X6T': '+22%/-33%', 'X7R': '+/-15%',
    'X7R(S)': '+/-15%', 'X7S': '+/-22%', 'X7T': '+22%/-33%',
    'Y5V': '+22%/-82%', 'X8M': '+50%/-50%', 'X8L': '+15%/-40%',
    'JIS-B': '+/-10%',
}

VOLTAGE_MAP = {
    'S': '2.5V', 'R': '4V', 'Q': '6.3V', 'P': '10V', 'O': '16V',
    'A': '25V', 'L': '35V', 'B': '50V', 'C': '100V', 'D': '200V',
    'E': '250V', 'F': '350V', 'G': '500V', 'H': '630V', 'I': '1kV',
    'J': '2kV', 'K': '3kV',
}

TOLERANCE_MAP = {
    'N': '+/-0.03pF', 'A': '+/-0.05pF', 'B': '+/-0.1pF',
    'C': '+/-0.25pF', 'D': '+/-0.50pF',
    'F': '+/-1pF/1%',
    'G': '2%', 'J': '5%', 'K': '10%', 'M': '20%',
    'Z': '-20/+80%',
}

# Thickness character -> max body height in mm.
THICKNESS_TO_HEIGHT_MM = {
    '2': 0.20, '3': 0.30, '5': 0.50, '8': 0.80, '9': 0.90,
    'A': 0.65, 'C': 0.85, 'E': 1.10, 'F': 1.25, 'G': 1.40,
    'H': 1.60, 'I': 2.00, 'J': 2.50, 'L': 3.20, 'M': 1.15,
    'P': 1.15, 'Q': 1.25, 'S': 1.35, 'U': 1.80, 'V': 2.50,
    'Y': 1.25,
}

# Thickness character -> CAPC footprint height code per IPC-SM-782: max
# body height in 1/100 mm, round half up, zero-padded to a min of two
# digits (so 0.30 mm -> '30', not '03'; 0.65 mm -> '65', not '065'; 0.85
# mm -> '85', not '085'). Heights >= 1.00 mm spill to three digits
# naturally (e.g. 1.25 mm -> '125').
THICKNESS_TO_HEIGHT_CODE = {
    '2': '20', '3': '30', '5': '50', '8': '80', '9': '90',
    'A': '65', 'C': '85', 'E': '110', 'F': '125', 'G': '140',
    'H': '160', 'I': '200', 'J': '250', 'L': '320', 'M': '115',
    'P': '115', 'Q': '125', 'S': '135', 'U': '180', 'V': '250',
    'Y': '125',
}

# Body length / width per metric size code, plus the Samsung-CL-style
# terminal/band length (Tx) used by the house.PcbLib for ceramic chip
# capacitors. Drives the per-vendor footprints JSON output at the
# bottom of this script.
CAPC_BODY = {
    # metric: (L, W, T)
    "0402": (0.4, 0.2,  0.10),
    "0603": (0.6, 0.3,  0.15),
    "1005": (1.0, 0.5,  0.30),
    "1608": (1.6, 0.8,  0.35),
    "2012": (2.0, 1.25, 0.50),
    "3216": (3.2, 1.6,  0.50),
    "3225": (3.2, 2.5,  0.50),
}

HEADERS = [
    "Comment", "Description", "MFG", "MPN", "Package", "Value",
    "Tolerance", "Tcr", "Tr", "Qual", "Voltage",
    "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref",
    "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]


def format_capacitance(pf):
    """Format a capacitance in picofarads as e.g. '4.7nF', '100pF', '1uF'."""
    if pf < 1000:
        return str(pf).rstrip('0').rstrip('.') + 'pF'
    if pf < 1e6:
        return str(pf / 1e3).rstrip('0').rstrip('.') + 'nF'
    return str(pf / 1e6).rstrip('0').rstrip('.') + 'uF'


def decode_capacitance(cap_code):
    """'105' -> 1_000_000 pF (= 1uF); '4R7' -> 4.7 pF; etc."""
    if 'R' in cap_code:
        return float(cap_code.replace('R', '.'))
    return float(cap_code[0:2]) * (10 ** int(cap_code[2]))


def build_row(pn):
    """Decode a Samsung CL part number into a workbook row plus the three
    CAPC footprint names it references and the (metric, thick_code) body
    key. Returns (row, footprints, body_key) on success, or
    (None, reason, None) when a field can't be decoded."""
    size_code = pn[2:4]
    dielectric_code = pn[4]
    cap_code = pn[5:8]
    tol_code = pn[8]
    volt_code = pn[9]
    thick_code = pn[10]

    if size_code not in SIZE_TO_EIA:
        return None, f"unknown size '{size_code}'", None
    if dielectric_code not in DIELECTRIC_MAP:
        return None, f"unknown dielectric '{dielectric_code}'", None
    if volt_code not in VOLTAGE_MAP:
        return None, f"unknown voltage '{volt_code}'", None
    if tol_code not in TOLERANCE_MAP:
        return None, f"unknown tolerance '{tol_code}'", None
    if thick_code not in THICKNESS_TO_HEIGHT_CODE:
        return None, f"unknown thickness '{thick_code}'", None

    eia = SIZE_TO_EIA[size_code]
    metric = SIZE_TO_METRIC[size_code]
    dielectric = DIELECTRIC_MAP[dielectric_code]
    tr = TEMPERATURE_RANGE[dielectric]
    tcr = TEMPERATURE_COEFFICIENT[dielectric]
    rv = VOLTAGE_MAP[volt_code]
    tol = TOLERANCE_MAP[tol_code]
    height = THICKNESS_TO_HEIGHT_CODE[thick_code]

    cap_str = format_capacitance(decode_capacitance(cap_code))
    fp_root = f"CAPC{metric}X{height}"
    footprints = [fp_root + "N", fp_root + "L", fp_root + "M"]

    description = (
        f"CAPACITOR CERAMIC {cap_str.upper()} {tol} {rv} {dielectric} {eia}"
    )

    row = [
        pn,                           # Comment
        description,                  # Description
        "SAMSUNG",                    # MFG
        pn,                           # MPN
        eia,                          # Package
        cap_str,                      # Value
        tol,                          # Tolerance
        tcr,                          # Tcr
        tr,                           # Tr
        "",                           # Qual (Samsung CL series is general-purpose; auto-grade is CL*-Auto, not in this list)
        rv,                           # Voltage
        SCHLIB, "CAP",                # Library Path / Ref
        PCBLIB, footprints[0],        # Footprint 1 (Nominal density)
        PCBLIB, footprints[1],        # Footprint 2 (Least density)
        PCBLIB, footprints[2],        # Footprint 3 (Most density)
    ]
    return row, footprints, (metric, thick_code)


# --- Per-vendor footprint JSON output ------------------------------------
# Emit one entry per density (L/N/M) of every unique CAPC footprint root
# referenced by the database. Multiple Samsung thickness chars can map
# to the same height code (e.g. 'F', 'Q', 'Y' all encode 1.25 mm ->
# '125'), so we de-dupe on the (metric, height_code) tuple to avoid
# duplicate FootprintName rows.

def write_footprints_json(path, bodies):
    seen = set()  # (metric, height_code)
    deduped = []
    for metric, thick_code in bodies:
        if metric not in CAPC_BODY:
            print(
                f"warning: no body dimensions for metric={metric!r}, "
                "skipping its footprint row",
                file=sys.stderr,
            )
            continue
        height_code = THICKNESS_TO_HEIGHT_CODE[thick_code]
        key = (metric, height_code)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((metric, thick_code, height_code))

    rows = []
    for metric, thick_code, height_code in deduped:
        L, W, T = CAPC_BODY[metric]
        H = THICKNESS_TO_HEIGHT_MM[thick_code]
        root = f"CAPC{metric}X{height_code}"
        for density in ("L", "N", "M"):
            rows.append({
                "name":        root + density,
                "kind":        "C",
                "density":     density,
                "drawingNote": DRAWING_NOTE,
                "bodyMm": {
                    "lengthNominal":         L,
                    "widthNominal":          W,
                    "heightNominal":         H,
                    "terminalLengthNominal": T,
                },
            })

    _vendor_common.write_footprints_json(
        path, vendor=VENDOR_KEY, footprints=rows,
    )
    return len(deduped)


def main():
    wb = xlwt.Workbook()
    sheet = wb.add_sheet("CL")
    for col, h in enumerate(HEADERS):
        sheet.write(0, col, h)

    row_idx = 0
    skipped = []
    emitted_footprints = Counter()
    eia_counts = Counter()
    unique_bodies = set()

    with open(INPUT_CSV, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            _, pn = line.split(",", 1)

            row, info, body_key = build_row(pn)
            if row is None:
                skipped.append((pn, info))
                continue

            row_idx += 1
            for col, cell in enumerate(row):
                sheet.write(row_idx, col, cell)

            eia_counts[row[4]] += 1
            unique_bodies.add(body_key)
            for fp in info:
                emitted_footprints[fp] += 1

    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(OUTPUT_XLS)
    fp_count = write_footprints_json(FOOTPRINTS_JSON, unique_bodies)

    # --- Diagnostic report ----------------------------------------------
    print(f"Wrote {OUTPUT_XLS}: {row_idx} rows.", file=sys.stderr)
    print(f"Wrote {FOOTPRINTS_JSON}: {fp_count} unique CAPC "
          f"footprints x 3 density variants.", file=sys.stderr)
    print(file=sys.stderr)
    print("Emitted by EIA size:", file=sys.stderr)
    for s, n in sorted(eia_counts.items()):
        print(f"  {n:>5}  {s}", file=sys.stderr)

    if skipped:
        print(file=sys.stderr)
        print(f"Skipped {len(skipped)} parts (undecodable):", file=sys.stderr)
        for pn, reason in skipped:
            print(f"  {pn}: {reason}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
