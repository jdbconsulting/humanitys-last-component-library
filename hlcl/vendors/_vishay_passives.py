"""Ordering-code decoders for the reviewed CRCW, TNPW, RCS, RCP and MC subfamilies.

The curated input lists can grow independently of the decoders; unsupported
suffixes, ranges and case/packing combinations fail the build.
"""
from decimal import Decimal, ROUND_FLOOR
import re
from _passives import Part, body, code_value, number, resistance

CRCW = 'https://www.vishay.com/docs/20035/dcrcwe3.pdf'
CRCW0201 = 'https://www.vishay.com/docs/20052/crcw0201e3.pdf'
RCS = 'https://www.vishay.com/docs/20065/rcse3.pdf'
RCP = 'https://www.vishay.com/docs/31098/rcp.pdf'
MC = 'https://www.vishay.com/docs/28700/mcx0x0xpre.pdf'
MCAT = 'https://www.vishay.com/docs/28952/mcr0201at-mca1206at.pdf'
TNPW = 'https://www.vishay.com/docs/28758/tnpw_e3.pdf'
TNPW_SNPB = 'https://www.vishay.com/docs/31006/tnpw.pdf'
E24 = (10,11,12,13,15,16,18,20,22,24,27,30,33,36,39,43,47,51,56,62,68,75,82,91)
E192 = (100,101,102,104,105,106,107,109,110,111,113,114,115,117,118,120,121,123,124,126,127,129,130,132,
        133,135,137,138,140,142,143,145,147,149,150,152,154,156,158,160,162,164,165,167,169,172,174,176,178,
        180,182,184,187,189,191,193,196,198,200,203,205,208,210,213,215,218,221,223,226,229,232,234,237,240,
        243,246,249,252,255,258,261,264,267,271,274,277,280,284,287,291,294,298,301,305,309,312,316,320,324,
        328,332,336,340,344,348,352,357,361,365,370,374,379,383,388,392,397,402,407,412,417,422,427,432,437,
        442,448,453,459,464,470,475,481,487,493,499,505,511,517,523,530,536,542,549,556,562,569,576,583,590,
        597,604,612,619,626,634,642,649,657,665,673,681,690,698,706,715,723,732,741,750,759,768,777,787,796,
        806,816,825,835,845,856,866,876,887,898,909,920,931,942,953,965,976,988)
E96 = E192[::2]


def in_series(value, series):
    """True if ``value`` (ohms) has a mantissa from ``series`` ('E24', 'E96' or 'E192')."""
    digits = value.scaleb(2 - value.adjusted())  # three significant digits, 100..999
    return digits in {x * 10 for x in E24} if series == 'E24' else digits in (E96 if series == 'E96' else E192)


def _tnpw_grid(f_lo, hi, b_lo, xy_lo, b_hi=None):
    """(TCR, tolerance) -> (min, max) ohms for one TNPW e3 size (doc 28758 p.3-4):
    H/E (50/25 ppm) at F/D/B (1/0.5/0.1%), X/Y (15/10 ppm) at B only."""
    b_hi = b_hi or hi
    grid = {(t, 'B'): (xy_lo, b_hi) for t in 'XY'}
    for t in 'HE':
        grid.update({(t, 'F'): (f_lo, hi), (t, 'D'): (f_lo, hi), (t, 'B'): (b_lo, b_hi)})
    return grid


def _tnpw_snpb_grid(hi, b_hi=None):
    """Narrower SnPb grid (doc 31006 p.2): H at F, E at D/B, X/Y at B."""
    b_hi = b_hi or hi
    return {('H', 'F'): (10, hi), ('E', 'D'): (10, hi), ('E', 'B'): (47, b_hi),
            ('X', 'B'): (47, b_hi), ('Y', 'B'): (47, b_hi)}


_k, _M, _3R5 = 1000, 1000000, Decimal('3.5')
TNPW_RANGES = {
    'e3': {
        '0201': {('E', 'D'): (22, 40*_k), ('E', 'B'): (22, 25*_k)},
        '0402': _tnpw_grid(10, 100*_k, 47, 47),
        '0603': _tnpw_grid(1, 332*_k, _3R5, 47),
        '0805': _tnpw_grid(1, _M, _3R5, _3R5),
        '1206': _tnpw_grid(1, 2*_M, _3R5, 47),
        '1210': _tnpw_grid(10, Decimal('3.01')*_M, 47, 47, Decimal('2.13')*_M),
    },
    'snpb': {
        '0402': _tnpw_snpb_grid(100*_k), '0603': _tnpw_snpb_grid(332*_k),
        '0805': _tnpw_snpb_grid(_M), '1206': _tnpw_snpb_grid(2*_M),
        '1210': _tnpw_snpb_grid(Decimal('3.01')*_M, Decimal('2.13')*_M),
    },
}


def decode(row, family):
    mpn = row['mpn']
    extra, construction, alternates = {}, '', ()
    if family == 'vishay-crcw':
        m = re.fullmatch(r'CRCW(0201|0402|0603|0805|1206|1210|1218|2010|2512)([0-9RKM]{4})([FJ][KNX]|Z0)(E[A-K])', mpn)
        if not m:
            raise ValueError(f'invalid CRCW code: {mpn}')
        size, code, grade, packing = m.groups()
        # Bottom terminal T1 drives the lands; top terminal T2 is model-only.
        # 0402-0805 use standard-mode P70/Umax, not the extended-mode ratings.
        # 0201 is a separate commercial datasheet without AEC-Q200.
        metric,L,W,H,T,top,power,voltage,upper,imax,packs = {
            '0201': ('0603',.6,.3,.26,.15,.1,.05,30,10000000,'1A',('ED','EE','EI')),
            '0402': ('1005',1,.5,.40,.25,.2,.063,50,10000000,'1.5A',('ED','EE')),
            '0603': ('1608',1.55,.85,.50,.3,.3,.1,75,10000000,'2A',('EA','EC','ED','EE','EI')),
            '0805': ('2012',2,1.25,.60,.3,.3,.125,150,10000000,'2.5A',('EA','EC')),
            '1206': ('3216',3.2,1.6,.60,.45,.4,.25,200,10000000,'3.5A',('EA','EC')),
            '1210': ('3225',3.2,2.5,.60,.45,.4,.5,200,10000000,'5A',('EA','EC')),
            '1218': ('3246',3.2,4.6,.60,.45,.4,1,200,2200000,'7A',('EK',)),
            '2010': ('5025',5,2.5,.70,.6,.6,.75,400,10000000,'6A',('EF',)),
            '2512': ('6332',6.3,3.15,.70,.6,.6,1,500,10000000,'7A',('EG','EH')),
        }[size]
        ranges = ({'FK': (47, 1000000), 'FN': (10, upper), 'FX': (1, Decimal('9.76')),
                   'JN': (10, upper), 'JX': (1, Decimal('9.1'))} if size == '0201' else
                  {'FK': (1, upper), 'FN': (1, Decimal('9.76')), 'JN': (1, upper)})
        if code != '0000' and (code[0] == '0' or sum(c in 'RKM' for c in code) != 1):
            raise ValueError(f'{mpn}: CRCW requires one embedded resistance unit and no leading zero')
        value = code_value(code)
        lower, upper = ranges.get(grade, (0, 0))
        if packing not in packs or (grade == 'Z0') != (code == '0000') or (value and not lower <= value <= upper):
            raise ValueError(f'invalid CRCW range/packing: {mpn}')
        if grade[0] == 'J' and value.scaleb(1 - value.adjusted()) not in E24:
            raise ValueError(f'{mpn}: CRCW 5% values are E24 only')
        tol = {'F': '1%', 'J': '5%', 'Z': ''}[grade[0]]
        tcr = {'K': '+/-100', 'N': '+/-200', 'X': '-200/+400', '0': ''}[grade[1]]
        source = CRCW0201 if size == '0201' else CRCW
        qual,temp,features = '' if size == '0201' else 'AEC-Q200','-55:155','thick film'
        mode = ('P70 standard operation mode; extended mode not advertised'
                if size in ('0402','0603','0805') else 'P70 ambient rating')
        conditions = mode + '; derate above 70 C; working voltage <= min(Umax, sqrt(P*R))'
        if size != '0201':
            conditions += '; see pulse curves'
        if not value:
            power, voltage = '', ''
            features += f"; jumper <={50 if size == '0201' else 20}mOhm; Imax=" + imax
            conditions = 'Jumper current must meet datasheet thermal conditions'
        qualifier, construction = 'CRCW', 'THICK FILM'
        # Same part on the size's other datasheet reels.
        alternates = tuple(mpn[:-2] + other for other in packs if other != packing)
        extra['model'] = {'type': 'wide-bottom', 'topTerminalLengthMm': top}
    elif family == 'vishay-tnpw':
        m = re.fullmatch(r'TNPW(0201|0402|0603|0805|1206|1210)([0-9RKM]{4})([BDF])([HEXY])(E[ACD]|T[ADP]|CN)', mpn)
        if not m:
            raise ValueError(f'invalid TNPW code: {mpn}')
        size, code, tol_code, tcr_code, packing = m.groups()
        finish = 'snpb' if packing in ('TA', 'TD', 'TP', 'CN') else 'e3'
        if code[0] == '0' or sum(c in 'RKM' for c in code) != 1:
            raise ValueError(f'{mpn}: TNPW requires one embedded resistance unit and no leading zero')
        value = code_value(code)
        lower, upper = TNPW_RANGES[finish].get(size, {}).get((tcr_code, tol_code), (0, -1))
        if not lower <= value <= upper:
            raise ValueError(f'invalid TNPW size/grade/range: {mpn}')
        if not in_series(value, 'E24') and not in_series(value, 'E96' if tol_code == 'F' else 'E192'):
            raise ValueError(f'{mpn}: TNPW 1% values are E24/E96 and tighter ones E24/E192')
        # Reels per size (28758 p.4; 31006 p.2). EC (20,000) exists only for
        # 25/50 ppm; SnPb TP/CN (1,000) only for 0.1%.
        if finish == 'e3':
            packs = ('ED',) if size in ('0201', '0402') else ('EA',) + (('EC',) if tcr_code in 'HE' else ())
        else:
            packs = (('TD',) if size == '0402' else ('TA',)) + (((('TP',) if size == '0402' else ('CN',))) if tol_code == 'B' else ())
        if packing not in packs:
            raise ValueError(f'invalid TNPW reel for {size} {tol_code}{tcr_code}: {mpn}')
        # Nominal L/W, maximum H, terminal (top = bottom) from both dimension tables.
        metric,L,W,H,T = {'0201': ('0603',.6,.3,.26,.12), '0402': ('1005',1,.5,.40,.2),
                          '0603': ('1608',1.55,.85,.55,.3), '0805': ('2012',2,1.25,.55,.4),
                          '1206': ('3216',3.2,1.6,.65,.5), '1210': ('3225',3.2,2.45,.75,.5)}[size]
        if finish == 'e3':
            # General operation mode: lowest drift; power/advanced modes trade
            # drift for dissipation and are not advertised here.
            power, voltage = {'0201': (.05,25), '0402': (.07,75), '0603': (.11,100),
                              '0805': (.14,150), '1206': (.27,200), '1210': (.33,200)}[size]
            source, features = TNPW, 'thin film; sulfur resistant'
            conditions = ('P70 general operation mode, film <=125 C; power/advanced modes allow more '
                          'dissipation with more drift; working voltage <= min(Umax, sqrt(P*R))')
        else:
            power, voltage = {'0402': (.063,50), '0603': (.1,75), '0805': (.125,150),
                              '1206': (.25,200), '1210': (.33,200)}[size]
            source, features = TNPW_SNPB, 'thin film; SnPb termination (lead-bearing)'
            conditions = 'P70 ambient rating, film <=155 C; working voltage <= min(Umax, sqrt(P*R))'
        tol = {'B': '0.1%', 'D': '0.5%', 'F': '1%'}[tol_code]
        tcr = {'H': '+/-50', 'E': '+/-25', 'X': '+/-15', 'Y': '+/-10'}[tcr_code]
        qual, temp = 'AEC-Q200', '-55:125'
        qualifier, construction = 'TNPW', 'THIN FILM'
        alternates = tuple(mpn[:-2] + other for other in packs if other != packing)
        # One geometry note for both finishes: their dimension tables agree.
        geom = body('RESC', metric, H, qualifier, L, W, T,
                    f'{TNPW} and {TNPW_SNPB}; maximum height; nominal L/W and terminals')
        return Part(mpn, 'Vishay', size, 'R', resistance(value), tol, tcr, temp, qual,
                    number(voltage)+'V', number(power)+'W', features, conditions, source, geom,
                    construction, alternates)
    elif family == 'vishay-rcs':
        m = re.fullmatch(r'RCS(0402|0603|0805|1206)([0-9RKM]{4})(FK|DK|JN|Z0)(E[A-C]|E[D-I])', mpn)
        if not m:
            raise ValueError(f'invalid RCS code: {mpn}')
        size, code, grade, packing = m.groups()
        # Bottom terminal T1 drives the lands; top terminal T2 is model-only.
        metric,L,W,H,T,power,voltage,packs = {
            '0402': ('1005',1,.5,.40,.25,.2,50,('ED','EE')),
            '0603': ('1608',1.55,.85,.50,.3,.25,75,('EA','EC','EI','ED','EE')),
            '0805': ('2012',2,1.25,.60,.3,.5,150,('EA','EC')),
            '1206': ('3216',3.2,1.6,.65,.45,.5,200,('EA',)),
        }[size]
        value = code_value(code)
        if value and not any(c in code for c in 'RKM'):
            raise ValueError(f'{mpn}: RCS requires an embedded resistance unit')
        if packing not in packs or (grade == 'Z0') != (code == '0000') or (value and not 1 <= value <= 10000000):
            raise ValueError(f'invalid RCS range/packing: {mpn}')
        tol,tcr = {'FK':('1%','+/-100'), 'DK':('0.5%','+/-100'),
                   'JN':('5%','+/-200'), 'Z0':('','')}[grade]
        source,qual,temp,features = RCS,'AEC-Q200','-55:155','thick film; anti-surge'
        conditions = 'P70 ambient rating; derate above 70 C; working voltage <= min(Umax, sqrt(P*R)); see pulse curves'
        if not value:
            power, voltage = '', ''
            features += '; jumper <=20mOhm; Imax=' + {'0402':'3A','0603':'3.5A','0805':'4A','1206':'5A'}[size]
            conditions = 'Jumper current must meet datasheet thermal conditions'
        qualifier, construction = 'RCS', 'THICK FILM'
        extra['model'] = {'type': 'wide-bottom', 'topTerminalLengthMm':
                          {'0402': .2, '0603': .3, '0805': .3, '1206': .4}[size]}
    elif family == 'vishay-rcp':
        m = re.fullmatch(r'RCP(0603|1206|2512)(W|B)([0-9RK]{4})([FGJ])(EA|EB|EC|ED|ET)', mpn)
        if not m:
            raise ValueError(f'unsupported RCP code: {mpn}')
        size, terminal, code, grade, packing = m.groups()
        metric,L,W,H,top,wide,power,padw,widepad,widegap,normalpad,normalgap = {
            '0603':('1608',1.6,.81,.59,.30,.58,1.5,.94,1.09,.46,.89,.84),
            '1206':('3115',3.1,1.52,.64,.38,1.22,2.4,1.68,1.73,.46,.94,2.06),
            '2512':('6332',6.35,3.15,.64,.51,2.87,3.5,3.28,3.38,.61,1.02,5.33),
        }[size]
        T = wide if terminal == 'W' else (.51 if size == '2512' else .38)
        value = code_value(code)
        if not 10 <= value <= 2000:
            raise ValueError(f'RCP resistance outside 10..2000 ohm: {mpn}')
        tol,tcr = {'F':'1%','G':'2%','J':'5%'}[grade], '+/-150'
        voltage = number((Decimal(str(power))*value).sqrt().quantize(Decimal('.01'), rounding=ROUND_FLOOR))
        source,qual,temp,features = RCP,'','-65:155','thick film; AlN substrate; '+terminal+' terminals'
        conditions = 'P25 on standard test board; thermal design required; no active-cooling power claim; Umax=sqrt(P*R)'
        extra = {'model':{'type':'wide-bottom','topTerminalLengthMm':top},
                 'landPatternMm':{'padLength':widepad if terminal=='W' else normalpad,
                                  'padWidth':padw, 'gap':widegap if terminal=='W' else normalgap}}
        qualifier, construction = 'RCP'+terminal, 'THICK FILM'
    elif family in ('vishay-mc-precision','vishay-mc-at'):
        m = re.fullmatch(r'(MCS0402|MCT0603|MCU0805|MCA1206)(0|M)D(\d{4})B(E0|P5|PW)00', mpn)
        if not m:
            raise ValueError(f'unsupported MC code (initial scope: 0.1%, 25ppm): {mpn}')
        case,version,code,packing = m.groups()
        at = family == 'vishay-mc-at'
        if (version == 'M') != at:
            raise ValueError(f'{mpn}: precision and AT versions must not be mixed')
        size = case[3:]
        metric,L,W,H,T,voltage,power,upper = {
            '0402':('1005',1,.5,.37,.2,75,.07 if at else .063,1000000 if at else 221000),
            '0603':('1608',1.55,.85,.55,.3,100,.11 if at else .1,2000000 if at else 511000),
            '0805':('2012',2,1.25,.62 if at else .55,.4,150,.14 if at else .125,7500000 if at else 1500000),
            '1206':('3216',3.2,1.6,.65,.5,200,.27 if at else .25,10000000 if at else 2000000),
        }[size]
        exponent = int(code[-1]); exponent = exponent-10 if exponent in (8,9) else exponent
        value = Decimal(code[:3])*Decimal(10)**exponent
        lower = 100 if size=='0402' and not at else 47
        packs = ('E0',) if size=='0402' else ('P5',) if size=='1206' else ('P5','PW')
        if not lower <= value <= upper or packing not in packs:
            raise ValueError(f'{mpn}: invalid MC range/packing')
        tol,tcr,qual,temp = '0.1%','+/-25','AEC-Q200' if at else 'IECQ-CECC','-55:125'
        source,features = (MCAT,'thin film; automotive') if at else (MC,'thin film; precision')
        conditions = 'P70 general operating mode, film <=125 C; higher power modes require separate drift/thermal review' if at else 'P70 precision operating mode, film <=125 C'
        qualifier, construction = ('MCAT' if at else 'MCP'), 'THIN FILM'
    else:
        raise ValueError(f'unknown Vishay family: {family}')
    geom = body('RESC',metric,H,qualifier,L,W,T,source+'; maximum height; nominal L/W and terminals',**extra)
    return Part(mpn,'Vishay',size,'R',resistance(value),tol,tcr,temp,qual,
                number(voltage)+'V' if voltage != '' else '',number(power)+'W' if power != '' else '',
                features,conditions,source,geom,construction,alternates)



def tcr_ppm(tcr):
    """Worst-case magnitude of a Tcr field: '+/-25' -> 25, '-200/+400' -> 400."""
    return max(int(x) for x in re.findall(r'\d+', tcr))


def select_grades(parts, options, tcr_codes, tolerance_codes=''):
    """Apply grade options to parts whose MPN is <model><size><4-character value>
    <tolerance letter><TCR letter><reel> (CRCW, TNPW).

    Keeps the ticked ``tcr_options`` (and ``tolerance_options`` when
    ``tolerance_codes`` is given); with ``lowest_tcr_only`` keeps only the
    tightest TCR per size, value, tolerance and reel. Parts without a TCR
    (jumpers) always pass.
    """
    def chosen(option, codes):
        picked = set(options.get_option(option, list(codes)))
        if picked - set(codes):
            raise ValueError(f'unknown {option}: {sorted(picked - set(codes))}')
        return picked
    tcrs = chosen('tcr_options', tcr_codes)
    tols = chosen('tolerance_options', tolerance_codes) if tolerance_codes else None
    kept = [p for p in parts if not p.tcr
            or (p.mpn[13] in tcrs and (tols is None or p.mpn[12] in tols))]
    if not options.get_option('lowest_tcr_only', False):
        return kept
    key = lambda p: (p.mpn[:12], p.mpn[12], p.mpn[14:])
    best = {}
    for p in kept:
        if p.tcr and (key(p) not in best or tcr_ppm(p.tcr) < tcr_ppm(best[key(p)].tcr)):
            best[key(p)] = p
    return [p for p in kept if not p.tcr or best[key(p)] is p]
