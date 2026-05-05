#!/usr/bin/env python
"""
Generate build/output/murata-grm.xls from vendors/murata/grm/grm_parts.csv.

GRM is Murata's general-purpose / commercial multilayer ceramic
capacitor series. Same physical chip body as GCM but a different part
catalogue: GRM ships ~50,000 SKUs across the same 0201-1210 EIA range,
covers more dielectric codes (CH, SL, B, R, CJ, CK in addition to
the IEC X7R / C0G / U2J / etc.), and is *not* automotive-qualified
(Qual is left blank, vs. GCM's "AEC-Q200").

The CSV schema is identical to GCM's; this script is therefore largely
a clone of vendors/murata/gcm/murata-gcm.py with three policy
differences:

  1. ``Qual`` is emitted as the empty string (commercial grade, no
     automotive qualification).
  2. The ``TCR_BY_DIELECTRIC`` table is extended with the older
     Murata-internal class-1 codes (CH, SL, CJ, CK, UJ) that GRM
     uses in addition to the IEC names. Class-2-style two-letter
     codes (B, R, F) GRM also ships -- but their published TC bands
     vary by part-size, so we leave Tcr blank and let
     ``unknown_dielectrics`` surface the count.
  3. Output paths point at build/output/murata-grm.* and
     build/intermediate/footprints/murata-grm-footprints.json.

All other transformations (mm parsing, reel-suffix MPN expansion,
EIA-size lookup, footprint naming, status filtering) are line-for-line
the same as the GCM script. Where a transformation has policy
implications worth explaining, the comment is duplicated here rather
than referenced into ../gcm/murata-gcm.py to keep this file
readable on its own.

Usage:
    python vendors/murata/grm/murata-grm.py
    python vendors/murata/grm/murata-grm.py --include-nrnd
    python vendors/murata/grm/murata-grm.py --input vendors/murata/grm/grm_parts.csv \\
                                            --output build/output/murata-grm.xls

To refresh the CSV from Murata's PIM API (slow, ~3-5 minutes for the
full GRM catalogue):

    python vendors/murata/fetch_gcm_pim.py \\
        --part-prefix GRM \\
        --output vendors/murata/grm/grm_parts.csv \\
        --acquisition-num 60000
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

import xlwt

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(HERE, "grm_parts.csv")

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
DEFAULT_OUTPUT = os.path.join(OUTPUT_DIR, "murata-grm.xls")

# Make the shared `vendors/_common.py` and `vendors/_dblib.py` helpers
# importable regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common as _vendor_common
import _dblib as _vendor_dblib

VENDOR_KEY = "murata-grm"
DEFAULT_DBLIB_OUTPUT = os.path.join(OUTPUT_DIR, VENDOR_KEY + ".DbLib")
DEFAULT_FOOTPRINTS_OUTPUT = os.path.join(
    FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"
)

# Written to the drawingNote field of every row in the per-vendor
# footprints JSON so a downstream reviewer can see which datasheet
# the body geometry came from.
DRAWING_NOTE = "Dimensions from Murata GRM PIM bulk dataset"

SCHLIB = r"house.SchLib"
PCBLIB = r"house.PcbLib"

# Accepted Murata product statuses, in order of preference. "In Production"
# is the default; NRND (Not Recommended for New Designs) is opt-in via
# --include-nrnd. "End of Production" and similar are never emitted.
STATUS_ALLOW = {"In Production"}
STATUS_NRND = {"NRND"}

# Nominal L x W (mm) -> (EIA size code, metric footprint-dimension code).
# These are the canonical chip sizes our house.PcbLib covers; anything
# outside this list (e.g. GRM015, the 0.25x0.125 mm "008004" subminiature
# body, or GRM03 0.4x0.2 mm "01005") gets dropped since we don't have a
# CAPC footprint for it.
EIA_BY_MM = {
    (0.4, 0.2):  ("01005", "0402"),
    (0.6, 0.3):  ("0201",  "0603"),
    (1.0, 0.5):  ("0402",  "1005"),
    (1.6, 0.8):  ("0603",  "1608"),
    (2.0, 1.25): ("0805",  "2012"),
    (3.2, 1.6):  ("1206",  "3216"),
    (3.2, 2.5):  ("1210",  "3225"),
}

# Terminal/band length per metric size code (Samsung-CL convention used
# library-wide; see top-level README "Library / pad section" notes).
# Drives the per-vendor footprints JSON output below.
TERMINAL_BY_METRIC = {
    "0402": 0.10,
    "0603": 0.15,
    "1005": 0.30,
    "1608": 0.35,
    "2012": 0.50,
    "3216": 0.50,
    "3225": 0.50,
}

# Dielectric -> Tcr string. GRM uses both IEC dielectric names (X7R,
# C0G, etc.) and older Murata-internal codes (CH, SL, CJ, CK, UJ).
# Class 1 (paraelectric, linear TC) entries are in ppm/°C; Class 2
# (ferroelectric, nonlinear TC) entries are the allowable
# capacitance-change bands over the rated temperature range.
# See EIA-RS-198 / IEC 60384-21 for the IEC scheme; the Murata
# part-numbering catalogue covers the legacy codes.
#
# Codes Murata uses where the published TC depends on the part size
# (B, R, F, the various "two-letter" pre-IEC characteristics) are
# left out and emitted blank; the unknown-dielectric summary at the
# end of the run surfaces the count so we can revisit the table.
TCR_BY_DIELECTRIC = {
    # Class 1, IEC names
    "C0G": "+/-30 ppm",
    "X8G": "+/-30 ppm",
    "U2J": "-750 ppm",
    "X8N": "+/-30 ppm",
    # Class 1, older Murata codes
    # CH = NP0 with looser tolerance than C0G (Murata legacy); +/-60 ppm
    # is the figure listed in the GRM master catalog (cat. C02E) for
    # the CH characteristic.
    "CH":  "+/-60 ppm",
    # SL = negative-going TC: 0/-750 ppm (a.k.a. N750-style); the
    # Murata catalogue lists the band as +350/-1000 ppm but the
    # nominal is -750 ppm, which is what the BOM consumer cares about.
    "SL":  "0/-750 ppm",
    # UJ is U2J pre-IEC short-form; same -750 ppm linear TC.
    "UJ":  "-750 ppm",
    # Class 2, IEC names
    "X7R": "+/-15%",
    "X7S": "+/-22%",
    "X7T": "+22/-33%",
    "X7U": "+22/-56%",
    "X8R": "+/-15%",
    "X8L": "+15/-40%",
    "X8M": "+/-50%",
    "X6S": "+/-22%",
    "X6T": "+22/-33%",
    "X5R": "+/-15%",
    "X5S": "+/-22%",
    "X5T": "+22/-33%",
}

# Murata packaging suffixes emitted into (MFG 2, MPN 2) .. (MFG 5, MPN 5).
# Order is fixed and significant: downstream consumers (Part Choices,
# BOM templates) can address a specific reel format by column index.
# Codes are the four canonical {180/330 mm} x {embossed/paper} formats
# from Murata's MLCC packaging spec (codes L/D/E/W/F/J/K, see
# vendors/murata/reference/murata_part_numbering.pdf page 4). The
# most-distributor-stocked code (L) comes first; see the docstring of
# vendors/murata/gcm/murata-gcm.py for the rationale on dropping the
# previously-emitted (and invalid) `V` and (rarely-stocked) `W`.
PACK_SUFFIXES = ("L", "K", "D", "J")

# Columns emitted in the xls, in order. Must match the per-row schema
# documented in README.md ("Database Standards" section). The MFG 2/MPN 2
# .. MFG 5/MPN 5 slots carry Murata-internal packaging alternates of the
# same electrical part, NOT cross-vendor substitutes. The numbered slots
# start at 2 (the unsuffixed MFG/MPN above is slot 1, by convention).
HEADERS = [
    "Comment", "Description", "MFG", "MPN",
    "MFG 2", "MPN 2", "MFG 3", "MPN 3",
    "MFG 4", "MPN 4", "MFG 5", "MPN 5",
    "Package", "Value",
    "Tolerance", "Tcr", "Tr", "Qual", "Voltage",
    "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref",
    "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]


def parse_mm(s: str) -> float:
    """'1.6mm ±0.1mm' -> 1.6 ; '3.2mm +0.35mm/-0.3mm' -> 3.2"""
    m = re.match(r"^([\d.]+)\s*mm", s)
    if not m:
        raise ValueError(f"can't parse mm from {s!r}")
    return float(m.group(1))


def parse_opstemp(s: str) -> str:
    """'-55\uff5e125\u2103' -> '-55:125' ; blanks -> ''.

    Murata's CSV uses the fullwidth tilde U+FF5E as the range
    separator (not the ASCII tilde U+007E). Accepting both so the
    parser doesn't silently swallow a future CSV that happens to use
    the ASCII one.
    """
    if not s:
        return ""
    m = re.match(r"^(-?\d+)\s*[~\uff5e]\s*(-?\d+)", s)
    return f"{m.group(1)}:{m.group(2)}" if m else ""


def parse_voltage(s: str) -> str:
    """'50Vdc' -> '50V', '1,000Vdc' -> '1kV', '1,250Vdc' -> '1.25kV'."""
    if not s:
        return ""
    m = re.match(r"^([\d.,]+)\s*V", s, re.IGNORECASE)
    if not m:
        return s
    v = float(m.group(1).replace(",", ""))
    if v >= 1000:
        kv = v / 1000
        if kv == int(kv):
            return f"{int(kv)}kV"
        return f"{kv:g}kV"
    if v == int(v):
        return f"{int(v)}V"
    return f"{v:g}V"


def parse_capacitance(s: str) -> str:
    """'1,000pF' -> '1nF', '22,000pF' -> '22nF', '1µF' -> '1uF'."""
    if not s:
        return ""
    m = re.match(r"^([\d.,]+)\s*([pnuµμmF]+)", s)
    if not m:
        return s
    num = float(m.group(1).replace(",", ""))
    unit = m.group(2).lower()
    if unit.startswith("p"):
        pf = num
    elif unit.startswith("n"):
        pf = num * 1e3
    elif unit.startswith(("u", "µ", "μ")):
        pf = num * 1e6
    elif unit.startswith("m"):
        pf = num * 1e9
    else:
        return s
    if pf < 1000:
        return _fmt_num(pf) + "pF"
    if pf < 1e6:
        return _fmt_num(pf / 1e3) + "nF"
    if pf < 1e9:
        return _fmt_num(pf / 1e6) + "uF"
    return _fmt_num(pf / 1e9) + "mF"


def _fmt_num(x: float) -> str:
    if x == int(x):
        return str(int(x))
    return f"{x:g}"


def parse_tolerance(s: str) -> str:
    """'±10%' -> '10%', '±0.1pF' -> '+/-0.1pF', '±2.5%' -> '2.5%'.
    Percent tolerances drop the '±' because that's the Panasonic
    convention; absolute-value (pF) tolerances keep the '+/-' since
    dropping it would be ambiguous."""
    if not s:
        return ""
    s = s.replace("±", "+/-")
    if s.endswith("%"):
        s = s.replace("+/-", "")
    return s


def format_height_code(thickness_max_mm: float) -> str:
    """Encode the body max-height portion of an IPC-SM-782 footprint
    name (the trailing "Xzz" segment of CAPCxxyyXzz). Height is given
    in 1/100 mm, rounded half up, zero-padded to a min of two digits.
    Decimal is used to dodge the float pothole where 0.065 * 100
    reads as 6.499999999999999 with banker's-rounding `round()`.
    """
    h = Decimal(str(thickness_max_mm))
    hundredths = int((h * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{hundredths:02d}"


def build_row(r: dict):
    """Return a (None, row, body_key) tuple where row matches HEADERS,
    or (reason, None, None) if this part should be skipped.

    body_key is (metric, height_code, height_mm) so the caller can
    accumulate the unique CAPC footprints needed by the dataset and
    emit them to the per-vendor footprints JSON.
    """
    mpn_full = r["Part Number"].rstrip("#")
    if not mpn_full:
        return ("skipped: empty Part Number", None, None)

    try:
        L = parse_mm(r["Length"])
        W = parse_mm(r["Width"])
        # Prefer Thickness(max.) because that's what the house.PcbLib
        # footprint naming convention is keyed on. Fall back to
        # Thickness if max isn't populated.
        tmax_src = r["Thickness(max.)"] or r["Thickness"]
        T = parse_mm(tmax_src)
    except (ValueError, KeyError) as e:
        return (f"skipped: unparseable dimensions ({e})", None, None)

    size_key = (L, W)
    if size_key not in EIA_BY_MM:
        return (f"skipped: no footprint for {L}x{W} mm body", None, None)
    eia, metric = EIA_BY_MM[size_key]

    height_code = format_height_code(T)
    fp_root = f"CAPC{metric}X{height_code}"
    body_key = (metric, height_code, T)

    cap_str = parse_capacitance(r["Capacitance"])
    tol_str = parse_tolerance(r["Tolerance of capacitance"])
    v_str = parse_voltage(r["Rated Voltage DC"])
    tr_str = parse_opstemp(r["Operating Temperature"])
    dielectric = (r["Temperature characteristics"] or "").strip()
    tcr_str = TCR_BY_DIELECTRIC.get(dielectric, "")

    description = (
        "CAPACITOR CERAMIC "
        + (cap_str.upper() if cap_str else "")
        + (" " + tol_str if tol_str else "")
        + (" " + v_str if v_str else "")
        + (" " + dielectric if dielectric else "")
        + (" " + eia if eia else "")
    ).strip()

    pack_cells = []
    for suffix in PACK_SUFFIXES:
        pack_cells += ["MURATA", mpn_full + suffix]

    return (None, [
        mpn_full,                     # Comment
        description,                  # Description
        "MURATA",                     # MFG
        mpn_full,                     # MPN
        *pack_cells,                  # MFG 2/MPN 2 .. MFG 5/MPN 5
        eia,                          # Package
        cap_str,                      # Value
        tol_str,                      # Tolerance
        tcr_str,                      # Tcr
        tr_str,                       # Tr
        "",                           # Qual (commercial; not AEC-Q200)
        v_str,                        # Voltage
        SCHLIB, "CAP",                # Library Path / Ref
        PCBLIB, fp_root + "N",        # Footprint 1 (Nominal density)
        PCBLIB, fp_root + "L",        # Footprint 2 (Least density)
        PCBLIB, fp_root + "M",        # Footprint 3 (Most density)
    ], body_key)


# --- Per-vendor footprint JSON output ----------------------------------
# De-dup the bodies on (metric, height_code) and emit one row per
# density level L / N / M for each unique footprint root. Consumed by
# house/build_house_footprints.py (merged into house-footprints.json
# with priority resolution per settings.toml).

def _body_dims_for_metric(metric):
    """(L, W) for a metric size code, derived from EIA_BY_MM."""
    for (L, W), (_eia, m) in EIA_BY_MM.items():
        if m == metric:
            return L, W
    raise KeyError(metric)


def write_footprints_json(path, bodies):
    """bodies is an iterable of (metric, height_code, height_mm).
    De-dup on (metric, height_code) and emit one row per density level
    L / N / M for each unique footprint root."""
    seen = set()
    deduped = []
    for metric, height_code, height_mm in bodies:
        key = (metric, height_code)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((metric, height_code, height_mm))

    deduped.sort(key=lambda mhh: (mhh[0], mhh[2]))

    rows = []
    for metric, height_code, height_mm in deduped:
        L, W = _body_dims_for_metric(metric)
        T = TERMINAL_BY_METRIC[metric]
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
                    "heightNominal":         height_mm,
                    "terminalLengthNominal": T,
                },
            })

    _vendor_common.write_footprints_json(
        path, vendor=VENDOR_KEY, footprints=rows,
    )
    return len(deduped)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", default=DEFAULT_INPUT,
                    help="Input CSV from fetch_gcm_pim.py "
                         "(--part-prefix GRM)")
    ap.add_argument("--output", default=DEFAULT_OUTPUT,
                    help="Output .xls path")
    ap.add_argument("--footprints-output", default=DEFAULT_FOOTPRINTS_OUTPUT,
                    help="Output path for the per-vendor footprints "
                         "JSON sidecar listing the unique CAPC "
                         "footprints referenced (consumed by "
                         "house/build_house_footprints.py and "
                         "house/altium_pcblib/).")
    ap.add_argument("--include-nrnd", action="store_true",
                    help="Also emit rows for 'NRND' (Not Recommended "
                         "for New Designs) parts. Default is to keep "
                         "only 'In Production' parts.")
    args = ap.parse_args()

    accepted_status = set(STATUS_ALLOW)
    if args.include_nrnd:
        accepted_status |= STATUS_NRND

    wb = xlwt.Workbook()
    sheet = wb.add_sheet("GRM")
    for col, h in enumerate(HEADERS):
        sheet.write(0, col, h)

    row_idx = 0
    skipped = Counter()
    skipped_status = Counter()
    eia_counts = Counter()
    dielectric_counts = Counter()
    unknown_dielectrics = Counter()
    unique_bodies = []

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            status = r.get("Product Status", "").strip()
            if status not in accepted_status:
                skipped_status[status or "(blank)"] += 1
                continue

            reason, row, body_key = build_row(r)
            if row is None:
                skipped[reason] += 1
                continue

            dielectric = (r["Temperature characteristics"] or "").strip()
            dielectric_counts[dielectric] += 1
            if dielectric and dielectric not in TCR_BY_DIELECTRIC:
                unknown_dielectrics[dielectric] += 1
            eia_counts[row[HEADERS.index("Package")]] += 1

            row_idx += 1
            for col, cell in enumerate(row):
                sheet.write(row_idx, col, cell)
            unique_bodies.append(body_key)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(FOOTPRINTS_DIR, exist_ok=True)
    wb.save(args.output)
    _vendor_dblib.write_dblib(DEFAULT_DBLIB_OUTPUT, vendor_key=VENDOR_KEY, tables=["GRM"])
    fp_count = write_footprints_json(args.footprints_output, unique_bodies)

    # --- Diagnostic report to stderr -----------------------------------
    print(f"Wrote {args.output}: {row_idx} rows.", file=sys.stderr)
    print(f"Wrote {args.footprints_output}: {fp_count} unique CAPC "
          f"footprints x 3 density variants.", file=sys.stderr)
    print(file=sys.stderr)
    print("Filtered out by status:", file=sys.stderr)
    for s, n in skipped_status.most_common():
        print(f"  {n:>5}  {s}", file=sys.stderr)
    if skipped:
        print(file=sys.stderr)
        print("Filtered out for other reasons:", file=sys.stderr)
        for reason, n in skipped.most_common():
            print(f"  {n:>5}  {reason}", file=sys.stderr)
    print(file=sys.stderr)
    print("Emitted by EIA size:", file=sys.stderr)
    for s, n in sorted(eia_counts.items()):
        print(f"  {n:>5}  {s}", file=sys.stderr)
    print(file=sys.stderr)
    print("Emitted by dielectric:", file=sys.stderr)
    for d, n in dielectric_counts.most_common():
        mark = "" if (not d or d in TCR_BY_DIELECTRIC) else "  [no Tcr mapping]"
        print(f"  {n:>5}  {d!r}{mark}", file=sys.stderr)
    if unknown_dielectrics:
        print(file=sys.stderr)
        print("Dielectrics with no Tcr mapping (Tcr emitted blank):",
              file=sys.stderr)
        for d, n in unknown_dielectrics.most_common():
            print(f"  {n:>5}  {d}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
