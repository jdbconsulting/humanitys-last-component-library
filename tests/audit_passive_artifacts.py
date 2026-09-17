"""Audit a full build; optionally validate STEP topology with Open Cascade.

python tests/audit_passive_artifacts.py [--with-ocp]
"""
import argparse
import json
import math
from pathlib import Path
import re
import zlib

import olefile
import xlrd

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'hlcl/build'
REQUIRED = {
    'murata-gcd': ['GCD21BR72A104KA01L','GCD188R72A472KA01D'],
    'murata-krm': ['KRM55QR72A106KH01L'],
    'kemet-x7r': ['C0402C103K1RAC7411','C0805C394J5RACTU'],
    'kemet-open-mode': ['C0603F223K1RACAUTO','C1210F155K1RACAUTO'],
    'kemet-esd-c0g': ['C0805C473F3GECAUTO7210'],
    'tdk-c': ['C1005X7R1H473K050BB','C3225X7R2A225K230AB'],
    'samsung-capacitors': ['CL31B474KCHWPNE','CL10B223KC8WPNC'],
    'panasonic-era-a': ['ERA-2ARB6811X','ERA-2ARB562X'],
    'vishay-rcs': ['RCS120633K0FKEA','RCS08051R50FKEA','RCS04020000Z0ED','RCS080510K0FKEA'],
    'vishay-rcp': ['RCP0603W10R0GEB','RCP2512W15R0FEA'],
    'vishay-mc-precision': ['MCS04020D2491BE000'],
    'vishay-mc-at': ['MCS0402MD1004BE000','MCS0402MD2673BE000','MCS0402MD3093BE000','MCA1206MD2492BP500'],
    'yageo-ac': ['AC1210FR-0760R4L'],
    'murata-gcm': ['GCM1555C1H5R1BA16D'],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--with-ocp', action='store_true')
    args = ap.parse_args()
    fps = json.loads((BUILD/'intermediate/footprints/house-footprints.json').read_text())['footprints']
    names = {fp['name'] for fp in fps}
    rows_checked = 0
    books = {p.stem:p for p in (BUILD/'output').glob('*.xls')}
    assert set(REQUIRED) <= books.keys(), 'missing required workbook'
    for family,path in books.items():
        found = set()
        for sheet in xlrd.open_workbook(path).sheets():
            headings = sheet.row_values(0)
            mpn_cols = [i for i,h in enumerate(headings) if h == 'MPN' or h.startswith('MPN ')]
            fp_cols = [i for i,h in enumerate(headings) if h.startswith('Footprint Ref')]
            seen = set()
            for n in range(1,sheet.nrows):
                row = sheet.row_values(n)
                primary = row[headings.index('MPN')]
                # Unchanged inductor catalogs can contain multiple variants of
                # a base MPN. Enforce uniqueness for this change's families.
                if family in REQUIRED and family != 'murata-gcm':
                    assert primary not in seen, (family,'duplicate MPN',primary)
                seen.add(primary)
                found.update(row[i] for i in mpn_cols if row[i])
                for i in fp_cols:
                    assert not row[i] or row[i] in names, (family,primary,'unresolved footprint',row[i])
                rows_checked += 1
        assert set(REQUIRED.get(family,[])) <= found, (family,'missing',set(REQUIRED.get(family,[]))-found)

    roots = {fp['name'][:-1]:fp for fp in fps}
    if args.with_ocp:
        from OCP.STEPControl import STEPControl_Reader
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib
        from OCP.IFSelect import IFSelect_RetDone
    step_texts = set()
    for root,fp in roots.items():
        path = BUILD/'intermediate/step'/f'{root}.step'
        data = path.read_bytes();step_texts.add(data)
        text = data.decode('ascii')
        assert 'SI_UNIT(.MILLI.,.METRE.)' in text, (root,'wrong STEP units')
        body = fp['bodyMm']
        L,W,H = (body[k] for k in ('lengthNominal','widthNominal','heightNominal'))
        points = [tuple(float(v) for v in match.split(','))
                  for match in re.findall(r"CARTESIAN_POINT\('[^']*',\(([^)]+)\)\)",text)]
        assert points, (root,'no points')
        for x,y,z in points:
            assert all(math.isfinite(v) for v in (x,y,z)), root
            assert abs(x)<=L/2+1e-6 and abs(y)<=W/2+1e-6 and -1e-6<=z<=H+1e-6, (root,(x,y,z),(L,W,H))
        if args.with_ocp:
            reader = STEPControl_Reader()
            assert reader.ReadFile(str(path)) == IFSelect_RetDone, root
            assert reader.TransferRoots() > 0, root
            shape = reader.OneShape()
            assert BRepCheck_Analyzer(shape).IsValid(), (root,'invalid STEP topology')
            box = Bnd_Box();BRepBndLib.AddOptimal_s(shape,box)
            lo,hi = box.CornerMin(),box.CornerMax()
            expected = (-L/2,-W/2,0,L/2,W/2,H)
            actual = (lo.X(),lo.Y(),lo.Z(),hi.X(),hi.Y(),hi.Z())
            assert all(abs(a-b)<1e-5 for a,b in zip(actual,expected)), (root,actual,expected)
    with olefile.OleFileIO(str(BUILD/'output/house.PcbLib')) as lib:
        model_paths = [p for p in lib.listdir() if len(p)==3 and p[:2]==['Library','Models'] and p[2].isdigit()]
        assert model_paths, 'no embedded STEP models'
        embedded = {zlib.decompress(lib.openstream(p).read()) for p in model_paths}
        assert embedded == step_texts, 'embedded models differ from generated STEP files'
    print(f'PASS: {rows_checked:,} workbook rows; requested coverage; {len(names)} footprint references; '
          f'{len(roots)} bounded STEP models and their embedded PcbLib copies'
          + ('; Open Cascade topology and extents' if args.with_ocp else ''))


if __name__ == '__main__':
    main()
