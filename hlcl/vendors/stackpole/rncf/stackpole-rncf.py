#!/usr/bin/env python
"""
Generate ``build/output/stackpole-rncf.xls`` from
``vendors/stackpole/rncf/rncf_parts.csv``.

Stackpole RNCF is the precision thin-film chip resistor family:
tolerances down to 0.01%, TCR as tight as 2 ppm/C, AEC-Q200
compliant. Sizes 0201..2512 in the public catalog; we carry
0201..1206 to match the rest of the library's footprint envelope.

Datasheet: ``vendors/stackpole/reference/SEI-RNCF.pdf``
(see ``../tools/scrape_stackpole.py`` for how the orderable
list was pulled from Stackpole's public parametric search).

Outputs:

* ``build/output/stackpole-rncf.xls`` -- Excel 97-2003 workbook,
  one sheet ``RNCF``. User-facing.
* ``build/output/stackpole-rncf.DbLib`` -- INI-format DbLib bound
  to the .xls above. User-facing.
* ``build/intermediate/footprints/stackpole-rncf-footprints.json``
  -- per-vendor footprints sidecar. Intermediate.

Description string says ``"THIN FILM"`` (vs ``"THICK FILM"`` for
RMCF), matching the Panasonic ERA / Yageo RT precision-thin-film
convention used elsewhere in the catalog.

Usage:

    python vendors/stackpole/rncf/stackpole-rncf.py
"""

import argparse
import csv
import os
import sys
from collections import Counter

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(HERE, "rncf_parts.csv")

BUILD_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "build"))
INTERMEDIATE_DIR = os.path.join(BUILD_DIR, "intermediate")
OUTPUT_DIR = os.path.join(BUILD_DIR, "output")
FOOTPRINTS_DIR = os.path.join(INTERMEDIATE_DIR, "footprints")

_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
_STACKPOLE_DIR = os.path.normpath(os.path.join(HERE, ".."))
if _STACKPOLE_DIR not in sys.path:
    sys.path.insert(0, _STACKPOLE_DIR)

import _common as _vendor_common      # noqa: E402
import _dblib as _vendor_dblib        # noqa: E402
import _stackpole_common as sc        # noqa: E402

VENDOR_KEY = "stackpole-rncf"
FAMILY_ID = VENDOR_KEY

SHEET = "RNCF"
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".xls")
DEFAULT_DBLIB_OUTPUT = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib")
DEFAULT_FOOTPRINTS_OUTPUT = os.path.join(
    FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"
)

DRAWING_NOTE = "Dimensions from Stackpole RNCF series datasheet (SEI-RNCF)"


def _qualifications(aecq200_cell: str) -> str:
    """Resolve the per-row Qual column from the parametric AECQ200
    field. Stackpole emits ``"Compliant"`` / ``"Not Compliant"`` /
    blank; only mark the row AEC-Q200 when the upstream record
    explicitly claims compliance. RNCF is uniformly AEC-Q200 in
    practice, but we mirror the upstream cell value rather than
    hard-coding so a future non-compliant SKU isn't mislabelled."""
    return "AEC-Q200" if (aecq200_cell or "").strip().lower() == "compliant" else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", default=DEFAULT_INPUT,
                    help="Input CSV from ../tools/scrape_stackpole.py.")
    ap.add_argument("--output", default=DEFAULT_OUTPUT,
                    help="Output .xls path.")
    ap.add_argument("--footprints-output", default=DEFAULT_FOOTPRINTS_OUTPUT,
                    help="Output path for the per-vendor footprints "
                         "JSON sidecar.")
    args = ap.parse_args()

    wb = xlwt.Workbook()
    sheet = wb.add_sheet(SHEET)
    for col, h in enumerate(sc.HEADERS):
        sheet.write(0, col, h)

    row_idx = 0
    skipped = Counter()
    eia_counts = Counter()
    used_roots: set[str] = set()

    with open(args.input, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            built = sc.row_for_part(
                r,
                family_id=FAMILY_ID,
                size_to_footprint=sc.SIZE_TO_FOOTPRINT_THIN,
                qualifications=_qualifications(r.get("aecq200", "")),
                description_kind="THIN FILM",
            )
            if built is None:
                eia = r.get("size", "")
                if eia in sc.SIZE_TO_FOOTPRINT_THIN:
                    skipped[f"size {eia}: disabled by config"] += 1
                else:
                    skipped[f"size {eia}: outside library support"] += 1
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
    fp_rows = sc.build_footprint_rows(
        used_roots, FAMILY_ID, DRAWING_NOTE, sc.SIZE_TO_FOOTPRINT_THIN,
    )
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
