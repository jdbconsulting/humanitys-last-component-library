"""Database standard for every generated workbook.

The website's Database standards page (``/docs/database-standards/``) is
the human-readable version of this module. Generators build each row as a
dict keyed by column name: every standard column for the component kind,
plus any extra (non-standard) columns the family can supply. ``write_sheet``
emits the standard columns in order, then only the extras the family
enabled on the Libraries tab (``extra_parameters`` option), and rejects
rows that break the general rules.

Kinds: ``R`` resistor, ``C`` capacitor, ``I`` inductor, ``FB`` ferrite bead.
"""
from __future__ import annotations

from decimal import Decimal
import re
from typing import Iterable, Mapping

import _config

COMMON = [
    "Comment", "Description", "MFG", "MPN", "Package", "Library Path",
    "Library Ref", "Footprint Path", "Footprint Ref", "Footprint Path 2",
    "Footprint Ref 2", "Footprint Path 3", "Footprint Ref 3", "Qual",
]
TYPE_FIELDS = {
    "R": ["Value", "Tolerance", "Voltage", "Tcr", "Tr"],
    "C": ["Value", "Tolerance", "Voltage", "Tcr", "Tr"],
    "I": ["Value", "Tolerance", "DCR", "Current", "Tr"],
    "FB": ["Value", "Current", "DCR", "Tr"],
}
#: Extra-parameter option ids (catalog ``extra_parameters`` choices) and the
#: columns each adds, in output order.
EXTRAS = {
    "power": ["Power"],
    "features": ["Features"],
    "rating_conditions": ["Rating Conditions"],
    "datasheet": ["Datasheet"],
    "alternates": ["MFG 2", "MPN 2", "MFG 3", "MPN 3", "MFG 4", "MPN 4", "MFG 5", "MPN 5"],
    "srf": ["SRF"],
    "q": ["Q"],
}
EXTRA_OPTION = "extra_parameters"

_DESCRIPTION_PREFIX = {"R": "RESISTOR ", "C": "CAPACITOR CERAMIC ",
                       "I": "INDUCTOR ", "FB": "FERRITE BEAD "}
_NUM = r"\d+(\.\d+)?"
_FIELD_RULES = {
    "Tolerance": rf"({_NUM}%|\+/-{_NUM}[pnum]?[FH])",
    "Voltage": rf"{_NUM}V",
    "Tr": r"-?\d+:-?\d+",
    "Tcr": r"[-+][^\s]*",
    "DCR": rf"{_NUM}m?",
    "Current": rf"{_NUM}m?A",
}
_VALUE_RULES = {
    "R": rf"{_NUM}[kM]?",
    "C": rf"{_NUM}[pnum]F",
    "I": rf"{_NUM}[pnum]H",
    "FB": rf"{_NUM}K?OHM",
}


# --- Value formatting ------------------------------------------------------

def number(value) -> str:
    """Plain decimal text without exponent or trailing zeros."""
    return format(Decimal(str(value)).normalize(), "f")


def _scaled(value, steps) -> tuple[str, str]:
    value = Decimal(str(value))
    for scale, suffix in steps:
        if value >= scale:
            return number(value / scale), suffix
    return number(value), ""


def ohms(value) -> str:
    """Resistance field notation: 100, 4.7k, 1M (no OHM)."""
    text, suffix = _scaled(value, [(Decimal("1e6"), "M"), (Decimal("1e3"), "k")])
    return text + suffix


def ohms_description(value) -> str:
    """Resistance in descriptions: 100, 4.7K, 2.2M (plain below 1 kOhm)."""
    return ohms(value).upper()


def dcr(value) -> str:
    """DC resistance field, ohms implied: 0.1, 2.1m (milli below 0.1 Ohm)."""
    value = Decimal(str(value))
    return number(value * 1000) + "m" if 0 < value < Decimal("0.1") else number(value)


def current(amps) -> str:
    """Current field: 300mA, 1.5A."""
    amps = Decimal(str(amps))
    return number(amps * 1000) + "mA" if 0 < amps < 1 else number(amps) + "A"


def capacitance(pf) -> str:
    """Capacitance field: 100pF, 4.7nF, 10uF."""
    text, suffix = _scaled(pf, [(Decimal("1e9"), "m"), (Decimal("1e6"), "u"), (Decimal("1e3"), "n")])
    return text + (suffix or "p") + "F"


def inductance(nh) -> str:
    """Inductance field: 100nH, 4.7uH, 10mH."""
    text, suffix = _scaled(nh, [(Decimal("1e6"), "m"), (Decimal("1e3"), "u")])
    return text + (suffix or "n") + "H"


def impedance(value) -> str:
    """Ferrite impedance field: 60OHM, 1KOHM."""
    return ohms_description(value) + "OHM"


# --- Descriptions ---------------------------------------------------------
# Built from the already-formatted field values, so a description can never
# disagree with the cells in its own row.

def resistor_description(construction: str, value: str, tolerance: str, package: str) -> str:
    """RESISTOR THICK FILM 4.7K OHM 1% 0402, or RESISTOR JUMPER 0 OHM 0402."""
    if value == "0":
        return f"RESISTOR JUMPER 0 OHM {package}"
    return f"RESISTOR {construction} {value} OHM {tolerance} {package}".upper()


def capacitor_description(value: str, tolerance: str, voltage: str, dielectric: str,
                          package: str) -> str:
    """CAPACITOR CERAMIC 100NF 10% 16V X7R 0402."""
    return f"CAPACITOR CERAMIC {value} {tolerance} {voltage} {dielectric} {package}".upper()


def inductor_description(construction: str, value: str, tolerance: str, dcr_value: str,
                         package: str) -> str:
    """INDUCTOR MULTILAYER 4.7UH 20% 0.1 OHM 0402 (DCR as a plain number)."""
    ohm = Decimal(dcr_value[:-1]) / 1000 if dcr_value.endswith("m") else Decimal(dcr_value)
    return f"INDUCTOR {construction} {value} {tolerance} {number(ohm)} OHM {package}".upper()


def ferrite_description(value: str, current_value: str, package: str) -> str:
    """FERRITE BEAD 60 OHM 1A 0402, from the 60OHM / 1A field values."""
    return f"FERRITE BEAD {value[:-3]} OHM {current_value} {package}".upper()


# --- Rows and sheets ------------------------------------------------------

def enabled_extras(family_id: str, supported: Iterable[str]) -> list[str]:
    """Extra-parameter ids the family enabled, in EXTRAS order."""
    chosen = _config.current().family(family_id).get_option(EXTRA_OPTION, []) or []
    unsupported = set(chosen) - set(supported)
    if unsupported:
        raise ValueError(f"{family_id}: unsupported extra parameters {sorted(unsupported)}")
    return [key for key in EXTRAS if key in chosen]


def headers(kind: str, extras: Iterable[str]) -> list[str]:
    return COMMON + TYPE_FIELDS[kind] + [c for key in extras for c in EXTRAS[key]]


def check(kind: str, row: Mapping[str, str]) -> None:
    """Raise ValueError if ``row`` breaks the database standard."""
    mpn = row.get("MPN", "")
    problems = []
    if not mpn or row.get("Comment") != mpn:
        problems.append("Comment must equal a non-empty MPN")
    description = row["Description"]
    if (description != description.upper() or description.endswith(".")
            or "\n" in description or not description.startswith(_DESCRIPTION_PREFIX[kind])):
        problems.append(f"description {description!r}")
    for column in ["MFG", "Package"] + [f"MFG {n}" for n in range(2, 6)]:
        if row.get(column, "") != row.get(column, "").upper():
            problems.append(f"{column} must be upper case")
    if row["Value"] and not re.fullmatch(_VALUE_RULES[kind], row["Value"]):
        problems.append(f"Value {row['Value']!r}")
    for column, rule in _FIELD_RULES.items():
        value = row.get(column, "")
        if value and not re.fullmatch(rule, value):
            problems.append(f"{column} {value!r}")
    if not all(cell.isascii() for cell in row.values()):
        problems.append("non-ASCII text")
    if problems:
        raise ValueError(f"{mpn or '?'}: violates the database standard: {'; '.join(problems)}")


def cells(kind: str, extras: Iterable[str], record: Mapping[str, object]) -> list[str]:
    """Ordered, validated cells for one record."""
    missing = [c for c in COMMON + TYPE_FIELDS[kind] if c not in record]
    if missing:
        raise ValueError(f"{record.get('MPN', '?')}: missing standard columns {missing}")
    columns = headers(kind, extras)
    row = {c: "" if record.get(c) is None else str(record.get(c, "")) for c in columns}
    check(kind, row)
    return [row[c] for c in columns]


def write_sheet(sheet, kind: str, family_id: str, records: Iterable[Mapping[str, object]],
                supported: Iterable[str] = ()) -> int:
    """Write the header and validated rows to an xlwt sheet; return the row count.

    Alternate MFG n / MPN n pairs are written only when some row in the
    sheet fills them, so a family whose parts have at most one alternate
    exports MFG 2 / MPN 2 and nothing beyond.
    """
    extras = enabled_extras(family_id, supported)
    columns = headers(kind, extras)
    rows = [cells(kind, extras, record) for record in records]
    unused = set()
    for n in range(2, 6):
        pair = [columns.index(c) for c in (f"MFG {n}", f"MPN {n}") if c in columns]
        if pair and not any(row[i] for row in rows for i in pair):
            unused.update(pair)
    keep = [i for i in range(len(columns)) if i not in unused]
    for col, i in enumerate(keep):
        sheet.write(0, col, columns[i])
    for r, row in enumerate(rows, 1):
        for col, i in enumerate(keep):
            sheet.write(r, col, row[i])
    return len(rows)
