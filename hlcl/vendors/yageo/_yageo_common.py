"""
Shared helpers for the Yageo per-family generator scripts.

The Yageo resistor library covers three sibling product families that
all share the same orderable-parts CSV shape (one MPN per row, dumped
by ``vendors/yageo/tools/scrape_yageo.py``) and the same .xls / DbLib /
footprints-JSON output contract:

* :mod:`vendors.yageo.rc.yageo-rc` -- general-purpose thick-film
  ("RC_L"); commercial grade.
* :mod:`vendors.yageo.ac.yageo-ac` -- automotive thick-film, AEC-Q200.
* :mod:`vendors.yageo.rt.yageo-rt` -- precision thin-film.

This module hosts the bits every Yageo family script needs:

* :data:`HEADERS` -- canonical .xls column order (matches the schema
  documented in the top-level README's "Database Standards" section).
* :data:`RESC_BODIES` -- the unique RESC body geometries the three
  families reference, keyed by IPC-7351B footprint root. Each family
  script passes the subset of root keys its parts actually use to
  :func:`build_footprint_rows` to produce the per-density rows for
  its per-vendor footprints JSON sidecar.
* :data:`SIZE_TO_FOOTPRINT` -- Yageo size code (e.g. ``"0100"``,
  ``"0201"``) -> ``(eia, fp_root)`` for both thick-film (RC/AC) and
  thin-film (RT). The two technologies pick the same RESC roots
  here because Yageo's published RC, AC, and RT body heights for
  each chip size match within rounding (the X<height> code is
  identical), so a single mapping covers all three.
* :func:`format_resistance` -- convert an ohm value to the SI-suffixed
  string used in the Value / Description columns.
* :func:`row_for_part` -- a single-row builder that takes one parsed
  CSV row plus the family-specific qualification string and returns
  the .xls row matching :data:`HEADERS`.
* :func:`build_footprint_rows` -- wraps the
  :func:`vendors._common.expand_footprint_rows` density-fanout so each
  family script just hands in its set of footprint roots.

Path-resolution helpers are intentionally NOT in here -- each family
script knows its own depth from the repo root and builds its own
``BUILD_DIR`` / ``FOOTPRINTS_DIR`` / ``_VENDORS_DIR`` constants
directly, mirroring the per-family pattern under
``vendors/panasonic/`` and ``vendors/murata/``.

CSV schema (one row per stocked Yageo MPN, written by
``tools/scrape_yageo.py``):

    mpn,size_code,resistance_ohms,tolerance,tcr,power_w,
    voltage_v,temp_min_c,temp_max_c,length_mm,width_mm,height_mm

Field-by-field mapping back to the Yageo PIM ``parameterValues``
the scraper consumed:

    mpn               <- displayPn (preserves the human-readable
                         hyphenation, e.g. ``RC0402FR-074K7L``)
    size_code         <- the 4-digit prefix of the MPN, parsed off
                         the front since Yageo's "Chip Size /
                         Footprint" parameter encodes it as
                         ``"0402 / 1005"`` and the metric half is
                         redundant with the EIA size we already
                         resolve from ``SIZE_TO_FOOTPRINT``.
    resistance_ohms   <- "Resistance (Resistors)" (numeric, in ohms)
    tolerance         <- "Resistance Tolerance" (e.g. ``"1%"``)
    tcr               <- "Temperature Coefficient (Resistors)"
                         (e.g. ``"-/+200 ppm/C"``); normalised below
                         to the ``+/-200`` form the rest of the
                         library uses.
    power_w           <- "Compare Power" (numeric, in watts)
    voltage_v         <- "Compare Voltage DC" (numeric, in volts)
    temp_min_c        <- "Compare Temperature Minimum" (numeric)
    temp_max_c        <- "Compare Temperature Maximum" (numeric)
    length_mm         <- "Compare Length" (numeric, in metres in
                         the raw PIM; converted to mm by the scraper)
    width_mm          <- parsed from the "W" string field
                         (the PIM only exposes width in the human
                         "0.2mm +/-0.02mm" form; the scraper grabs
                         the leading nominal)
    height_mm         <- "Compare Thickness" (numeric)

Scope of supported sizes: the mapping below intentionally covers
01005 .. 1206. Yageo also publishes 0075 (009005), 1210, 1218, 2010,
and 2512 parts; those drop out at row-build time because
:data:`SIZE_TO_FOOTPRINT` doesn't list them, keeping the library's
size envelope aligned with the rest of the catalog (Panasonic,
Murata, Samsung).
"""

from __future__ import annotations

import os
import re
import sys
from typing import Iterable, Mapping

# Reach up two levels (yageo/.. == vendors/) so `_common` is importable
# whether the family script is run via `python build.py` or directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_VENDORS_DIR = os.path.normpath(os.path.join(_HERE, ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)

import _common  # noqa: E402  -- vendors/_common.py


# --- .xls column schema --------------------------------------------------
# Same shape every Yageo-family workbook uses; matches the per-row schema
# documented in README.md ("Database Standards" section). The three
# Footprint Path / Ref pairs hold IPC-7351B density variants
# (Nominal / Least / Most) for the same physical part. Yageo doesn't
# ship multi-suffix packaging alternates the way Murata/Samsung do
# (the trailing "L" is a *fixed* default code, not a packaging
# selector), so the (MFG 2, MPN 2) .. (MFG 5, MPN 5) columns are
# omitted entirely -- same approach Panasonic ERJ/ERA workbooks
# take. Altium auto-discovers any extra .xls columns as parameters,
# so the per-row schema documented in README.md is "at least
# these columns, in this order"; absent optional columns are fine.
HEADERS = [
    "Comment", "Description", "MFG", "MPN",
    "Package", "Value",
    "Tolerance", "Tcr", "Tr", "Qual", "Voltage", "Power",
    "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref",
    "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]

SCHLIB = r"house.SchLib"
PCBLIB = r"house.PcbLib"


# --- Yageo size code -> EIA / footprint mapping --------------------------
# Yageo prefixes their MPN with a 4-digit size code that maps to the
# usual EIA chip-size + IPC RESC body. The body geometry comes from
# the dimensions tables in PYU-RC_GROUP_51_ROHS_L.pdf,
# PYU-AC_51_ROHS_L.pdf, and PYU-RT_1-TO-0-01_ROHS_L.pdf; nominal
# heights match between the three datasheets (RC and AC ship the
# same chip stack, RT differs only at 0805 by 0.05 mm which we
# round to the same X-code). Sizes 0075 (009005), 1218, 2010, 2512
# are intentionally omitted -- the rest of the library doesn't
# carry footprints for those EIA cases. 1210 is omitted too: the
# CGA / GCM-style 3225 RESC body isn't yet in the catalog.
#
#                yageo:  (eia,    metric, fp_root,         L,    W,    H,    T)
SIZE_TO_FOOTPRINT: Mapping[str, tuple] = {
    "0100": ("01005", "0402",  "RESC0402X13", 0.40, 0.20, 0.13, 0.10),
    "0201": ("0201",  "0603",  "RESC0603X23", 0.60, 0.30, 0.23, 0.15),
    "0402": ("0402",  "1005",  "RESC1005X35", 1.00, 0.50, 0.35, 0.25),
    "0603": ("0603",  "1608",  "RESC1608X45", 1.60, 0.80, 0.45, 0.30),
    # Yageo 0805 nominal H = 0.50 mm (vs Panasonic ERA-6V's 0.55, ERJ-6's
    # 0.60). Mapping to RESC2012X55 keeps the .xls Footprint cells
    # pointing at an existing RESC root the merge step already
    # resolves (Panasonic ERA-6 wins on priority); the height
    # discrepancy is well inside the sum of Yageo's +/-0.10 and
    # Panasonic's +/-0.10 tolerance bands.
    "0805": ("0805",  "2012",  "RESC2012X55", 2.00, 1.20, 0.55, 0.40),
    # Yageo 1206 length = 3.10 mm (Panasonic ERA-8P uses 3.20 mm).
    # Same reasoning as 0805: priority resolution keeps Panasonic's
    # 3.20 mm body as the canonical RESC3216X55 source.
    "1206": ("1206",  "3216",  "RESC3216X55", 3.20, 1.60, 0.55, 0.45),
}


# --- Resistance / TCR formatting -----------------------------------------

def format_resistance(value: float) -> str:
    """Format a resistance in ohms as a SI-suffixed string used by the
    rest of the library (e.g. ``'4.7k'``, ``'100'``, ``'1M'``). Mirrors
    :func:`vendors.panasonic._panasonic_common.format_resistance`."""
    if value < 1000:
        return f"{value:g}"
    if value < 1_000_000:
        k = value / 1000
        return f"{k:g}k"
    m = value / 1_000_000
    return f"{m:g}M"


_TCR_RE = re.compile(
    r"^\s*(?P<sym>-/\+|\+/-|\+/-|\-/\+|\+|-)?\s*(?P<a>\d+)"
    r"(?:\s*/\s*(?P<sym2>[-+])(?P<b>\d+))?"
    r"\s*ppm",
    re.IGNORECASE,
)


def normalize_tcr(raw: str) -> str:
    """Convert Yageo's TCR strings to the library's compact ASCII form.

    Examples (input -> output):
        ``"-/+200 ppm/C"``        -> ``"+/-200 ppm"``
        ``"-200/+600 ppm/C"``     -> ``"-200/+600 ppm"``
        ``"+/-25 ppm/C"``         -> ``"+/-25 ppm"``
        ``""``                    -> ``""``
        anything else / unknown   -> the raw string with the trailing
                                     ``"/C"`` stripped, in case Yageo
                                     adds a band shape we haven't met
                                     yet (better preserved than silently
                                     dropped).
    """
    if not raw:
        return ""
    s = raw.strip().replace("\u00b0", "").replace("/C", "")
    s = s.replace("/c", "")
    m = _TCR_RE.match(raw)
    if not m:
        return s.strip()
    a = m.group("a")
    b = m.group("b")
    sym = (m.group("sym") or "").replace("-/+", "+/-")
    if b is None:
        return f"+/-{a} ppm" if sym in ("+/-", "") else f"{sym}{a} ppm"
    sym2 = m.group("sym2") or "+"
    return f"-{a}/{sym2}{b} ppm"


def format_power_w(p_w: float) -> str:
    """Format a watt rating as the fractional or milliwatt string the
    rest of the library prefers. Yageo publishes 30 mW, 50 mW, 62.5 mW,
    100 mW, ..., 1 W ratings; the conventional fractions
    (``"1/32W"``, ``"1/16W"``, ...) would be ideal but Yageo's PIM
    doesn't expose them, so we emit the decimal form instead."""
    if p_w >= 1:
        return f"{p_w:g}W"
    mw = p_w * 1000
    if abs(mw - round(mw)) < 1e-6:
        return f"{int(round(mw))}mW"
    return f"{mw:g}mW"


def format_voltage_v(v: float) -> str:
    """``50.0`` -> ``'50V'``; ``200.0`` -> ``'200V'``; ``1000.0`` -> ``'1kV'``."""
    if v >= 1000:
        kv = v / 1000
        return f"{int(kv)}kV" if kv == int(kv) else f"{kv:g}kV"
    return f"{int(v)}V" if v == int(v) else f"{v:g}V"


def format_temp_range(tmin: float, tmax: float) -> str:
    """``-55, 125`` -> ``'-55:125'``."""
    return f"{int(tmin)}:{int(tmax)}"


# --- Per-row builder ------------------------------------------------------

def row_for_part(
    csv_row: Mapping[str, str],
    *,
    family_id: str,
    qualifications: str,
    description_kind: str,
) -> tuple | None:
    """Return ``(row, fp_root, eia)`` for a CSV row, or ``None`` if the
    part should be dropped (size not in :data:`SIZE_TO_FOOTPRINT` or
    disabled by the active BuildConfig).

    ``description_kind`` is the human-readable technology phrase
    inserted into the Description column (e.g.
    ``"THICK FILM"`` for RC/AC, ``"THIN FILM"`` for RT) so the row
    text matches the Panasonic ERJ / ERA convention used elsewhere
    in the catalog.
    """
    size_code = csv_row["size_code"]
    if size_code not in SIZE_TO_FOOTPRINT:
        return None

    eia, _metric, fp_root, _L, _W, _H, _T = SIZE_TO_FOOTPRINT[size_code]
    if eia not in _common.enabled_sizes(family_id):
        return None

    mpn = csv_row["mpn"]
    ohms = float(csv_row["resistance_ohms"])
    tol = csv_row["tolerance"].strip()
    tcr = normalize_tcr(csv_row["tcr"])
    power = format_power_w(float(csv_row["power_w"])) if csv_row.get("power_w") else ""
    volts = (
        format_voltage_v(float(csv_row["voltage_v"]))
        if csv_row.get("voltage_v") else ""
    )
    tr = (
        format_temp_range(float(csv_row["temp_min_c"]), float(csv_row["temp_max_c"]))
        if csv_row.get("temp_min_c") and csv_row.get("temp_max_c") else ""
    )

    value = format_resistance(ohms)
    description = (
        f"RESISTOR {description_kind} {value} OHM {tol} {eia}"
    ).strip()

    fp_cells = _common.xls_footprint_columns(PCBLIB, fp_root, family_id)

    row = [
        mpn,                          # Comment
        description,                  # Description
        "YAGEO",                      # MFG
        mpn,                          # MPN
        eia,                          # Package
        value,                        # Value
        tol,                          # Tolerance
        tcr,                          # Tcr
        tr,                           # Tr
        qualifications,               # Qual
        volts,                        # Voltage
        power,                        # Power
        SCHLIB, "RES",                # Library Path / Ref
    ] + fp_cells
    return row, fp_root, eia


# --- Per-vendor footprints JSON helper ------------------------------------

def build_footprint_rows(
    roots: Iterable[str],
    family_id: str,
    drawing_note: str,
) -> list:
    """Expand ``roots`` (an iterable of footprint-root strings) into one
    JSON row per family-resolved density variant, ready for
    :func:`vendors._common.write_footprints_json`. Roots whose EIA case
    isn't in the family's resolved size set are silently skipped (the
    caller has already filtered, but the size gate here keeps the
    helper independently safe).
    """
    enabled = _common.enabled_sizes(family_id)
    bodies = []
    for root in sorted(set(roots)):
        # Find the (eia, L, W, H, T) tuple that owns this root.
        match = next(
            (entry for entry in SIZE_TO_FOOTPRINT.values() if entry[2] == root),
            None,
        )
        if match is None:
            raise KeyError(
                f"unknown Yageo RESC root {root!r}; add it to SIZE_TO_FOOTPRINT first"
            )
        eia, _metric, _root, L, W, H, T = match
        if eia not in enabled:
            continue
        bodies.append(
            {
                "root": root,
                "kind": "R",
                "drawingNote": drawing_note,
                "bodyMm": {
                    "lengthNominal":         L,
                    "widthNominal":          W,
                    "heightNominal":         H,
                    "terminalLengthNominal": T,
                },
            }
        )
    return _common.expand_footprint_rows(bodies, family_id)
