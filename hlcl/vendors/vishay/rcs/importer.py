"""Offline Vishay RCS importer; see vendors/passive-importers.md."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from _passives import csv_main
from _vishay_passives import decode as decode_catalog
FAMILY = "vishay-rcs"

def decode(row):
    return decode_catalog(row, FAMILY)

def main():
    csv_main(FAMILY, "rcs", HERE / "parts.csv", decode)

if __name__ == "__main__":
    main()
