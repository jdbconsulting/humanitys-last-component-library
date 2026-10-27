"""Shared output for datasheet-backed passive importers.

Network acquisition belongs in separate refresh tools. Builds only consume
checked-in data and reject malformed rows instead of silently guessing a code.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import xlwt

import _common
import _dblib

ROOT = Path(__file__).resolve().parents[1]
HEADERS = [
    "Comment", "Description", "MFG", "MPN", "Package", "Value",
    "Tolerance", "Tcr", "Tr", "Qual", "Voltage", "Power", "Features",
    "Rating Conditions", "Datasheet", "Library Path", "Library Ref",
    "Footprint Path", "Footprint Ref", "Footprint Path 2", "Footprint Ref 2",
    "Footprint Path 3", "Footprint Ref 3",
]
# Database standard (website docs: /docs/database-standards): common fields,
# then resistor fields, and nothing the standard does not define.
RESISTOR_HEADERS = [
    "Comment", "Description", "MFG", "MPN", "Package", "Library Path",
    "Library Ref", "Footprint Path", "Footprint Ref", "Footprint Path 2",
    "Footprint Ref 2", "Footprint Path 3", "Footprint Ref 3", "Qual",
    "Value", "Tolerance", "Voltage", "Tcr", "Tr",
]


def number(value) -> str:
    return format(Decimal(str(value)).normalize(), "f")


def resistance(value) -> str:
    value = Decimal(str(value))
    for scale, suffix in [(Decimal("1e6"), "M"), (Decimal("1e3"), "k")]:
        if value >= scale:
            return number(value / scale) + suffix
    return number(value)


def capacitance(pf) -> str:
    value = Decimal(str(pf))
    for scale, suffix in [(Decimal("1e9"), "mF"), (Decimal("1e6"), "uF"),
                          (Decimal("1e3"), "nF")]:
        if value >= scale:
            return number(value / scale) + suffix
    return number(value) + "pF"


def code_value(code: str) -> Decimal:
    """Three significant digits + exponent, or an embedded R/K/M decimal."""
    for letter, scale in [("R", 1), ("K", 1000), ("M", 1000000)]:
        if letter in code:
            return Decimal(code.replace(letter, ".")) * scale
    if not code.isdigit() or len(code) not in (3, 4):
        raise ValueError(f"invalid value code: {code!r}")
    return Decimal(code[:-1]) * Decimal(10) ** int(code[-1])


def height_code(mm) -> str:
    return f"{int((Decimal(str(mm)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)):02d}"


@dataclass(frozen=True)
class Part:
    mpn: str
    manufacturer: str
    package: str
    kind: str
    value: str
    tolerance: str
    tcr: str
    temperature: str
    qualification: str
    voltage: str
    power: str
    features: str
    conditions: str
    datasheet: str
    geometry: dict = field(compare=False)
    construction: str = ""  # e.g. "THICK FILM"; required by standard_cells


    def cells(self, family):
        symbol = "CAP" if self.kind == "C" else "RES"
        description = f"{symbol} {self.features} {self.value} {self.tolerance} {self.voltage} {self.package}".strip()
        return [self.mpn, description, self.manufacturer, self.mpn, self.package,
                self.value, self.tolerance, self.tcr, self.temperature,
                self.qualification, self.voltage, self.power, self.features,
                self.conditions, self.datasheet, "house.SchLib", symbol,
                *_common.xls_footprint_columns("house.PcbLib", self.geometry["root"], family)]

    def standard_cells(self, family):
        """RESISTOR_HEADERS row; rejects rows that break the database standard."""
        if self.kind != "R" or not self.construction:
            raise ValueError(f"{self.mpn}: the standard schema needs a resistor construction")
        if self.value == "0":
            description = f"RESISTOR JUMPER 0 OHM {self.package}"
        else:
            description = (f"RESISTOR {self.construction} {self.value.upper()} OHM "
                           f"{self.tolerance} {self.package}")
        cells = [self.mpn, description, self.manufacturer.upper(), self.mpn,
                 self.package.upper(), "house.SchLib", "RES",
                 *_common.xls_footprint_columns("house.PcbLib", self.geometry["root"], family),
                 self.qualification, self.value, self.tolerance, self.voltage, self.tcr,
                 self.temperature]
        if (description != description.upper() or description.endswith(".")
                or not all(cell.isascii() for cell in cells)):
            raise ValueError(f"{self.mpn}: row violates the database standard: {cells!r}")
        return cells


def body(prefix, metric, height, qualifier, length, width, terminal, source, **extra):
    """Qualifiers prevent distinct terminal geometries merging by body size."""
    result = {
        "root": f"{prefix}{metric}X{height_code(height)}_{qualifier}",
        "kind": "C" if prefix == "CAPC" else "R",
        "drawingNote": source,
        "bodyMm": {"lengthNominal": float(length), "widthNominal": float(width),
                   "heightNominal": float(height), "terminalLengthNominal": float(terminal)},
    }
    result.update(extra)
    return result


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def run(family, sheet_name, parts, standard=False):
    """Validate first, then emit an offline workbook, DbLib and footprint set.

    ``standard`` selects RESISTOR_HEADERS and Part.standard_cells.
    """
    enabled = _common.enabled_sizes(family)
    seen, geometries, accepted = set(), {}, []
    for part in parts:
        if part.mpn in seen:
            raise ValueError(f"duplicate MPN: {part.mpn}")
        seen.add(part.mpn)
        if part.package not in enabled:
            continue
        geom = part.geometry
        root = geom["root"]
        if root in geometries and geometries[root] != geom:
            raise ValueError(f"conflicting geometry for {root}")
        geometries[root] = geom
        accepted.append(part)
    footprints = _common.expand_footprint_rows(geometries.values(), family)
    for fp in footprints:
        _common._validate_footprint(fp)
    wb = xlwt.Workbook()
    sheet = wb.add_sheet(sheet_name)
    for col, heading in enumerate(RESISTOR_HEADERS if standard else HEADERS):
        sheet.write(0, col, heading)
    for row, part in enumerate(sorted(accepted, key=lambda p: p.mpn), 1):
        cells = part.standard_cells(family) if standard else part.cells(family)
        for col, cell in enumerate(cells):
            sheet.write(row, col, cell)
    output = ROOT / "build" / "output"
    output.mkdir(parents=True, exist_ok=True)
    wb.save(str(output / f"{family}.xls"))
    _dblib.write_dblib(str(output / f"{family}.DbLib"), vendor_key=family, tables=[sheet_name])
    _common.write_footprints_json(str(ROOT / "build" / "intermediate" / "footprints" /
                                      f"{family}-footprints.json"), family, footprints)
    print(f"{family}: {len(accepted)} parts, {len(footprints)} footprints")


def csv_main(family, sheet, default_input, decoder, standard=False):
    parser = argparse.ArgumentParser(description=f"Build {family} from a verified offline catalog")
    parser.add_argument("--input", default=str(default_input))
    args = parser.parse_args()
    parts = []
    for line, row in enumerate(read_csv(args.input), 2):
        try:
            part = decoder(row)
            if part is not None:
                parts.append(part)
        except (ValueError, KeyError, ArithmeticError) as exc:
            raise ValueError(f"{args.input}:{line}: {exc}") from exc
    run(family, sheet, parts, standard)
