#!/usr/bin/env python

import os
import sys
from sys import *
import xlwt
from xlwt import Workbook

# Make the shared `vendors/_common.py` helper importable regardless of cwd.
_VENDORS_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _VENDORS_DIR not in sys.path:
    sys.path.insert(0, _VENDORS_DIR)
import _common as _vendor_common

# Output goes to <project_root>/build/ (database workbook used by the
# Altium DbLib) and <project_root>/build/footprints/ (per-vendor JSON
# footprint specifications consumed by the merge step and the .PcbLib
# autogenerator) regardless of cwd.
BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build")
FOOTPRINTS_DIR = os.path.join(BUILD_DIR, "footprints")

# --- IPC-SM-782 RESC footprint catalogue used by this script -------------
# Each entry pairs a unique component body (length / width / max-height in
# mm + Panasonic ERJ-family terminal/band length) with its IPC-SM-782 code:
#
#     RESCxxyyXzz  (xx, yy in 1/10 mm; zz in 1/100 mm, min 2 digits, round
#                   half up; trailing density-level letter L / N / M is
#                   appended at use-site)
#
# Heights are encoded *consistently* in 1/100 mm with no special-casing for
# round-tenths-of-mm values (so 0.30 mm -> '30', not '03'; 0.13 mm -> '13',
# not '013'). The two-digit minimum-pad survives sub-tenth heights such as
# 0.065 mm -> '07' (the README's worked example). Heights >= 1.00 mm
# naturally spill to three digits (e.g. 1.25 mm -> '125').
#
# `source` is the part family the dimensions came from, written into the
# `drawingNote` field of the per-vendor footprints JSON so a downstream
# reviewer can trace the geometry back to its datasheet.
RESC_FOOTPRINTS = [
    # (root,         L,   W,   H,    T,    EIA,    source family)
    ("RESC0402X13", 0.4, 0.2, 0.13, 0.10, "01005", "Panasonic ERJ-XGN (01005 thick film)"),
    ("RESC0603X23", 0.6, 0.3, 0.23, 0.15, "0201",  "Panasonic ERJ-1GN / ERJ-1GJ / ERA-1A (0201)"),
    ("RESC1005X35", 1.0, 0.5, 0.35, 0.25, "0402",  "Panasonic ERJ-2 / ERA-2 (0402)"),
    ("RESC1608X45", 1.6, 0.8, 0.45, 0.30, "0603",  "Panasonic ERJ-3 / ERA-3 (0603)"),
    ("RESC2012X55", 2.0, 1.2, 0.55, 0.40, "0805",  "Panasonic ERA-6V / ERA-6K (0805 thin film)"),
    ("RESC2012X60", 2.0, 1.2, 0.60, 0.40, "0805",  "Panasonic ERJ-6 (0805 thick film)"),
    ("RESC3216X55", 3.2, 1.6, 0.55, 0.50, "1206",  "Panasonic ERA-8P (1206 thin film)"),
]

def format_number(num):
    if 1 <= num < 10:
        int_part = int(num)
        frac_str = "{:.2f}".format(num - int_part)[2:]
        return "{}R{}".format(int_part, frac_str)
    elif 10 <= num < 100:
        int_part = int(num)
        frac_part = round(num - int_part, 1)
        frac_part = int(str(frac_part)[2:]) if '.' in str(frac_part) else 0
        return "{:02d}R{}".format(int_part, frac_part)
    elif num >= 100:
        str_num = str(int(num))
        trailing_zeros = str_num[3:].count('0')
        return "{}{}".format(str_num[:3], trailing_zeros)
    else:
        return "Number not in range."

def format_resistance(value):
    if value < 1000:
        return str(value) if value % 1 != 0 else str(int(value))
    elif value < 1000000:
        k_val = value / 1000
        return "{}k".format(k_val if k_val % 1 != 0 else int(k_val))
    else:
        m_val = value / 1000000
        return "{}M".format(m_val if m_val % 1 != 0 else int(m_val))

def make_res_range(vendor, prefix, suffix, values, power, voltage, tolerance, tcr, tr, qualifications, eiacase, schematic, schem_lib, footprints, fp_libs):
	table = [];
	for x in values:
		pn = prefix + format_number(x) + suffix
		description = "RESISTOR THICK FILM " + format_resistance(x) + " OHM " + tolerance + " " + eiacase
		row = [pn, description, vendor, pn, eiacase, format_resistance(x), tolerance, tcr, tr, qualifications, voltage, schem_lib, schematic]
		for y in range(0,3):
			row = row + [fp_libs[y], footprints[y]]
		table.append(row)
	return table

def make_res_jumper(vendor, pn, current, eiacase, schematic, schem_lib, footprints, fp_libs):
	table = [];
	description = "RESISTOR JUMPER 0 OHM " + eiacase
	row = [pn, description, vendor, pn, eiacase, '0', '' , '', '', '', '', schem_lib, schematic]
	for y in range(0,3):
		row = row + [fp_libs[y], footprints[y]]
	table.append(row)
	return table

e24_e96_combined_1_9R76 = [1,1.02,1.05,1.07,1.1,1.13,1.15,1.18,1.2,1.21,1.24,1.27,1.3,1.33,1.37,1.4,1.43,1.47,1.5,1.54,1.58,1.6,1.62,1.65,1.69,1.74,1.78,1.8,1.82,1.87,1.91,1.96,2,2.05,2.1,2.15,2.2,2.21,2.26,2.32,2.37,2.4,2.43,2.49,2.55,2.61,2.67,2.7,2.74,2.8,2.87,2.94,3,3.01,3.09,3.16,3.24,3.3,3.32,3.4,3.48,3.57,3.6,3.65,3.74,3.83,3.9,3.92,4.02,4.12,4.22,4.3,4.32,4.42,4.53,4.64,4.7,4.75,4.87,4.99,5.1,5.11,5.23,5.36,5.49,5.6,5.62,5.76,5.9,6.04,6.19,6.2,6.34,6.49,6.65,6.8,6.81,6.98,7.15,7.32,7.5,7.68,7.87,8.06,8.2,8.25,8.45,8.66,8.87,9.09,9.1,9.31,9.53,9.76]
e24_e96_combined_10_97R6 = [10,10.2,10.5,10.7,11,11.3,11.5,11.8,12,12.1,12.4,12.7,13,13.3,13.7,14,14.3,14.7,15,15.4,15.8,16,16.2,16.5,16.9,17.4,17.8,18,18.2,18.7,19.1,19.6,20,20.5,21,21.5,22,22.1,22.6,23.2,23.7,24,24.3,24.9,25.5,26.1,26.7,27,27.4,28,28.7,29.4,30,30.1,30.9,31.6,32.4,33,33.2,34,34.8,35.7,36,36.5,37.4,38.3,39,39.2,40.2,41.2,42.2,43,43.2,44.2,45.3,46.4,47,47.5,48.7,49.9,51,51.1,52.3,53.6,54.9,56,56.2,57.6,59,60.4,61.9,62,63.4,64.9,66.5,68,68.1,69.8,71.5,73.2,75,76.8,78.7,80.6,82,82.5,84.5,86.6,88.7,90.9,91,93.1,95.3,97.6]
e24_e96_combined_100_1M = [100,102,105,107,110,113,115,118,120,121,124,127,130,133,137,140,143,147,150,154,158,160,162,165,169,174,178,180,182,187,191,196,200,205,210,215,220,221,226,232,237,240,243,249,255,261,267,270,274,280,287,294,300,301,309,316,324,330,332,340,348,357,360,365,374,383,390,392,402,412,422,430,432,442,453,464,470,475,487,499,510,511,523,536,549,560,562,576,590,604,619,620,634,649,665,680,681,698,715,732,750,768,787,806,820,825,845,866,887,909,910,931,953,976,1000,1020,1050,1070,1100,1130,1150,1180,1200,1210,1240,1270,1300,1330,1370,1400,1430,1470,1500,1540,1580,1600,1620,1650,1690,1740,1780,1800,1820,1870,1910,1960,2000,2050,2100,2150,2200,2210,2260,2320,2370,2400,2430,2490,2550,2610,2670,2700,2740,2800,2870,2940,3000,3010,3090,3160,3240,3300,3320,3400,3480,3570,3600,3650,3740,3830,3900,3920,4020,4120,4220,4300,4320,4420,4530,4640,4700,4750,4870,4990,5100,5110,5230,5360,5490,5600,5620,5760,5900,6040,6190,6200,6340,6490,6650,6800,6810,6980,7150,7320,7500,7680,7870,8060,8200,8250,8450,8660,8870,9090,9100,9310,9530,9760,10000,10200,10500,10700,11000,11300,11500,11800,12000,12100,12400,12700,13000,13300,13700,14000,14300,14700,15000,15400,15800,16000,16200,16500,16900,17400,17800,18000,18200,18700,19100,19600,20000,20500,21000,21500,22000,22100,22600,23200,23700,24000,24300,24900,25500,26100,26700,27000,27400,28000,28700,29400,30000,30100,30900,31600,32400,33000,33200,34000,34800,35700,36000,36500,37400,38300,39000,39200,40200,41200,42200,43000,43200,44200,45300,46400,47000,47500,48700,49900,51000,51100,52300,53600,54900,56000,56200,57600,59000,60400,61900,62000,63400,64900,66500,68000,68100,69800,71500,73200,75000,76800,78700,80600,82000,82500,84500,86600,88700,90900,91000,93100,95300,97600,100000,102000,105000,107000,110000,113000,115000,118000,120000,121000,124000,127000,130000,133000,137000,140000,143000,147000,150000,154000,158000,160000,162000,165000,169000,174000,178000,180000,182000,187000,191000,196000,200000,205000,210000,215000,220000,221000,226000,232000,237000,240000,243000,249000,255000,261000,267000,270000,274000,280000,287000,294000,300000,301000,309000,316000,324000,330000,332000,340000,348000,357000,360000,365000,374000,383000,390000,392000,402000,412000,422000,430000,432000,442000,453000,464000,470000,475000,487000,499000,510000,511000,523000,536000,549000,560000,562000,576000,590000,604000,619000,620000,634000,649000,665000,680000,681000,698000,715000,732000,750000,768000,787000,806000,820000,825000,845000,866000,887000,909000,910000,931000,953000,976000,1000000]
e24_e96_combined_10_1M = e24_e96_combined_10_97R6 + e24_e96_combined_100_1M
e24_e96_combined_1M02_10M = [1020000,1050000,1070000,1100000,1130000,1150000,1180000,1200000,1210000,1240000,1270000,1300000,1330000,1370000,1400000,1430000,1470000,1500000,1540000,1580000,1600000,1620000,1650000,1690000,1740000,1780000,1800000,1820000,1870000,1910000,1960000,2000000,2050000,2100000,2150000,2200000,2210000,2260000,2320000,2370000,2400000,2430000,2490000,2550000,2610000,2670000,2700000,2740000,2800000,2870000,2940000,3000000,3010000,3090000,3160000,3240000,3300000,3320000,3400000,3480000,3570000,3600000,3650000,3740000,3830000,3900000,3920000,4020000,4120000,4220000,4300000,4320000,4420000,4530000,4640000,4700000,4750000,4870000,4990000,5100000,5110000,5230000,5360000,5490000,5600000,5620000,5760000,5900000,6040000,6190000,6200000,6340000,6490000,6650000,6800000,6810000,6980000,7150000,7320000,7500000,7680000,7870000,8060000,8200000,8250000,8450000,8660000,8870000,9090000,9100000,9310000,9530000,9760000,10000000]
e24_e96_combined_1M02_2M2 = [1020000,1050000,1070000,1100000,1130000,1150000,1180000,1200000,1210000,1240000,1270000,1300000,1330000,1370000,1400000,1430000,1470000,1500000,1540000,1580000,1600000,1620000,1650000,1690000,1740000,1780000,1800000,1820000,1870000,1910000,1960000,2000000,2050000,2100000,2150000,2200000]
e24_e96_combined_10_2M2 = e24_e96_combined_10_1M + e24_e96_combined_1M02_2M2

e24_e96_combined_200_1M = [200,205,210,215,220,221,226,232,237,240,243,249,255,261,267,270,274,280,287,294,300,301,309,316,324,330,332,340,348,357,360,365,374,383,390,392,402,412,422,430,432,442,453,464,470,475,487,499,510,511,523,536,549,560,562,576,590,604,619,620,634,649,665,680,681,698,715,732,750,768,787,806,820,825,845,866,887,909,910,931,953,976,1000,1020,1050,1070,1100,1130,1150,1180,1200,1210,1240,1270,1300,1330,1370,1400,1430,1470,1500,1540,1580,1600,1620,1650,1690,1740,1780,1800,1820,1870,1910,1960,2000,2050,2100,2150,2200,2210,2260,2320,2370,2400,2430,2490,2550,2610,2670,2700,2740,2800,2870,2940,3000,3010,3090,3160,3240,3300,3320,3400,3480,3570,3600,3650,3740,3830,3900,3920,4020,4120,4220,4300,4320,4420,4530,4640,4700,4750,4870,4990,5100,5110,5230,5360,5490,5600,5620,5760,5900,6040,6190,6200,6340,6490,6650,6800,6810,6980,7150,7320,7500,7680,7870,8060,8200,8250,8450,8660,8870,9090,9100,9310,9530,9760,10000,10200,10500,10700,11000,11300,11500,11800,12000,12100,12400,12700,13000,13300,13700,14000,14300,14700,15000,15400,15800,16000,16200,16500,16900,17400,17800,18000,18200,18700,19100,19600,20000,20500,21000,21500,22000,22100,22600,23200,23700,24000,24300,24900,25500,26100,26700,27000,27400,28000,28700,29400,30000,30100,30900,31600,32400,33000,33200,34000,34800,35700,36000,36500,37400,38300,39000,39200,40200,41200,42200,43000,43200,44200,45300,46400,47000,47500,48700,49900,51000,51100,52300,53600,54900,56000,56200,57600,59000,60400,61900,62000,63400,64900,66500,68000,68100,69800,71500,73200,75000,76800,78700,80600,82000,82500,84500,86600,88700,90900,91000,93100,95300,97600,100000,102000,105000,107000,110000,113000,115000,118000,120000,121000,124000,127000,130000,133000,137000,140000,143000,147000,150000,154000,158000,160000,162000,165000,169000,174000,178000,180000,182000,187000,191000,196000,200000,205000,210000,215000,220000,221000,226000,232000,237000,240000,243000,249000,255000,261000,267000,270000,274000,280000,287000,294000,300000,301000,309000,316000,324000,330000,332000,340000,348000,357000,360000,365000,374000,383000,390000,392000,402000,412000,422000,430000,432000,442000,453000,464000,470000,475000,487000,499000,510000,511000,523000,536000,549000,560000,562000,576000,590000,604000,619000,620000,634000,649000,665000,680000,681000,698000,715000,732000,750000,768000,787000,806000,820000,825000,845000,866000,887000,909000,910000,931000,953000,976000,1000000]
e24_e96_combined_200_100K = [200,205,210,215,220,221,226,232,237,240,243,249,255,261,267,270,274,280,287,294,300,301,309,316,324,330,332,340,348,357,360,365,374,383,390,392,402,412,422,430,432,442,453,464,470,475,487,499,510,511,523,536,549,560,562,576,590,604,619,620,634,649,665,680,681,698,715,732,750,768,787,806,820,825,845,866,887,909,910,931,953,976,1000,1020,1050,1070,1100,1130,1150,1180,1200,1210,1240,1270,1300,1330,1370,1400,1430,1470,1500,1540,1580,1600,1620,1650,1690,1740,1780,1800,1820,1870,1910,1960,2000,2050,2100,2150,2200,2210,2260,2320,2370,2400,2430,2490,2550,2610,2670,2700,2740,2800,2870,2940,3000,3010,3090,3160,3240,3300,3320,3400,3480,3570,3600,3650,3740,3830,3900,3920,4020,4120,4220,4300,4320,4420,4530,4640,4700,4750,4870,4990,5100,5110,5230,5360,5490,5600,5620,5760,5900,6040,6190,6200,6340,6490,6650,6800,6810,6980,7150,7320,7500,7680,7870,8060,8200,8250,8450,8660,8870,9090,9100,9310,9530,9760,10000,10200,10500,10700,11000,11300,11500,11800,12000,12100,12400,12700,13000,13300,13700,14000,14300,14700,15000,15400,15800,16000,16200,16500,16900,17400,17800,18000,18200,18700,19100,19600,20000,20500,21000,21500,22000,22100,22600,23200,23700,24000,24300,24900,25500,26100,26700,27000,27400,28000,28700,29400,30000,30100,30900,31600,32400,33000,33200,34000,34800,35700,36000,36500,37400,38300,39000,39200,40200,41200,42200,43000,43200,44200,45300,46400,47000,47500,48700,49900,51000,51100,52300,53600,54900,56000,56200,57600,59000,60400,61900,62000,63400,64900,66500,68000,68100,69800,71500,73200,75000,76800,78700,80600,82000,82500,84500,86600,88700,90900,91000,93100,95300,97600,100000]

# ERA resistance ranges
# Sub-100 ohm: only E24 values are available (4-digit E96 code requires multiplier >= 0)
e24_only_47_91 = [47, 51, 56, 62, 68, 75, 82, 91]
era_100_10k = [v for v in e24_e96_combined_100_1M if v <= 10000]          # ERA-1AEB (0201)
era_47_100K = e24_only_47_91 + [v for v in e24_e96_combined_100_1M if v <= 100000]  # ERA-V low range
era_102K_330K = [v for v in e24_e96_combined_100_1M if 102000 <= v <= 330000]       # ERA-3KEB high range
era_102K_820K = [v for v in e24_e96_combined_100_1M if 102000 <= v <= 820000]       # ERA-6KEB high range
era_160K_1M = [v for v in e24_e96_combined_100_1M if 160000 <= v <= 1000000]        # ERA-8PEB high voltage

# ERA-A part numbering: E24 values use 3-digit codes, E96-only values use 4-digit codes
e24_base = {10,11,12,13,15,16,18,20,22,24,27,30,33,36,39,43,47,51,56,62,68,75,82,91}

def is_e24(ohms):
    v = float(ohms)
    while v >= 100:
        v /= 10
    while v < 10:
        v *= 10
    for e24v in e24_base:
        if abs(v - e24v) < 0.01:
            return True
    return False

def format_number_era(num):
    s = str(int(num))
    if is_e24(num):
        return s[:2] + str(len(s) - 2)
    else:
        return s[:3] + str(len(s) - 3)

def make_era_range(vendor, prefix, suffix, values, power, voltage, tolerance, tcr, tr, qualifications, eiacase, schematic, schem_lib, footprints, fp_libs):
	table = []
	for x in values:
		pn = prefix + format_number_era(x) + suffix
		description = "RESISTOR THIN FILM " + format_resistance(x) + " OHM " + tolerance + " " + eiacase
		row = [pn, description, vendor, pn, eiacase, format_resistance(x), tolerance, tcr, tr, qualifications, voltage, schem_lib, schematic]
		for y in range(0,3):
			row = row + [fp_libs[y], footprints[y]]
		table.append(row)
	return table

wb = Workbook()

headers = ["Comment", "Description", "MFG", "MPN", "Package", "Value", "Tolerance", "Tcr", "Tr", "Qual", "Voltage", "Library Path", "Library Ref", "Footprint Path", "Footprint Ref", "Footprint Path 2", "Footprint Ref 2", "Footprint Path 3", "Footprint Ref 3"]

erj_table = [headers]
era_table = [headers]

# --------------------------------------------
# PRECISION RESISTOR FAMILY (ERJ)
# Datasheet: reference/panasonic_erj.pdf
# --------------------------------------------


# ERJ-XGNF (01005)
# NOTE: there are multiple suffix options for packaging (Y and U) but it appears only Y is commonly used
erj_table += make_res_range("PANASONIC", "ERJ-XGNF", "Y", e24_e96_combined_10_97R6, "1/32W", "15V",
	     "1%", "+/-300", "-55:125", "", "01005", "RES", r".\house.SchLib",
	     ["RESC0402X13N","RESC0402X13L","RESC0402X13M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# NOTE: there are multiple suffix options for packaging (Y and U) but it appears only Y is commonly used
erj_table += make_res_range("PANASONIC", "ERJ-XGNF", "Y", e24_e96_combined_100_1M, "1/32W", "15V",
	     "1%", "+/-200", "-55:125", "", "01005", "RES", r".\house.SchLib",
	     ["RESC0402X13N","RESC0402X13L","RESC0402X13M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-1GNF (0201)
erj_table += make_res_range("PANASONIC", "ERJ-1GNF", "C", e24_e96_combined_10_1M, "1/20W", "25V",
	     "1%", "+/-200", "-55:125", "", "0201", "RES", r".\house.SchLib",
	     ["RESC0603X23N","RESC0603X23L","RESC0603X23M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-1GJF (0201) AUTOMOTIVE
erj_table += make_res_range("PANASONIC", "ERJ-1GJF", "C", e24_e96_combined_10_1M, "1/20W", "25V",
	     "1%", "+/-200", "-55:155", "AEC-Q200 GRADE 1", "0201", "RES", r".\house.SchLib",
	     ["RESC0603X23N","RESC0603X23L","RESC0603X23M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-2RC (0402)
# NOTE: DOESN'T APPEAR TO BE IN STOCK ANYWHERE
# table += make_res_range(df, "PANASONIC", "ERJ-2RCF", "X", e24_e96_combined_1_9R76, "1/10W", "50V",
# 	     "1%", "-100/+600", "-55:155", "AEC-Q200 GRADE 0", "0402", "RES", r".\house.SchLib",
# 	     ["RESC1005X35N","RESC1005X35L","RESC1005X35M"],
# 	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])


# ERJ-2RKF (0402)
erj_table += make_res_range("PANASONIC", "ERJ-2RKF", "X", e24_e96_combined_10_1M, "1/10W", "50V",
	     "1%", "+/-100", "-55:155", "AEC-Q200 GRADE 0", "0402", "RES", r".\house.SchLib",
	     ["RESC1005X35N","RESC1005X35L","RESC1005X35M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-3EKF (0603)
erj_table += make_res_range("PANASONIC", "ERJ-3EKF", "V", e24_e96_combined_10_1M, "1/10W", "75V",
	     "1%", "+/-100", "-55:155", "AEC-Q200 GRADE 0", "0603", "RES", r".\house.SchLib",
	     ["RESC1608X45N","RESC1608X45L","RESC1608X45M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-6ENF (0805)
erj_table += make_res_range("PANASONIC", "ERJ-6ENF", "V", e24_e96_combined_10_2M2, "1/8W", "150V",
	     "1%", "+/-100", "-55:155", "AEC-Q200 GRADE 0", "0805", "RES", r".\house.SchLib",
	     ["RESC2012X60N","RESC2012X60L","RESC2012X60M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# --------------------------------------------
# STANDARD RESISTOR FAMILY (ERJ jumpers / 0 ohm)
# Datasheet: reference/panasonic_erj.pdf
# --------------------------------------------

# ERJ-XGNJ (01005)
# NOTE: NOT GOING TO ADD 5% RESISTORS TO LIBRARY. USE 1% RESISTORS INSTEAD.
# NOTE: there are multiple suffix options for packaging (Y and U) but it appears only Y is commonly used
erj_table += make_res_jumper("PANASONIC", "ERJ-XGN0R00Y", "0.5A", "01005", "RES", r".\house.SchLib",
	     ["RESC0402X13N","RESC0402X13L","RESC0402X13M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-1GNJ (0201)
# NOTE: NOT GOING TO ADD 5% RESISTORS TO LIBRARY. USE 1% RESISTORS INSTEAD.

erj_table += make_res_jumper("PANASONIC", "ERJ-1GN0R00C", "0.5A", "0201", "RES", r".\house.SchLib",
	     ["RESC0603X23N","RESC0603X23L","RESC0603X23M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-2GEJ (0402)
# NOTE: NOT GOING TO ADD 5% RESISTORS TO LIBRARY. USE 1% RESISTORS INSTEAD.

erj_table += make_res_jumper("PANASONIC", "ERJ-2GE0R00X", "0.5A", "0402", "RES", r".\house.SchLib",
	     ["RESC1005X35N","RESC1005X35L","RESC1005X35M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-3GEYJ (0603)
# NOTE: NOT GOING TO ADD 5% RESISTORS TO LIBRARY. USE 1% RESISTORS INSTEAD.

erj_table += make_res_jumper("PANASONIC", "ERJ-3GEY0R00V", "0.5A", "0603", "RES", r".\house.SchLib",
	     ["RESC1608X45N","RESC1608X45L","RESC1608X45M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERJ-6GEYJ (0603)
# NOTE: NOT GOING TO ADD 5% RESISTORS TO LIBRARY. USE 1% RESISTORS INSTEAD.

erj_table += make_res_jumper("PANASONIC", "ERJ-6GEY0R00V", "0.5A", "0805", "RES", r".\house.SchLib",
	     ["RESC2012X60N","RESC2012X60L","RESC2012X60M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])



# --------------------------------------------
# THIN FILM RESISTOR FAMILY (ERA-A) - 0201 ONLY
# Datasheet: reference/panasonic_era-a.pdf
# ±0.1% tolerance, ±25 ppm/K TCR
# ERA-2AEB/3AEB/6AEB/8AEB are intentionally omitted: they are superseded
# by the newer ERA-V/K line (higher power, anti-ESD, anti-sulfur).
# ERA-1AEB is the only 0201 thin-film precision part in Panasonic's lineup.
# --------------------------------------------

# ERA-1AEB (0201)
era_table += make_era_range("PANASONIC", "ERA-1AEB", "C", era_100_10k, "1/20W", "25V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 1", "0201", "RES", r".\house.SchLib",
	     ["RESC0603X23N","RESC0603X23L","RESC0603X23M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])


# --------------------------------------------
# THIN FILM HIGH STABILITY RESISTOR FAMILY (ERA-V/K) - 0402 / 0603 / 0805 only
# Datasheet: reference/panasonic_era-v.pdf (covers both V and K suffixes)
# ±0.1% tolerance, ±25 ppm/K TCR, anti-ESD, anti-sulfur
# 1206 is intentionally omitted: at that size we only carry the 500V ERA-P
# (see below), since the incremental cost over ERA-V/K is not worth losing
# the voltage headroom.
# --------------------------------------------

erav_table = [headers]

# ERA-2VEB (0402)
erav_table += make_era_range("PANASONIC", "ERA-2VEB", "X", era_47_100K, "1/10W", "75V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0402", "RES", r".\house.SchLib",
	     ["RESC1005X35N","RESC1005X35L","RESC1005X35M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERA-3VEB (0603)
erav_table += make_era_range("PANASONIC", "ERA-3VEB", "V", era_47_100K, "1/8W", "100V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0603", "RES", r".\house.SchLib",
	     ["RESC1608X45N","RESC1608X45L","RESC1608X45M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERA-3KEB (0603) - high resistance extension
erav_table += make_era_range("PANASONIC", "ERA-3KEB", "V", era_102K_330K, "1/8W", "100V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0603", "RES", r".\house.SchLib",
	     ["RESC1608X45N","RESC1608X45L","RESC1608X45M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERA-6VEB (0805)
erav_table += make_era_range("PANASONIC", "ERA-6VEB", "V", era_47_100K, "1/4W", "150V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0805", "RES", r".\house.SchLib",
	     ["RESC2012X55N","RESC2012X55L","RESC2012X55M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# ERA-6KEB (0805) - high resistance extension
erav_table += make_era_range("PANASONIC", "ERA-6KEB", "V", era_102K_820K, "1/4W", "150V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "0805", "RES", r".\house.SchLib",
	     ["RESC2012X55N","RESC2012X55L","RESC2012X55M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])

# NOTE: ERA-8VEB / ERA-8KEB (1206) are intentionally omitted. At 1206, the
# incremental cost over the 500V ERA-8PEB (below) is not worth the reduced
# voltage headroom, so we only carry ERA-P in 1206.


# --------------------------------------------
# THIN FILM HIGH VOLTAGE RESISTOR FAMILY (ERA-P)
# Datasheet: reference/panasonic_era-p.pdf
# 1206 only, 500V limiting, ±0.1% tolerance, ±25 ppm/K TCR
# Anti-ESD (4kV HBM Class 3), anti-sulfur
# --------------------------------------------

erap_table = [headers]

# ERA-8PEB (1206)
erap_table += make_era_range("PANASONIC", "ERA-8PEB", "V", era_160K_1M, "1/4W", "500V",
	     "0.1%", "+/-25", "-55:155", "AEC-Q200 GRADE 0", "1206", "RES", r".\house.SchLib",
	     ["RESC3216X55N","RESC3216X55L","RESC3216X55M"],
	     [r".\house.PcbLib", r".\house.PcbLib", r".\house.PcbLib"])


def write_sheet(workbook, name, table):
	sheet = workbook.add_sheet(name)
	for x, line in enumerate(table):
		for y, data in enumerate(line):
			sheet.write(x, y, data)

write_sheet(wb, 'ERJ', erj_table)
write_sheet(wb, 'ERA-A', era_table)
write_sheet(wb, 'ERA-V', erav_table)
write_sheet(wb, 'ERA-P', erap_table)

os.makedirs(BUILD_DIR, exist_ok=True)
wb.save(os.path.join(BUILD_DIR, "panasonic-resistors.xls"))


# --- Per-vendor footprint JSON output ------------------------------------
# Emits build/footprints/panasonic-resistors-footprints.json containing
# one entry per (RESC root, density) pair. The downstream pipeline reads
# this JSON in two places:
#
#   1. house/build_house_footprints.py merges every vendor's footprints
#      JSON into a single house-footprints.json (priority resolution per
#      settings.toml).
#   2. The .PcbLib autogenerator under house/HouseLibGenerator/ and the
#      STEP 3D model generator under house/stepgen/ both read the merged
#      JSON to produce build/house.PcbLib.
#
# L / W / H / T are emitted as nominal-only values (no tolerance band) --
# this matches the repo's "0%-tolerance" pad-math policy (see
# README's "Philosophy" section). The DrawingNote field is the part
# family the dimensions came from so a downstream reviewer can trace
# the geometry back to a datasheet.

VENDOR_KEY = "panasonic-resistors"


def _build_footprint_rows(footprints, kind):
	"""Expand each (root, L, W, H, T, ...) entry into 3 dict rows, one
	per IPC-7351B density variant (L / N / M)."""
	out = []
	for root, L, W, H, T, _eia, source in footprints:
		for density in ("L", "N", "M"):
			out.append({
				"name":        root + density,
				"kind":        kind,
				"density":     density,
				"drawingNote": f"Dimensions from {source}",
				"bodyMm": {
					"lengthNominal":         L,
					"widthNominal":          W,
					"heightNominal":         H,
					"terminalLengthNominal": T,
				},
			})
	return out


_vendor_common.write_footprints_json(
	os.path.join(FOOTPRINTS_DIR, VENDOR_KEY + "-footprints.json"),
	vendor=VENDOR_KEY,
	footprints=_build_footprint_rows(RESC_FOOTPRINTS, kind="R"),
)

