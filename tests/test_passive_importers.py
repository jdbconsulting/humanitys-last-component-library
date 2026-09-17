"""Datasheet examples, negative ordering codes and manufacturing geometry.

Run after npm run regen: python -m unittest discover -s tests -v.
The generated-artifact audit additionally requires python hlcl/build.py all.
"""
import copy
import csv
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'hlcl'), str(ROOT/'hlcl/vendors'), str(ROOT/'hlcl/house')]
import _common
from _catalog_passives import decode as capacitor
from _vishay_passives import decode as resistor
from build import load_module
from altium_pcblib.footprint import FootprintInput, build_chip_footprint


def catalog(family):
    vendor, subfamily = family.split('-', 1)
    with (ROOT/'hlcl/vendors'/vendor/subfamily/'parts.csv').open() as stream:
        return list(csv.DictReader(stream))


def find_part(family, mpn):
    row = next(r for r in catalog(family) if r['mpn'] == mpn)
    return (resistor if family.startswith('vishay') else capacitor)(row, family)


class PassiveCatalogTests(unittest.TestCase):
    def test_all_catalog_rows_decode_and_have_distinct_mpns(self):
        for family in ('murata-gcd', 'murata-krm', 'kemet-x7r', 'kemet-open-mode',
                       'kemet-esd-c0g', 'tdk-c', 'vishay-rcs', 'vishay-rcp',
                       'vishay-mc-precision', 'vishay-mc-at'):
            with self.subTest(family=family):
                rows = catalog(family)
                self.assertEqual(len(rows), len({r['mpn'] for r in rows}))
                for row in rows:
                    part = (resistor if family.startswith('vishay') else capacitor)(row, family)
                    with patch.object(_common, 'density_codes', return_value=('N',)):
                        fp, = _common.expand_footprint_rows([part.geometry], family)
                    _common._validate_footprint(fp)

    def test_requested_values_and_ratings(self):
        cases = [
            ('vishay-rcs','RCS08051R50FKEA','1.5','1%','0.5W'),
            ('vishay-rcs','RCS120633K0FKEA','33k','1%','0.5W'),
            ('vishay-mc-precision','MCS04020D2491BE000','2.49k','0.1%','0.063W'),
            ('vishay-mc-at','MCS0402MD1004BE000','1M','0.1%','0.07W'),
            ('vishay-mc-at','MCS0402MD2673BE000','267k','0.1%','0.07W'),
            ('vishay-mc-at','MCS0402MD3093BE000','309k','0.1%','0.07W'),
            ('vishay-rcp','RCP0603W10R0GEB','10','2%','1.5W'),
            ('vishay-rcp','RCP2512W15R0FEA','15','1%','3.5W'),
            ('kemet-x7r','C0402C103K1RAC7411','10nF','10%',''),
            ('kemet-x7r','C0805C394J5RACTU','390nF','5%',''),
            ('kemet-open-mode','C1210F155K1RACAUTO','1.5uF','10%',''),
            ('kemet-esd-c0g','C0805C473F3GECAUTO7210','47nF','1%',''),
            ('murata-gcd','GCD21BR72A104KA01L','100nF','10%',''),
            ('murata-krm','KRM55QR72A106KH01L','10uF','10%',''),
        ]
        for family, mpn, value, tolerance, power in cases:
            with self.subTest(mpn=mpn):
                p = find_part(family, mpn)
                self.assertEqual((p.value,p.tolerance,p.power),(value,tolerance,power))

    def test_bad_ordering_codes_and_inconsistent_data_fail(self):
        for family, mpn in [('vishay-rcs','RCS040210K0FKEA'),
                            ('vishay-rcs','RCS08052491FKEA'),
                            ('vishay-mc-at','MCS04020D2491BE000'),
                            ('vishay-mc-precision','MCS04020D1004BE000'),
                            ('vishay-rcp','RCP2512W1R00FEA')]:
            with self.subTest(mpn=mpn), self.assertRaises(ValueError):
                resistor({'mpn':mpn},family)
        row = catalog('kemet-open-mode')[0]
        for key, wrong in [('voltage_v','50'),('dielectric','C0G'),('height_max_mm','nan'),
                           ('mpn','C0603C223K1RACAUTO')]:
            bad = dict(row, **{key:wrong})
            with self.subTest(key=key), self.assertRaises(ValueError):
                capacitor(bad,'kemet-open-mode')

    def test_rcs_jumpers_use_current_ratings_not_resistor_power(self):
        for size,pack,current in [('0402','ED','3A'),('0603','EA','3.5A'),
                                  ('0805','EA','4A'),('1206','EA','5A')]:
            p = resistor({'mpn':f'RCS{size}0000Z0{pack}'},'vishay-rcs')
            self.assertEqual((p.value,p.power,p.voltage,p.tcr),('0','','',''))
            self.assertIn('Imax='+current,p.features)

    def test_era_a_keeps_mixed_codes(self):
        mod = load_module(str(ROOT/'hlcl/vendors/panasonic/era-a/panasonic-era-a.py'))
        rows = mod.build_table()
        index = rows[0].index('MPN')
        mpns = {r[index] for r in rows[1:]}
        self.assertIn('ERA-2ARB6811X',mpns)
        self.assertIn('ERA-2ARB562X',mpns)
        self.assertIn('ERA-2ARB5620X',mpns)  # 562 ohm, distinct from 562 = 5.6 kohm
        self.assertNotIn('ERA-2ARB5601X',mpns)  # 5.6 kohm uses the E24 code
        self.assertIn('ERA-2AEB9091X',mpns)
        self.assertIn('ERA-2AEB911X',mpns)

    def test_samsung_automotive_packaging_and_height(self):
        mod = load_module(str(ROOT/'hlcl/vendors/samsung/cl/samsung-capacitors.py'))
        for base, size, suffixes, height in [('CL10B223KC8WPN','0603',('C','D'),90),
                                           ('CL31B474KCHWPN','1206',('E','F'),180)]:
            row, root, _ = mod.build_row(base,{size})
            self.assertEqual(row[mod.HEADERS.index('Qual')],'AEC-Q200')
            self.assertEqual([row[mod.HEADERS.index(f'MPN {n}')] for n in (2,3)],
                             [base+s for s in suffixes])
            self.assertEqual(row[mod.HEADERS.index('MPN 4')],'')
            self.assertTrue(root.endswith(f'X{height}_SAMA'))

    def test_manufacturer_pad_geometry_survives_density_expansion(self):
        for family,mpn,length,width,gap in [('vishay-rcp','RCP2512W15R0FEA',3.38,3.28,.61),
                                          ('murata-krm','KRM55QR72A106KH01L',2.7,5.6,2.6)]:
            part = find_part(family,mpn)
            with patch.object(_common,'density_codes',return_value=('L','N','M')):
                fps = _common.expand_footprint_rows([part.geometry],family)
            for fp in fps:
                self.assertEqual(fp['landPatternMm'],{'padLength':length,'padWidth':width,'gap':gap})
                input = FootprintInput.from_json(fp)
                with patch('altium_pcblib.footprint._make_pad', wraps=__import__('altium_pcblib.footprint',fromlist=['_make_pad'])._make_pad) as make_pad:
                    build_chip_footprint(input)
                    pad = make_pad.call_args_list[0].args[2]
                    self.assertAlmostEqual(pad.pad_length_along_terminal_mm,length)
                    self.assertAlmostEqual(pad.pad_width_across_terminal_mm,width)
                    self.assertAlmostEqual(pad.g_mm,gap)

    def test_optional_geometry_is_validated(self):
        geom = find_part('murata-krm','KRM55QR72A106KH01L').geometry
        with patch.object(_common,'density_codes',return_value=('N',)):
            fp, = _common.expand_footprint_rows([geom],'murata-krm')
        for field,value in [('landPatternMm',{'padLength':2.7,'padWidth':5.6,'gap':0}),
                            ('model',{'type':'unknown'})]:
            bad = copy.deepcopy(fp);bad[field]=value
            with self.assertRaises(ValueError):_common._validate_footprint(bad)


if __name__ == '__main__':
    unittest.main()
