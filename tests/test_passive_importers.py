"""Datasheet examples, negative ordering codes and manufacturing geometry.

Run after npm run regen: python -m unittest discover -s tests -v.
The generated-artifact audit additionally requires python hlcl/build.py all.
"""
import copy
import csv
import dataclasses
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'hlcl'), str(ROOT/'hlcl/vendors'), str(ROOT/'hlcl/house')]
import _common
import _standard
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
                       'kemet-esd-c0g', 'tdk-c', 'vishay-crcw', 'vishay-tnpw', 'vishay-rcs', 'vishay-rcp',
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
            ('vishay-crcw','CRCW02011K00FKED','1k','1%','0.05W'),
            ('vishay-crcw','CRCW020110R0FNED','10','1%','0.05W'),
            ('vishay-crcw','CRCW020110K0FNED','10k','1%','0.05W'),
            ('vishay-crcw','CRCW04021R00FNED','1','1%','0.063W'),
            ('vishay-crcw','CRCW0603562RFKEA','562','1%','0.1W'),
            ('vishay-tnpw','TNPW12061K32DEEA','1.32k','0.5%','0.27W'),  # datasheet example
            ('vishay-tnpw','TNPW040228K0BEED','28k','0.1%','0.07W'),
            ('vishay-tnpw','TNPW020122R0DEED','22','0.5%','0.05W'),
            ('vishay-tnpw','TNPW08053R52BYEA','3.52','0.1%','0.14W'),
            ('vishay-tnpw','TNPW12061K32DETA','1.32k','0.5%','0.25W'),  # SnPb
            ('vishay-crcw','CRCW04024K70JNED','4.7k','5%','0.063W'),
            ('vishay-crcw','CRCW121810K0FKEK','10k','1%','1W'),
            ('vishay-crcw','CRCW201010K0FKEF','10k','1%','0.75W'),
            ('vishay-crcw','CRCW2512100RFKEG','100','1%','1W'),
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
        for family, mpn in [('vishay-crcw','CRCW0603100RFKEB'),  # EB is not a CRCW reel
                            ('vishay-crcw','CRCW12182M70FKEK'),  # 1218 stops at 2.2 Mohm
                            ('vishay-crcw','CRCW06034K99JNEA'),  # 5% is E24 only
                            ('vishay-crcw','CRCW060310R0FNEA'),  # 200 ppm 1% stops at 9.76 ohm
                            ('vishay-crcw','CRCW06030K10FKEA'),  # non-canonical 100 ohm
                            ('vishay-crcw','CRCW06031002FKEA'),  # no embedded unit
                            ('vishay-crcw','CRCW06030000FKEA'),  # jumper needs Z0
                            ('vishay-crcw','CRCW020146R4FKED'),  # 0201 100 ppm starts at 47 ohm
                            ('vishay-crcw','CRCW02011K00FKEA'),  # EA is not a 0201 reel
                            ('vishay-crcw','CRCW02019R10JNED'),  # 0201 5% below 10 ohm is JX
                            ('vishay-crcw','CRCW04021R00FXED'),  # X TCR is 0201 only
                            ('vishay-tnpw','TNPW0603100RBXEC'),  # EC reel only for 25/50 ppm
                            ('vishay-tnpw','TNPW0201100RFEED'),  # 0201 has no 1% grade
                            ('vishay-tnpw','TNPW12102M20BEEA'),  # 1210 0.1% stops at 2.13 Mohm
                            ('vishay-tnpw','TNPW06031K01FEEA'),  # E192-only value at 1%
                            ('vishay-tnpw','TNPW0201100RDETD'),  # no SnPb 0201
                            ('vishay-tnpw','TNPW0402100RDETP'),  # SnPb TP reel only at 0.1%
                            ('vishay-tnpw','TNPW0402100RFEEA'),  # 0402 reel is ED
                            ('vishay-rcs','RCS040210K0FKEA'),
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

    def test_rcs_lands_use_bottom_terminal(self):
        for size,pack,bottom,top in [('0402','ED',.25,.2),('0603','EA',.3,.3),
                                     ('0805','EA',.3,.3),('1206','EA',.45,.4)]:
            g = resistor({'mpn':f'RCS{size}10K0FK{pack}'},'vishay-rcs').geometry
            self.assertEqual((g['bodyMm']['terminalLengthNominal'],
                              g['model']['topTerminalLengthMm']),(bottom,top))

    def test_crcw_jumpers_ratings_and_terminals(self):
        for size,pack,current in [('0201','ED','1A'),('0402','ED','1.5A'),('0603','EA','2A'),('0805','EA','2.5A'),
                                  ('1206','EA','3.5A'),('1210','EA','5A'),('1218','EK','7A'),
                                  ('2010','EF','6A'),('2512','EG','7A')]:
            p = resistor({'mpn':f'CRCW{size}0000Z0{pack}'},'vishay-crcw')
            self.assertEqual((p.value,p.power,p.voltage,p.tcr),('0','','',''))
            self.assertIn('Imax='+current,p.features)
        # 0402-0805 advertise standard-mode ratings, not the extended-mode table.
        p = resistor({'mpn':'CRCW08051K00FKEA'},'vishay-crcw')
        self.assertEqual((p.power,p.voltage,p.qualification),('0.125W','150V','AEC-Q200'))
        self.assertIn('standard operation mode',p.conditions)
        p = resistor({'mpn':'CRCW06031R00FNEA'},'vishay-crcw')
        self.assertEqual((p.tolerance,p.tcr),('1%','+/-200'))
        # 0201 has its own commercial datasheet: no AEC-Q200, 50 mOhm jumper.
        p = resistor({'mpn':'CRCW02014R70FXED'},'vishay-crcw')
        self.assertEqual((p.tcr,p.voltage,p.qualification),('-200/+400','30V',''))
        self.assertIn('20052',p.datasheet)
        self.assertIn('<=50mOhm',resistor({'mpn':'CRCW02010000Z0ED'},'vishay-crcw').features)
        # T1 (bottom) sets the lands; T2 (top) only shapes the 3D model.
        for size,pack,root,bottom,top in [('0201','ED','RESC0603X26_CRCW',.15,.1),
                                          ('0402','ED','RESC1005X40_CRCW',.25,.2),
                                          ('1218','EK','RESC3246X60_CRCW',.45,.4),
                                          ('2512','EG','RESC6332X70_CRCW',.6,.6)]:
            g = resistor({'mpn':f'CRCW{size}10K0FK{pack}'},'vishay-crcw').geometry
            self.assertEqual((g['root'],g['bodyMm']['terminalLengthNominal'],
                              g['model']['topTerminalLengthMm']),(root,bottom,top))

    def assert_catalog_complete(self, family, grades):
        """Every grade/value the decoder accepts on each size's catalog reel is listed."""
        rows = {r['mpn'] for r in catalog(family)}
        reels = {(m[:8], m[14:]) for m in rows}
        codes = {m[8:12] for m in rows}
        missing = []
        for model_size, reel in reels:
            for code in codes:
                for grade in grades:
                    mpn = f'{model_size}{code}{grade}{reel}'
                    try:
                        resistor({'mpn':mpn},family)
                    except ValueError:
                        continue
                    if mpn not in rows:
                        missing.append(mpn)
        self.assertEqual(missing, [])

    def test_crcw_catalog_lists_every_grade_the_decoder_accepts(self):
        self.assert_catalog_complete('vishay-crcw', ('FK','FN','FX','JN','JX','Z0'))

    def test_tnpw_catalog_lists_every_grade_the_decoder_accepts(self):
        self.assert_catalog_complete('vishay-tnpw', [t + c for t in 'FDB' for c in 'HEXY'])

    def test_tnpw_options_and_alternates(self):
        importer = load_module(str(ROOT/'hlcl/vendors/vishay/tnpw/importer.py'))
        parts = [importer.decode(r) for r in catalog('vishay-tnpw')]

        def chosen(**options):
            raw = json.loads((ROOT/'hlcl/factory-defaults.json').read_text())
            raw['families']['vishay-tnpw']['options'].update(options)
            with patch.object(importer._config, 'current', return_value=importer._config.from_dict(raw)):
                return [p.mpn for p in importer.select(parts)]

        default = chosen()
        self.assertEqual(len(default), 37622)  # e3 only, every TCR, tolerance and E192 value
        self.assertFalse(any(m[14:] in importer.SNPB_REELS for m in default))
        self.assertEqual(len(chosen(terminations=['e3', 'snpb'])), len(parts))
        lowest = chosen(lowest_tcr_only=True)
        self.assertEqual(len(lowest), len({(m[:13], m[14:]) for m in default}))
        self.assertIn('TNPW0805100RBYEA', lowest)  # 10 ppm wins at 0.1%
        self.assertNotIn('TNPW0805100RBEEA', lowest)
        self.assertEqual({m[12] for m in chosen(tolerance_options=['B'])}, {'B'})
        self.assertNotIn('TNPW08051K01DEEA', chosen(value_series='e96'))  # 1.01k is E192-only
        self.assertIn('TNPW08051K02DEEA', chosen(value_series='e96'))

        record = resistor({'mpn':'TNPW06031K00BEEA'},'vishay-tnpw').record('vishay-tnpw')
        self.assertEqual(record['MPN 2'], 'TNPW06031K00BEEC')
        record = resistor({'mpn':'TNPW06031K00BXEA'},'vishay-tnpw').record('vishay-tnpw')
        self.assertEqual(record['MPN 2'], '')  # no 20,000-piece reel at 15 ppm

    def test_crcw_tcr_options_and_reel_alternates(self):
        importer = load_module(str(ROOT/'hlcl/vendors/vishay/crcw/importer.py'))
        parts = [importer.decode(r) for r in catalog('vishay-crcw')]

        def chosen(**options):
            raw = json.loads((ROOT/'hlcl/factory-defaults.json').read_text())
            raw['families']['vishay-crcw']['options'].update(options)
            with patch.object(importer._config, 'current', return_value=importer._config.from_dict(raw)):
                return {p.mpn for p in importer.select(parts)}

        self.assertEqual(len(chosen()), len(parts))  # defaults: every TCR
        lowest = chosen(lowest_tcr_only=True)
        self.assertEqual(len(lowest), 8627)  # one TCR per value, tolerance and reel
        self.assertIn('CRCW020110K0FKED', lowest)
        self.assertNotIn('CRCW020110K0FNED', lowest)
        self.assertIn('CRCW020110R0FNED', lowest)  # FN is the tightest 1% grade at 10 ohm
        only_100 = chosen(tcr_options=['K'])
        self.assertTrue(all(m[13] in 'K0' for m in only_100))
        self.assertIn('CRCW06030000Z0EA', only_100)  # jumpers have no TCR
        self.assertFalse(any(m[12:14] == 'JN' for m in chosen(tcr_options=['K', 'X'])))

        record = resistor({'mpn':'CRCW06031K00FKEA'},'vishay-crcw').record('vishay-crcw')
        self.assertEqual([record[f'MPN {n}'] for n in range(2, 6)],
                         ['CRCW06031K00FKEC','CRCW06031K00FKED','CRCW06031K00FKEE','CRCW06031K00FKEI'])
        self.assertEqual(record['MFG 2'], 'VISHAY')
        self.assertEqual(_standard.cells('R', ['alternates'], record)[-8:-6], ['VISHAY','CRCW06031K00FKEC'])
        record = resistor({'mpn':'CRCW1218100RFKEK'},'vishay-crcw').record('vishay-crcw')
        self.assertEqual((record['MFG 2'], record['MPN 2']), ('', ''))  # 1218 has one reel

    def test_crcw_rows_follow_the_database_standard(self):
        def row(mpn):
            with patch.object(_common,'density_codes',return_value=('L','N','M')):
                record = resistor({'mpn':mpn},'vishay-crcw').record('vishay-crcw')
            return dict(zip(_standard.headers('R',[]),_standard.cells('R',[],record)))
        r = row('CRCW06034K70JNEA')
        self.assertEqual(list(r)[13:],['Qual','Value','Tolerance','Voltage','Tcr','Tr'])
        self.assertEqual((r['Description'],r['MFG'],r['Package'],r['Value'],r['Tolerance'],
                          r['Voltage'],r['Tcr'],r['Tr'],r['Qual'],r['Library Ref']),
                         ('RESISTOR THICK FILM 4.7K OHM 5% 0603','VISHAY','0603','4.7k','5%',
                          '75V','+/-200','-55:155','AEC-Q200','RES'))
        self.assertEqual([r[f'Footprint Ref{n}'] for n in ('',' 2',' 3')],
                         ['RESC1608X50_CRCWN','RESC1608X50_CRCWL','RESC1608X50_CRCWM'])
        self.assertEqual(row('CRCW02012M20FNED')['Description'],'RESISTOR THICK FILM 2.2M OHM 1% 0201')
        self.assertEqual(row('CRCW0402100RFKED')['Description'],'RESISTOR THICK FILM 100 OHM 1% 0402')
        self.assertEqual(row('CRCW04020000Z0ED')['Description'],'RESISTOR JUMPER 0 OHM 0402')
        bad = dataclasses.replace(resistor({'mpn':'CRCW04024K70JNED'},'vishay-crcw'),value='4.7k\u03a9')
        with self.assertRaises(ValueError):
            _standard.cells('R',[],bad.record('vishay-crcw'))

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
            self.assertEqual(row['Qual'],'AEC-Q200')
            self.assertEqual([row[f'MPN {n}'] for n in (2,3)],
                             [base+s for s in suffixes])
            self.assertEqual(row['MPN 4'],'')
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
