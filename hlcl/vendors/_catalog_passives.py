"""Strict catalog import for MLCC families whose geometry is not encoded in MPNs.

Each row is an explicitly verified ordering code, not a Cartesian expansion of
capacitance, voltage, thickness and packaging codes. See passive-importers.md.
"""
from decimal import Decimal
import math
import re

from _passives import Part, body, capacitance, code_value, number

VOLTAGES = {'1C': 16, '1E': 25, '1H': 50, '1J': 63, '2A': 100, '2D': 200, 'YA': 35}
KEMET_VOLTAGES = {'4': 16, '3': 25, '5': 50, '1': 100, '2': 200}
TOLERANCES = {'F': '1%', 'G': '2%', 'J': '5%', 'K': '10%', 'M': '20%'}


def decode(row, family):
    mpn = row['mpn']
    if family.startswith('kemet-'):
        m = re.fullmatch(r'C(\d{4})([CF])(\d{3}|\dR\d)([FGJKM])([13452])([RG])([AE])C(AUTO\d*|TU|\d{4})', mpn)
        if not m:
            raise ValueError(f'invalid KEMET ordering code: {mpn}')
        size, series, cap, tol, volt, dielectric, design, pack = m.groups()
        expected = {'kemet-x7r': ('C', 'R', 'A', False),
                    'kemet-open-mode': ('F', 'R', 'A', True),
                    'kemet-esd-c0g': ('C', 'G', 'E', True)}[family]
        if (series, dielectric, design, pack.startswith('AUTO')) != expected:
            raise ValueError(f'{mpn} does not belong to {family}')
        voltage = KEMET_VOLTAGES[volt]
        if row['dielectric'] != {'R': 'X7R', 'G': 'C0G'}[dielectric]:
            raise ValueError(f'{mpn}: dielectric disagrees with ordering code')
        if size != row['package']:
            raise ValueError(f'{mpn}: package disagrees with ordering code')
    elif family == 'tdk-c':
        m = re.fullmatch(r'C(1005|1608|2012|3216|3225)(X7R)(1H|2A)(\d{3})([JKM])(\d{3})(AB|BB)', mpn)
        if not m:
            raise ValueError(f'unsupported TDK C ordering code: {mpn}')
        metric, dielectric, volt, cap, tol, thickness, pack = m.groups()
        voltage = VOLTAGES[volt]
        if row['dielectric'] != dielectric:
            raise ValueError(f'{mpn}: dielectric disagrees with ordering code')
        if metric != row['metric'] or Decimal(thickness)/100 != Decimal(row['height_nominal_mm']):
            raise ValueError(f'{mpn}: dimensions disagree with ordering code')
    elif family in ('murata-gcd', 'murata-krm'):
        pattern = r'GCD(188|21B)(R7|C7)(1C|1E|1H|2A)(\d{3})([KM])(A01|E01)([DL])' if family == 'murata-gcd' else r'KRM(55Q)(R7)(2A)(\d{3})([K])(H01)([LK])'
        m = re.fullmatch(pattern, mpn)
        if not m:
            raise ValueError(f'unsupported Murata ordering code: {mpn}')
        size, tc, volt, cap, tol, control, pack = m.groups()
        if row['dielectric'] != {'R7': 'X7R', 'C7': 'X7S'}[tc]:
            raise ValueError(f'{mpn}: dielectric disagrees with ordering code')
        voltage = VOLTAGES[volt]
        if family == 'murata-gcd' and (size, pack) not in {('188', 'D'), ('21B', 'L')}:
            raise ValueError(f'{mpn}: packaging does not match verified case')
    else:
        raise ValueError(f'unknown capacitor family: {family}')
    pf = code_value(cap)
    if pf != Decimal(row['capacitance_pf']) or voltage != Decimal(row['voltage_v']) or TOLERANCES[tol] != row['tolerance']:
        raise ValueError(f'{mpn}: electrical data disagrees with ordering code')
    dims = [float(row[k]) for k in ('length_mm', 'width_mm', 'height_max_mm', 'terminal_mm')]
    if not all(math.isfinite(d) for d in dims) or min(dims) <= 0 or 2*dims[3] >= dims[0] or not 0 < float(row['height_nominal_mm']) <= dims[2]:
        raise ValueError(f'{mpn}: invalid dimensions')
    extra = {}
    if row.get('pad_length_mm'):
        extra['landPatternMm'] = dict(zip(('padLength', 'padWidth', 'gap'),
            [float(row[k]) for k in ('pad_length_mm', 'pad_width_mm', 'pad_gap_mm')]))
    if family == 'murata-krm':
        extra['model'] = {'type': 'metal-terminal'}
    geom = body('CAPC', row['metric'], dims[2], row['geometry_id'],
                dims[0], dims[1], dims[3], row['geometry_source'], **extra)
    return Part(mpn, row['manufacturer'], row['package'], 'C', capacitance(pf),
                row['tolerance'], {'C0G': '+/-30', 'X7R': '+/-15%', 'X7S': '+/-22%'}[row['dielectric']],
                '-55:125', row['qualification'], number(voltage)+'V', '',
                row['features'], row['conditions'], row['datasheet'], geom)
