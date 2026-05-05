#!/usr/bin/env python
"""
Generate ``build/output/yageo-rc.xls`` from
``vendors/yageo/rc/rc_parts.csv``.

Yageo's RC ("RC_L") is the volume general-purpose thick-film chip
resistor family -- commercial grade, low cost, sizes 0075..2512 in
the public catalog. We carry 01005 (Yageo's "0100") through 1206;
0075 (009005), 1210, 1218, 2010, 2512 drop out because the rest of
this library doesn't carry footprints for them yet.

Datasheet: ``vendors/yageo/reference/PYU-RC_GROUP_51_ROHS_L.pdf``
(see ``../tools/scrape_yageo.py`` for how the orderable list was
pulled from Yageo's public PIM).

Outputs:

* ``build/output/yageo-rc.xls`` -- Excel 97-2003 workbook, one sheet
  ``RC``, matches the per-row schema documented in README.md
  ("Database Standards" section). User-facing.
* ``build/output/yageo-rc.DbLib`` -- INI-format DbLib bound to the
  .xls above, emitted by :mod:`vendors._dblib`. User-facing.
* ``build/intermediate/footprints/yageo-rc-footprints.json`` --
  per-vendor footprints sidecar consumed by
  ``house/build_house_footprints.py``, the STEP generator, and the
  .PcbLib autogenerator. Intermediate.

Skipped sizes (out of repo support envelope) are accumulated into
the diagnostic summary at the end of the run, so a future bump of
the size set is easy to plan.

Usage:

    python vendors/yageo/rc/yageo-rc.py
"""

import argparse
import csv
import os
import sys
from collections import Counter

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(HERE, "rc_parts.csv")

# build/ has two subdirs:
#   intermediate/  artifacts the rest of the build chain consumes
#                  (per-vendor footprints JSONs, merged JSON, .step models,
#                  pdflatex aux files); never user-facing.
#   output/        user-facing artifacts (.xls, .DbLib, .PcbLib, .SchLib,
#                  .pdf). Each lives here exactly once -- no duplicates.
BUILD_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "build"))
INTERMEDIATE_DIR = os.path.join(BUILD_DIR, "intermediate")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
FOOTPRINTS_DIR = os.path.join(INTERMEDIATE_DIR, "footprints")

# Make the shared `vendors/_common.py` / `vendors/_dblib.py` and the
# sibling `vendors/yageo/_yageo_common.py` helpers importable
# regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
_YAGEO_DIR = os.path.normpath(os.path.join(HERE, ".."))
if _YAGEO_DIR not in sys.path:
    sys.path.insert(0, _YAGEO_DIR)

import _common as _vendor_common  # noqa: E402
import _dblib as _vendor_dblib    # noqa: E402
import _yageo_common as yc        # noqa: E402

VENDOR_KEY = "yageo-rc"
FAMILY_ID = VENDOR_KEY  # catalog id matches on-disk vendor key

SHEET = "RC"
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".xls")
DEFAULT_DBLIB_OUTPUT = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib")
DEFAULT_FOOTPRINTS_OUTPUT = os.path.join(
    FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"
)

# Written to the drawingNote field of every row in the per-vendor
# footprints JSON so a downstream reviewer can see which datasheet
# the body geometry came from.
DRAWING_NOTE = "Dimensions from Yageo RC_L series datasheet (PYU-RC_GROUP_51_ROHS_L)"

# RC is general-purpose / commercial; no AEC-Q200 claim in the
# datasheet (see AC for the automotive sibling). The Qual column
# stays blank so Altium's Part Choices tool doesn't surface a
# misleading qualification badge.
QUAL = ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", default=DEFAULT_INPUT,
                    help="Input CSV from ../tools/scrape_yageo.py.")
    ap.add_argument("--output", default=DEFAULT_OUTPUT,
                    help="Output .xls path.")
    ap.add_argument("--footprints-output", default=DEFAULT_FOOTPRINTS_OUTPUT,
                    help="Output path for the per-vendor footprints "
                         "JSON sidecar.")
    args = ap.parse_args()

    wb = xlwt.Workbook()
    sheet = wb.add_sheet(SHEET)
    for col, h in enumerate(yc.HEADERS):
        sheet.write(0, col, h)

    row_idx = 0
    skipped = Counter()
    eia_counts = Counter()
    used_roots: set[str] = set()

    with open(args.input, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            built = yc.row_for_part(
                r,
                family_id=FAMILY_ID,
                qualifications=QUAL,
                description_kind="THICK FILM",
            )
            if built is None:
                size_code = r.get("size_code", "")
                if size_code in yc.SIZE_TO_FOOTPRINT:
                    skipped[f"size {size_code}: disabled by config"] += 1
                else:
                    skipped[f"size {size_code}: outside library support"] += 1
                continue

            row, fp_root, eia = built
            row_idx += 1
            for col, cell in enumerate(row):
                sheet.write(row_idx, col, cell)
            eia_counts[eia] += 1
            used_roots.add(fp_root)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(args.output)
    _vendor_dblib.write_dblib(
        path=DEFAULT_DBLIB_OUTPUT, vendor_key=VENDOR_KEY, tables=[SHEET],
    )
    fp_rows = yc.build_footprint_rows(used_roots, FAMILY_ID, DRAWING_NOTE)
    _vendor_common.write_footprints_json(
        args.footprints_output, vendor=VENDOR_KEY, footprints=fp_rows,
    )

    densities = _vendor_common.density_codes(FAMILY_ID)
    print(f"Wrote {args.output}: {row_idx} rows.", file=sys.stderr)
    print(f"Wrote {args.footprints_output}: {len(used_roots)} unique RESC "
          f"footprints x {len(densities)} density variants "
          f"({'/'.join(densities) or '<none>'}).",
          file=sys.stderr)
    print(file=sys.stderr)
    print("Emitted by EIA size:", file=sys.stderr)
    for s, n in sorted(eia_counts.items()):
        print(f"  {n:>5}  {s}", file=sys.stderr)
    if skipped:
        print(file=sys.stderr)
        print("Skipped:", file=sys.stderr)
        for reason, n in skipped.most_common():
            print(f"  {n:>5}  {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
