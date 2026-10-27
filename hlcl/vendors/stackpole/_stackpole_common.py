"""
Shared helpers for the Stackpole per-family generator scripts.

Stackpole Electronics ships two sibling chip-resistor product
families that we carry, both consumed from the same orderable-parts
CSV shape (one MPN per row, dumped by
``vendors/stackpole/tools/scrape_stackpole.py``):

* :mod:`vendors.stackpole.rmcf.stackpole-rmcf` -- general-purpose
  thick film ("RMCF"); standard power, AEC-Q200 from 0201 up.
* :mod:`vendors.stackpole.rncf.stackpole-rncf` -- precision thin film
  ("RNCF"); tolerances down to 0.01%, TCR down to 2 ppm/C, AEC-Q200.

This module hosts the bits both Stackpole family scripts need:

* :data:`SUPPORTED_EXTRAS` -- the optional (non-standard) column groups
  the Stackpole rows can supply; the column order and field rules live
  in :mod:`vendors._standard`. Stackpole doesn't expose multi-suffix
  packaging alternates the way Murata and Samsung do (the trailing
  letter on RMCF/RNCF MPNs is a fixed reel-size code that's already
  part of the orderable MPN), so there are no alternates columns --
  same convention Panasonic ERJ/ERA and Yageo RC/AC/RT take.
* :data:`SIZE_TO_FOOTPRINT_THICK` / :data:`SIZE_TO_FOOTPRINT_THIN` --
  RMCF and RNCF respectively. Both are keyed by the 4-digit EIA size
  prefix Stackpole uses inside its MPNs (``"01005"``, ``"0201"``,
  ``"0402"``, ...) and resolve to the IPC-7351B RESC root + nominal
  body geometry from the corresponding datasheet. The two technologies
  share most roots; thin film differs only at 0805 (RNCF body height
  0.55 mm matches the existing thick-film root anyway, so they end up
  on the same RESC root and let the house-priority merge resolve the
  body geometry).
* :data:`format_resistance` -- ohms -> database-standard Value text
  (``100``, ``4.7k``, ``1M``).
* :func:`format_tolerance` -- normalize the tolerance text Stackpole
  emits in the parametric search response (e.g. ``"1%"``, ``"0.05%"``);
  jumper rows (``"< 0.05 ohm"``) have no percentage tolerance and
  become blank.
* :func:`normalize_tcr` -- ``"+/- 100 ppm"`` -> ``"+/-100"``;
  passes through symmetric / asymmetric forms in the database
  standard's compact, unit-less spelling.
* :func:`row_for_part` -- single-row builder that takes one parsed
  CSV row plus the family-specific qualification + construction
  strings and returns ``(record, fp_root, eia)``, where ``record`` is
  the database-standard dict for :func:`vendors._standard.write_sheet`.
* :func:`build_footprint_rows` -- wraps the
  :func:`vendors._common.expand_footprint_rows` density-fanout so each
  family script just hands in its set of footprint roots.

The MFG string is the database standard's upper-case spelling of
"Stackpole Electronics" (MFG cells are upper case across the library).

CSV schema (one row per stocked Stackpole MPN, written by
``tools/scrape_stackpole.py``):

    mpn,size,resistance_ohms,tolerance,tcr,power_w,
    voltage_v,overload_voltage_v,temp_min_c,temp_max_c,aecq200

Field-by-field mapping back to the parametric-search PIM oid columns
the scraper consumed:

    mpn                <- @PartDesc (e.g. "RMCF0805FG10R0", "RNCF0603BTF49R9")
    size               <- @oid11 ("EIA Size") -- already in EIA form,
                          one of "01005".."2512". Used directly as
                          the lookup key against
                          :data:`SIZE_TO_FOOTPRINT_THICK` /
                          :data:`SIZE_TO_FOOTPRINT_THIN`.
    resistance_ohms    <- @oid47 ("Ohmic Value", e.g. "10 ohm",
                          "4.99 Kohm", "1 Mohm", "0 ohm");
                          parsed numerically.
    tolerance          <- @oid10 ("Tolerance", e.g. "1%", "5%",
                          "0.1%", "< 0.05 ohm" for jumpers).
    tcr                <- @oid3 ("TCR", e.g. "+/- 100 ppm",
                          "+/- 50 ppm", "N/A" for jumpers).
    power_w            <- @oid1 ("Power Rating (watts)", numeric
                          string, e.g. "0.125", "0.1").
    voltage_v          <- @oid36 ("Max Working Voltage", numeric
                          string in volts).
    overload_voltage_v <- @oid37 ("Max Overload Voltage", numeric).
                          Captured but not currently emitted into
                          the .xls (no column slot today).
    temp_min_c         <- @oid57 split on "to", left side
                          (e.g. "-55 to +155" -> -55).
    temp_max_c         <- @oid57 split on "to", right side.
    aecq200            <- @oid80 ("AECQ200", "Compliant" /
                          "Not Compliant").

Scope of supported sizes: RMCF lives in 01005..2512, RNCF in 0201..2512.
We carry 01005..1206 to match the rest of the library's footprint
envelope; 1210/2010/2512 drop out at row-build time because their
RESC roots aren't yet in the catalog.
"""

from __future__ import annotations

import os
import re
import sys
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping

# Reach up two levels (stackpole/.. == vendors/) so `_common` is importable
# whether the family script is run via `python build.py` or directly.
_HERE = os.path.dirname(os.path.abspath(__file__))
_VENDORS_DIR = os.path.normpath(os.path.join(_HERE, ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)

import _common  # noqa: E402  -- vendors/_common.py
import _standard  # noqa: E402  -- vendors/_standard.py (after _common: needs _config)


# --- Manufacturer name ----------------------------------------------------
# Database standard: MFG cells are upper case.
MFG = "STACKPOLE ELECTRONICS"


# --- .xls column schema --------------------------------------------------
# Rows follow the shared database standard (vendors/_standard.py): every
# standard resistor column, plus the extra columns below, which only reach
# the workbook when the family enables them (``extra_parameters`` option).
# Three Footprint Path / Ref pairs hold IPC-7351B density variants
# (Nominal / Least / Most) of the same physical part. No alternates
# (MFG 2, MPN 2) .. (MFG 5, MPN 5): Stackpole's RMCF/RNCF orderable MPNs
# already encode their reel-size code in the trailing letter (no
# reel-format-only variants beyond the orderable MPN).
KIND = "R"
SUPPORTED_EXTRAS = ("power",)

SCHLIB = r"house.SchLib"
PCBLIB = r"house.PcbLib"


# --- EIA size -> footprint mapping ---------------------------------------
# RMCF (thick film) and RNCF (thin film) end up on the same set of
# RESC roots even where their as-built body heights differ slightly,
# because the rest of the library already carries those roots from
# Panasonic / Yageo and the house-footprint merge resolves the body
# geometry by priority. Specifically:
#
#   01005:   RMCF body 0.13 mm     (RNCF doesn't ship 01005)
#   0201:    RMCF 0.23 mm   /  RNCF 0.23 mm
#   0402:    RMCF 0.30 mm   /  RNCF 0.30 mm  (existing root: 0.35 mm
#                                              from Panasonic ERJ /
#                                              Yageo RC; merge keeps
#                                              the higher-priority
#                                              vendor's body geometry)
#   0603:    RMCF 0.45 mm   /  RNCF 0.45 mm
#   0805:    RMCF 0.50 mm   /  RNCF 0.55 mm  (existing root: 0.55 mm
#                                              from Yageo, 0.60 mm
#                                              for Panasonic ERJ; we
#                                              map both Stackpole
#                                              flavours to RESC2012X55)
#   1206:    RMCF 0.55 mm   /  RNCF 0.55 mm
#
# 1210, 2010, 2512 are deliberately out of scope until those EIA
# cases get RESC roots elsewhere in the library. RMCF goes down to
# 01005, RNCF starts at 0201.
#
#                       eia:    (metric, fp_root,         L,    W,    H,    T)
SIZE_TO_FOOTPRINT_THICK: Mapping[str, tuple] = {
    "01005": ("0402",  "RESC0402X13", 0.40, 0.20, 0.13, 0.10),
    "0201":  ("0603",  "RESC0603X23", 0.60, 0.30, 0.23, 0.15),
    "0402":  ("1005",  "RESC1005X35", 1.00, 0.50, 0.30, 0.15),
    "0603":  ("1608",  "RESC1608X45", 1.55, 0.80, 0.45, 0.30),
    "0805":  ("2012",  "RESC2012X55", 2.00, 1.25, 0.50, 0.35),
    "1206":  ("3216",  "RESC3216X55", 3.20, 1.60, 0.55, 0.50),
}

SIZE_TO_FOOTPRINT_THIN: Mapping[str, tuple] = {
    # No 01005 in RNCF.
    "0201": ("0603",  "RESC0603X23", 0.58, 0.29, 0.23, 0.12),
    "0402": ("1005",  "RESC1005X35", 1.00, 0.50, 0.30, 0.20),
    "0603": ("1608",  "RESC1608X45", 1.55, 0.80, 0.45, 0.30),
    "0805": ("2012",  "RESC2012X55", 2.00, 1.25, 0.55, 0.30),
    "1206": ("3216",  "RESC3216X55", 3.05, 1.55, 0.55, 0.42),
}


# --- Resistance / tolerance / TCR formatting -----------------------------

# "10 ohm", "4.99 Kohm", "1 Mohm", "0 ohm", "0.5 ohm" -> floats.
# Stackpole writes "Kohm" / "Mohm" with mixed case; tolerant.
_OHM_RE = re.compile(
    r"^\s*([\d.]+)\s*([kKmM]?)\s*ohm\s*$",
    re.IGNORECASE,
)

# "+/- 100 ppm", "+/- 50 ppm", "± 25 ppm", "-100/+200 ppm".
_TCR_RE = re.compile(
    r"^\s*"
    r"(?P<sym>\+/?-|-/?\+|[+\-±])?\s*"
    r"(?P<a>\d+)"
    r"(?:\s*/\s*(?P<sym2>[+\-])\s*(?P<b>\d+))?"
    r"\s*ppm",
    re.IGNORECASE,
)


def parse_resistance(raw: str) -> Decimal | None:
    """Convert Stackpole's ohmic-value string to an exact Decimal in
    ohms (no float noise like ``4990.000000000001``). Returns ``None``
    if the string isn't parseable (e.g. blanks, "Jumper" sentinels,
    anything other than ``<number><unit>ohm``)."""
    m = _OHM_RE.match(raw or "")
    if not m:
        return None
    try:
        value = Decimal(m.group(1))
    except InvalidOperation:
        return None
    unit = (m.group(2) or "").lower()
    if unit == "k":
        value *= 1_000
    elif unit == "m":
        value *= 1_000_000
    return value


def format_resistance(value) -> str:
    """``4700`` -> ``'4.7k'``; ``100`` -> ``'100'``; ``1000000`` ->
    ``'1M'`` (database-standard Value text)."""
    return _standard.ohms(value)


_PERCENT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%\s*$")


def format_tolerance(raw: str) -> str:
    """Canonical percentage text: ``"1%"`` -> ``'1%'``, ``"0.050%"`` ->
    ``'0.05%'``. Jumper rows arrive as ``"< 0.05 ohm"`` -- a maximum
    resistance, not a tolerance -- and become blank (the database
    standard's Tolerance holds percentages only). Anything else passes
    through stripped so :func:`vendors._standard.write_sheet` rejects it
    loudly."""
    s = (raw or "").strip()
    m = _PERCENT_RE.match(s)
    if m:
        return _standard.number(m.group(1)) + "%"
    if "ohm" in s.lower():
        return ""
    return s


def normalize_tcr(raw: str) -> str:
    """Convert Stackpole's TCR strings to the database-standard compact
    ASCII form (ppm/C implied, so no unit). Examples (input -> output):

        ``"+/- 100 ppm"``       -> ``"+/-100"``
        ``"+/- 50 ppm"``        -> ``"+/-50"``
        ``"± 25 ppm"``          -> ``"+/-25"``
        ``"-100/+200 ppm"``     -> ``"-100/+200"``
        ``"N/A"`` / ``""``      -> ``""``
    """
    s = (raw or "").strip()
    if not s or s.upper() == "N/A":
        return ""
    s = s.replace("\u00b1", "+/-").replace("/C", "").replace("/c", "")
    m = _TCR_RE.match(s)
    if not m:
        return s
    a = m.group("a")
    b = m.group("b")
    sym = (m.group("sym") or "").replace("-/+", "+/-").replace("±", "+/-").replace(" ", "")
    if b is None:
        return f"+/-{a}" if sym in ("+/-", "+", "") else f"{sym}{a}"
    sym2 = m.group("sym2") or "+"
    return f"-{a}/{sym2}{b}"


def format_power_w(raw: str) -> str:
    """``"0.125"`` -> ``'125mW'``; ``"0.1"`` -> ``'100mW'``;
    ``"1"`` -> ``'1W'``. Stackpole's parametric search returns
    power as a plain decimal-watts string -- we emit the
    fractional/milliwatt form the rest of the library prefers,
    matching :func:`vendors.yageo._yageo_common.format_power_w`."""
    if not raw:
        return ""
    try:
        p_w = float(raw)
    except ValueError:
        return raw.strip()
    if p_w >= 1:
        return f"{p_w:g}W"
    mw = p_w * 1000
    if abs(mw - round(mw)) < 1e-6:
        return f"{int(round(mw))}mW"
    return f"{mw:g}mW"


def format_voltage_v(raw: str) -> str:
    """``"150"`` -> ``'150V'``; ``"1000"`` -> ``'1000V'`` (database-standard
    Voltage: plain volts, no SI prefix). Stackpole parametric search
    returns voltage as a plain integer string."""
    if not raw:
        return ""
    try:
        return _standard.number(Decimal(raw.strip())) + "V"
    except InvalidOperation:
        return raw.strip()


def format_temp_range(tmin: str, tmax: str) -> str:
    """``("-55", "155")`` -> ``"-55:155"``. Returns ``""`` if either
    side is missing or unparseable."""
    if not tmin or not tmax:
        return ""
    try:
        return f"{int(float(tmin))}:{int(float(tmax))}"
    except ValueError:
        return ""


# --- Per-row builder ------------------------------------------------------

def row_for_part(
    csv_row: Mapping[str, str],
    *,
    family_id: str,
    size_to_footprint: Mapping[str, tuple],
    qualifications: str,
    construction: str,
) -> tuple | None:
    """Return ``(record, fp_root, eia)`` for a CSV row, or ``None`` if the
    part should be dropped (size not in ``size_to_footprint``, ohmic
    value unparseable, or disabled by the active BuildConfig).

    ``record`` is a dict holding every database-standard resistor column
    plus the :data:`SUPPORTED_EXTRAS` columns, ready for
    :func:`vendors._standard.write_sheet`. ``construction`` is the film
    type for the Description (``"THICK FILM"`` for RMCF, ``"THIN FILM"``
    for RNCF); 0-ohm parts become ``RESISTOR JUMPER 0 OHM <package>``.
    """
    eia = csv_row.get("size", "").strip()
    if eia not in size_to_footprint:
        return None
    if eia not in _common.enabled_sizes(family_id):
        return None

    _metric, fp_root, _L, _W, _H, _T = size_to_footprint[eia]

    mpn = csv_row.get("mpn", "").strip()
    if not mpn:
        return None

    ohms = parse_resistance(csv_row.get("resistance_ohms", ""))
    if ohms is None:
        return None

    tol = format_tolerance(csv_row.get("tolerance", ""))
    tcr = normalize_tcr(csv_row.get("tcr", ""))
    power = format_power_w(csv_row.get("power_w", ""))
    volts = format_voltage_v(csv_row.get("voltage_v", ""))
    tr = format_temp_range(
        csv_row.get("temp_min_c", ""),
        csv_row.get("temp_max_c", ""),
    )

    value = format_resistance(ohms)
    package = eia.upper()

    fp_path, fp_ref, fp_path2, fp_ref2, fp_path3, fp_ref3 = (
        _common.xls_footprint_columns(PCBLIB, fp_root, family_id)
    )

    record = {
        "Comment": mpn,
        "Description": _standard.resistor_description(construction, value, tol, package),
        "MFG": MFG,
        "MPN": mpn,
        "Package": package,
        "Library Path": SCHLIB,
        "Library Ref": "RES",
        "Footprint Path": fp_path,
        "Footprint Ref": fp_ref,
        "Footprint Path 2": fp_path2,
        "Footprint Ref 2": fp_ref2,
        "Footprint Path 3": fp_path3,
        "Footprint Ref 3": fp_ref3,
        "Qual": qualifications,
        "Value": value,
        "Tolerance": tol,
        "Voltage": volts,
        "Tcr": tcr,
        "Tr": tr,
        # Extra (non-standard) column; emitted only when enabled.
        "Power": power,
    }
    return record, fp_root, eia


# --- Per-vendor footprints JSON helper ------------------------------------

def build_footprint_rows(
    roots: Iterable[str],
    family_id: str,
    drawing_note: str,
    size_to_footprint: Mapping[str, tuple],
) -> list:
    """Expand ``roots`` (an iterable of footprint-root strings) into one
    JSON row per family-resolved density variant, ready for
    :func:`vendors._common.write_footprints_json`. Roots whose EIA case
    isn't in the family's resolved size set are silently skipped (the
    caller has already filtered, but the size gate here keeps the
    helper independently safe)."""
    enabled = _common.enabled_sizes(family_id)
    bodies = []
    for root in sorted(set(roots)):
        match = next(
            ((eia, *rest) for eia, rest in size_to_footprint.items()
             if rest[1] == root),
            None,
        )
        if match is None:
            raise KeyError(
                f"unknown Stackpole RESC root {root!r}; add it to "
                f"size_to_footprint first"
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
