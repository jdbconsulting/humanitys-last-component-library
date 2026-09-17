"""Ordering-code decoders for the reviewed RCS, RCP and MC subfamilies.

The curated input lists can grow independently of the decoders; unsupported
suffixes, ranges and case/packing combinations fail the build.
"""
from decimal import Decimal, ROUND_FLOOR
import re
from _passives import Part, body, code_value, number, resistance

RCS = 'https://www.vishay.com/docs/20065/rcse3.pdf'
RCP = 'https://www.vishay.com/docs/31098/rcp.pdf'
MC = 'https://www.vishay.com/docs/28700/mcx0x0xpre.pdf'
MCAT = 'https://www.vishay.com/docs/28952/mcr0201at-mca1206at.pdf'


def decode(row, family):
    mpn = row['mpn']
    extra = {}
    if family == 'vishay-rcs':
        m = re.fullmatch(r'RCS(0402|0603|0805|1206)([0-9RKM]{4})(FK|DK|JN|Z0)(E[A-C]|E[D-I])', mpn)
        if not m:
            raise ValueError(f'invalid RCS code: {mpn}')
        size, code, grade, packing = m.groups()
        metric,L,W,H,T,power,voltage,packs = {
            '0402': ('1005',1,.5,.40,.2,.2,50,('ED','EE')),
            '0603': ('1608',1.55,.85,.50,.3,.25,75,('EA','EC','EI','ED','EE')),
            '0805': ('2012',2,1.25,.60,.3,.5,150,('EA','EC')),
            '1206': ('3216',3.2,1.6,.65,.4,.5,200,('EA',)),
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
        qualifier = 'RCS'
        extra['model'] = {'type': 'wide-bottom', 'topTerminalLengthMm':
                          {'0402': .25, '0603': .3, '0805': .3, '1206': .45}[size]}
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
        qualifier = 'RCP'+terminal
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
        qualifier = 'MCAT' if at else 'MCP'
    else:
        raise ValueError(f'unknown Vishay family: {family}')
    geom = body('RESC',metric,H,qualifier,L,W,T,source+'; maximum height; nominal L/W and terminals',**extra)
    return Part(mpn,'Vishay',size,'R',resistance(value),tol,tcr,temp,qual,
                number(voltage)+'V' if voltage != '' else '',number(power)+'W' if power != '' else '',
                features,conditions,source,geom)
