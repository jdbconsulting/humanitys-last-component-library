"""
Altium DbLib (database library) generator.

Each vendor in this repo ships a per-vendor `.DbLib` file alongside its
`build/<vendor>.xls`. The `.DbLib` is a Windows-style INI file that
binds Altium's symbol/footprint resolver to the workbook's columns:

  - Each worksheet becomes a Table.
  - Each row's `Library Path` / `Library Ref` / `Footprint Path` /
    `Footprint Ref` (×3 IPC-7351B density variants) columns drive
    Altium to fetch the schematic symbol and PCB footprint when a part
    is placed.

Up until now those `.DbLib` files were hand-maintained under
``vendors/<name>/hardcoded/`` and `cp`'d verbatim into ``build/`` by
the (since-deleted) Makefile. They were ~95% boilerplate and 5%
per-vendor (table list, plus a couple of UI-state knobs). This module
replaces all that with a single ``write_dblib`` call per vendor:
every vendor generator script now emits its own `.DbLib` next to its
`.xls` in one shot.

Path-resolution policy
----------------------

The generated `.DbLib` uses two-step path resolution so it stays
portable across machines and project locations:

  1. ``DatabasePathRelative=1`` + ``LibraryDatabasePath=<vendor>.xls``
     resolves the workbook relative to the `.DbLib`'s own directory
     (which for us is always ``build/``). The ConnectionString's
     `Data Source=` value is just a placeholder -- Altium overwrites
     it at load time using ``LibraryDatabasePath`` whenever
     ``DatabasePathRelative=1``. Hence no hardcoded ``D:\\...`` paths
     in the output.

  2. ``LibrarySearchPath=.`` tells Altium to look in the `.DbLib`'s
     own directory when the per-row ``Library Path`` /
     ``Footprint Path`` columns carry a bare basename (no ``.\\``
     prefix). Since ``house.SchLib`` and ``house.PcbLib`` ship in the
     same ``build/`` directory as the `.DbLib`, this is the only
     search root we need.

     Historical note: the legacy hand-maintained `.DbLib` files used
     ``LibrarySearchPath=..\\altium;pcb;sch`` -- three paths none of
     which exist in this repo. They worked only as long as the per-row
     ``Library Path`` had a ``.\\`` prefix forcing relative resolution
     through Altium's "explicit-relative" code path. Stripping the
     prefix from the ``.xls`` rows broke library resolution because
     Altium fell through to ``LibrarySearchPath`` and found nothing.
     Setting ``LibrarySearchPath=.`` makes the bare-basename form
     resolve correctly without depending on that prefix.

Output format
-------------

Altium reads/writes `.DbLib` files as Windows-style INI: CRLF line
endings, Windows-1252 (cp1252) text encoding. We emit the same so a
round-trip through Altium's GUI editor leaves the structural lines
untouched.
"""

from __future__ import annotations

import os
from typing import Iterable


# Standard FieldMap entries Altium expects per Table for our database
# schema. Each tuple is ``(field_name, field_type, parameter_name)``.
# FieldType=0 marks the Comment field (drives the part designator);
# FieldType=1 marks parameters. Columns in the .xls beyond these (e.g.
# MFG, MPN, Value, Tolerance) are auto-discovered by Altium and exposed
# as parameters too -- they don't need explicit FieldMap entries.
_STANDARD_FIELDS = [
    ("Comment",          0, "Comment"),
    ("Description",      1, "[Description]"),
    ("Library Path",     1, "[Library Path]"),
    ("Library Ref",      1, "[Library Ref]"),
    ("Footprint Path",   1, "[Footprint Path]"),
    ("Footprint Ref",    1, "[Footprint Ref]"),
    ("Footprint Path 2", 1, "[Footprint Path 2]"),
    ("Footprint Ref 2",  1, "[Footprint Ref 2]"),
    ("Footprint Path 3", 1, "[Footprint Path 3]"),
    ("Footprint Ref 3",  1, "[Footprint Ref 3]"),
]


def write_dblib(
    path: str,
    vendor_key: str,
    tables: Iterable[str],
    extra_fields: Iterable[str] = (),
) -> None:
    """Write a `.DbLib` for one vendor.

    Args:
        path: Output `.DbLib` path. Conventionally
            ``build/<vendor_key>.DbLib`` so it sits next to the `.xls`
            it binds.
        vendor_key: The `.xls` basename without extension. The generated
            DbLib's ``ConnectionString`` and ``LibraryDatabasePath`` both
            point at ``<vendor_key>.xls`` next to the `.DbLib`.
        tables: Ordered list of worksheet names (no trailing ``$``). The
            first entry becomes ``LastFocusedTable`` and ``Table1`` --
            i.e. the table Altium opens by default in its DbLib browser
            when the user double-clicks the `.DbLib`.
        extra_fields: Optional extra column names beyond the standard
            10. Each gets a FieldMap entry per Table with ``FieldType=1``
            and ``ParameterName=[<name>]``. Use sparingly -- Altium
            auto-discovers all `.xls` columns as parameters anyway, so
            this is only needed when a column needs a non-default
            mapping. (None of the vendors in this repo currently need
            extras.)

    Raises:
        ValueError: If ``tables`` is empty.
    """
    table_list = list(tables)
    if not table_list:
        raise ValueError("write_dblib: tables must contain at least one worksheet name")

    extras = list(extra_fields)
    xls_basename = vendor_key + ".xls"
    primary_table = table_list[0] + "$"

    # Altium expects FieldMap sections numbered FieldMap1..FieldMapN
    # contiguously across the whole file (not reset per Table), so we
    # build the full list first.
    field_map_entries = []
    for table in table_list:
        td = table + "$"
        for fname, ftype, pname in _STANDARD_FIELDS:
            field_map_entries.append((td, fname, ftype, pname))
        for extra in extras:
            field_map_entries.append((td, extra, 1, f"[{extra}]"))

    lines: list[str] = []

    def emit(line: str) -> None:
        lines.append(line)

    emit("[OutputDatabaseLinkFile]")
    emit("Version=1.1")

    emit("[DatabaseLinks]")
    emit(
        f'ConnectionString=Provider=MICROSOFT.ACE.OLEDB.12.0;'
        f'Data Source={xls_basename};'
        f'Extended Properties="Excel 8.0;HDR=Yes;IMEX=1"'
    )
    emit("AddMode=3")
    emit("RemoveMode=1")
    emit("UpdateMode=2")
    emit("ViewMode=0")
    emit("LeftQuote=[")
    emit("RightQuote=]")
    emit("QuoteTableNames=1")
    emit("UseTableSchemaName=0")
    emit("DefaultColumnType=VARCHAR(255)")
    emit("LibraryDatabaseType=Microsoft Excel")
    emit(f"LibraryDatabasePath={xls_basename}")
    emit("DatabasePathRelative=1")
    emit("TopPanelCollapsed=0")
    emit("LibrarySearchPath=.")
    emit("OrcadMultiValueDelimiter=,")
    emit("SearchSubDirectories=1")
    emit("SchemaName=")
    emit(f"LastFocusedTable={primary_table}")

    for i, table in enumerate(table_list, start=1):
        emit(f"[Table{i}]")
        emit("SchemaName=")
        emit(f"TableName={table}$")
        emit("Enabled=True")
        emit("UserWhere=0")
        emit("UserWhereText=")

    for i, (td, fname, ftype, pname) in enumerate(field_map_entries, start=1):
        emit(f"[FieldMap{i}]")
        emit(
            f"Options=FieldName={td}.{fname}|TableNameOnly={td}|"
            f"FieldNameOnly={fname}|FieldType={ftype}|"
            f"ParameterName={pname}|VisibleOnAdd=False|"
            f"AddMode=0|RemoveMode=0|UpdateMode=0"
        )

    text = "\r\n".join(lines) + "\r\n"
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode("cp1252"))
