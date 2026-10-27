#!/usr/bin/env python
"""Generate build/output/tdk-capacitors.xls (TDK CGA automotive MLCCs) from
tdk_automotive_pn.csv: database-standard capacitor rows (vendors/_standard.py)
decoded from each full ordering code, plus the .DbLib and footprints JSON.
"""

import os
import sys
from decimal import Decimal

from xlwt import Workbook

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# build/ has two subdirs:
#   intermediate/  artifacts the rest of the build chain consumes
#                  (per-vendor footprints JSONs, merged JSON, .step models,
#                  pdflatex aux files); never user-facing.
#   output/        user-facing artifacts (.xls, .DbLib, .PcbLib, .SchLib,
#                  .pdf). Each lives here exactly once -- no duplicates.
BUILD_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", "build"))
INTERMEDIATE_DIR = os.path.join(BUILD_DIR, "intermediate")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
FOOTPRINTS_DIR = os.path.join(INTERMEDIATE_DIR, "footprints")
PN_CSV = os.path.join(SCRIPT_DIR, "tdk_automotive_pn.csv")

# Make the shared `vendors/_common.py` and `vendors/_dblib.py` helpers
# importable regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common as _vendor_common
import _dblib as _vendor_dblib
import _standard

# Written to the drawingNote field of every row in the per-vendor
# footprints JSON so a downstream reviewer can see which datasheet the
# body geometry came from.
DRAWING_NOTE = "Dimensions from TDK CGA automotive series datasheet"
VENDOR_KEY = "tdk-capacitors"
FAMILY_ID = VENDOR_KEY  # catalog id matches on-disk vendor key
# Each CSV row is one full orderable code, so there are no packaging
# alternates or other extra columns to offer.
SUPPORTED_EXTRAS = ()

# Resolve the active BuildConfig once at module load time -- every row
# in the CSV consults `enabled_sizes` to decide whether to emit, and
# `density_codes` to drive .xls / footprints-JSON column generation.
ENABLED_SIZES = _vendor_common.enabled_sizes(FAMILY_ID)


# CGA part-number decode tables (from TDK CGA automotive datasheet)
dimensionseia = {'1': '0201', '2': '0402', '3': '0603', '4': '0805', '5': '1206', '6': '1210', '8': '1812', '9': '2220'}
dimensionsmetric = {'1': '0603', '2': '1005', '3': '1608', '4': '2012', '5': '3216', '6': '3225', '8': '4532', '9': '5750'}
thickness = {'A': '0.30', 'B': '0.50', 'C': '0.60', 'E': '0.80', 'F': '0.85', 'H': '1.15', 'J': '1.25', 'L': '1.60', 'M': '2.00', 'N': '2.30', 'P': '2.50', 'Q': '2.80', 'R': '3.20'}
# Height code per IPC-SM-782: max body height in 1/100 mm, round half up,
# zero-padded to a min of two digits (so 0.30 mm -> '30', not '03'; 0.85
# mm -> '85', not '085'). Heights >= 1.00 mm spill to three digits.
thicknesscode = {'A': '30', 'B': '50', 'C': '60', 'E': '80', 'F': '85', 'H': '115', 'J': '125', 'L': '160', 'M': '200', 'N': '230', 'P': '250', 'Q': '280', 'R': '320'}

# Body length / width per metric size code, plus the Samsung-CL-style
# terminal/band length (Tx) used by the house.PcbLib for ceramic chip
# capacitors. Drives the per-vendor footprints JSON output at the
# bottom of this script.
CAPC_BODY = {
    # metric: (L, W, T)
    "0603": (0.6, 0.3,  0.15),
    "1005": (1.0, 0.5,  0.30),
    "1608": (1.6, 0.8,  0.35),
    "2012": (2.0, 1.25, 0.50),
    "3216": (3.2, 1.6,  0.50),
    "3225": (3.2, 2.5,  0.50),
    "4532": (4.5, 3.2,  0.60),
    "5750": (5.7, 5.0,  0.60),
}
voltage_test_condition = {'1': '1', '2': '2', '3': '3'}
temperature_range = {'C0G': '-55:125', 'X5R': '-55:85', 'X7R': '-55:125', 'X7S': '-55:125', 'X7T': '-55:125'}
temperature_coefficient = {'C0G': '+/-30', 'X5R': '+/-15%', 'X7R': '+/-15%', 'X7S': '+/-22%', 'X7T': '+22%/-33%'}
rated_voltage = {'0E': '2.5V', '0G': '4V', '0J': '6.3V', '1A': '10V', '1C': '16V', '1E': '25V', '1V': '35V', '1H': '50V', '1N': '75V'}
tolerance = {'C': '+/-0.25pF', 'D': '+/-0.5pF', 'J': '5%', 'K': '10%', 'M': '20%'}
packaging_style = {'A': 'A', 'B': 'B', 'K': 'K'}
reserved = {'A': 'A', 'B': 'B', 'C': 'C'}


def decode_cga_part(part_number):
    """Decode a TDK CGA part number into a database-standard record (a
    dict keyed by column name), returned as ``(record, fp_root,
    body_key)``, or ``(None, reason, None)`` if the row's package size
    has been disabled in the active BuildConfig."""
    metric = dimensionsmetric[part_number[3]]
    dim = dimensionseia[part_number[3]]
    if dim not in ENABLED_SIZES:
        return None, f"size {dim} disabled by config", None
    thick_letter = part_number[4]
    package = "CAPC" + metric + "X" + thicknesscode[thick_letter]
    dielectric = part_number[6:9]
    tr = temperature_range[dielectric]
    tcr = temperature_coefficient[dielectric]
    rv = rated_voltage[part_number[9:11]]

    capcode = part_number[11:14]
    if 'R' in capcode:
        cap = Decimal(capcode.replace('R', '.'))
    else:
        cap = Decimal(capcode[0:2]) * 10 ** int(capcode[2])

    tol = tolerance[part_number[14]]

    value = _standard.capacitance(cap)
    fp_cells = _vendor_common.xls_footprint_columns(r"house.PcbLib", package, FAMILY_ID)

    record = {
        **dict(zip(_standard.COMMON, [
            part_number,                                                   # Comment
            _standard.capacitor_description(value, tol, rv, dielectric, dim),
            "TDK", part_number, dim,                                       # MFG / MPN / Package
            r"house.SchLib", "CAP",                                        # Library Path / Ref
            *fp_cells,
            "AEC-Q200",                                                    # Qual (CGA = automotive)
        ])),
        "Value": value, "Tolerance": tol, "Voltage": rv, "Tcr": tcr, "Tr": tr,
    }
    return record, package, (metric, thick_letter)


# --- Per-vendor footprint JSON output ------------------------------------
# Emits build/intermediate/footprints/tdk-capacitors-footprints.json with one entry
# per (CAPC body, density) pair. Consumed by
# house/build_house_footprints.py (merge step), house/build_step_models.py
# (parametric STEP 3D model generator) and house/altium_pcblib/
# (.PcbLib autogenerator).

def _build_footprint_rows(bodies):
    body_specs = []
    for metric, thick_letter in bodies:
        L, W, T = CAPC_BODY[metric]
        H = float(thickness[thick_letter])
        body_specs.append({
            "root": "CAPC" + metric + "X" + thicknesscode[thick_letter],
            "kind": "C",
            "drawingNote": DRAWING_NOTE,
            "bodyMm": {
                "lengthNominal":         L,
                "widthNominal":          W,
                "heightNominal":         H,
                "terminalLengthNominal": T,
            },
        })
    return _vendor_common.expand_footprint_rows(body_specs, FAMILY_ID)


def main():
    records = []
    unique_bodies = set()  # (metric, thick_letter) pairs needing footprints
    config_skipped = 0

    with open(PN_CSV, 'r') as f:
        for line in f:
            part_number = line.strip()
            if not part_number:
                continue
            record, _info, body_key = decode_cga_part(part_number)
            if record is None:
                config_skipped += 1
                continue
            records.append(record)
            unique_bodies.add(body_key)

    if config_skipped:
        print(f"({config_skipped} CGA parts dropped because the active "
              f"BuildConfig disabled their package size.)", file=sys.stderr)

    wb = Workbook()
    _standard.write_sheet(wb.add_sheet('CGA'), 'C', FAMILY_ID, records,
                          supported=SUPPORTED_EXTRAS)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    wb.save(os.path.join(OUTPUT_DIR, "tdk-capacitors.xls"))
    _vendor_dblib.write_dblib(
        path=os.path.join(OUTPUT_DIR, "tdk-capacitors.DbLib"),
        vendor_key="tdk-capacitors",
        tables=["CGA"],
    )

    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    _vendor_common.write_footprints_json(
        os.path.join(FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"),
        vendor=VENDOR_KEY,
        footprints=_build_footprint_rows(unique_bodies),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
