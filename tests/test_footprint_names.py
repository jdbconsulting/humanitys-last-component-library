"""Vendor-specific vs generic footprint names, and merge collision reports.

Run after npm run regen: python -m unittest discover -s tests
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'hlcl'), str(ROOT/'hlcl/vendors'), str(ROOT/'hlcl/house')]
import _common
import _config
import build_house_footprints as merge


def naming(**families):
    """Patch the active config so each family uses the given naming."""
    raw = json.loads((ROOT/'hlcl/factory-defaults.json').read_text())
    for family, value in families.items():
        raw['families'][family]['options']['footprint_names'] = value
    return patch.object(_config, 'current', return_value=_config.from_dict(raw))


def body(root, length=1.0, terminal=0.25):
    return {'root': root, 'kind': 'R', 'drawingNote': 'test',
            'bodyMm': {'lengthNominal': length, 'widthNominal': 0.5,
                       'heightNominal': 0.4, 'terminalLengthNominal': terminal}}


class FootprintNameTests(unittest.TestCase):
    def test_vendor_names_are_the_default(self):
        with naming():
            self.assertEqual(_common.footprint_root('RESC0603X26_CRCW', 'vishay-crcw'), 'RESC0603X26_CRCW')
            self.assertEqual(_common.footprint_root('RESC1005X35', 'panasonic-erj'), 'RESC1005X35_ERJ')
            # Existing qualifiers win over the family tag.
            self.assertEqual(_common.footprint_root('CAPC1608X90_SAMA', 'samsung-capacitors'),
                             'CAPC1608X90_SAMA')

    def test_generic_names_drop_qualifiers(self):
        with naming(**{'vishay-crcw': 'generic', 'panasonic-erj': 'generic'}):
            self.assertEqual(_common.footprint_root('RESC0603X26_CRCW', 'vishay-crcw'), 'RESC0603X26')
            self.assertEqual(_common.footprint_root('RESC1005X35', 'panasonic-erj'), 'RESC1005X35')
            cells = _common.xls_footprint_columns('house.PcbLib', 'RESC0603X26_CRCW', 'vishay-crcw')
            self.assertIn('RESC0603X26N', cells)

    def test_generic_names_never_fold_different_geometry_in_one_family(self):
        bodies = [body('RESC1608X59_RCPW', 1.6, .30), body('RESC1608X59_RCPB', 1.6, .38)]
        with naming(**{'vishay-rcp': 'vendor'}):
            rows = _common.expand_footprint_rows(bodies, 'vishay-rcp')
        self.assertEqual({r['name'][:-1] for r in rows}, {'RESC1608X59_RCPW', 'RESC1608X59_RCPB'})
        with naming(**{'vishay-rcp': 'generic'}), self.assertRaises(ValueError):
            _common.expand_footprint_rows(bodies, 'vishay-rcp')
        same = [body('CAPC1608X90_SAMA'), body('CAPC1608X90')]
        same = [dict(b, kind='C') for b in same]
        with naming(**{'samsung-capacitors': 'generic'}), \
                patch.object(_common, 'density_codes', return_value=('N',)):
            rows = _common.expand_footprint_rows(same, 'samsung-capacitors')
        self.assertEqual([r['name'] for r in rows], ['CAPC1608X90N'])  # identical: shared once


class CollisionReportTests(unittest.TestCase):
    def test_merge_reports_names_several_vendors_emit(self):
        def fp(name, terminal):
            return {'name': name, 'kind': 'R', 'density': name[-1], 'drawingNote': 'test',
                    'bodyMm': {'lengthNominal': 1.6, 'widthNominal': 0.8,
                               'heightNominal': 0.45, 'terminalLengthNominal': terminal}}
        files = {
            'panasonic-erj': [fp('RESC1608X45N', .3), fp('RESC1608X45L', .3), fp('RESC1005X35N', .25)],
            'yageo-rc': [fp('RESC1608X45N', .3), fp('RESC1608X45L', .35)],
            'murata-ferrite': [fp('RESC1005X35N', .25)],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for vendor, rows in files.items():
                Path(tmp, f'{vendor}-footprints.json').write_text(json.dumps(
                    {'schemaVersion': 1, 'vendor': vendor, 'footprints': rows}))
            out = Path(tmp, 'house-footprints.json')
            with naming(), patch.object(merge, 'FOOTPRINTS_DIR', tmp), \
                    patch.object(merge, 'OUTPUT_PATH', str(out)), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(merge.main(), 0)
            doc = json.loads(out.read_text())
        collisions = {c['name']: c for c in doc['collisions']}
        self.assertEqual(set(collisions), {'RESC1608X45N', 'RESC1608X45L', 'RESC1005X35N'})
        self.assertTrue(collisions['RESC1608X45N']['sameGeometry'])
        self.assertFalse(collisions['RESC1608X45L']['sameGeometry'])
        # Ranked vendors come first; unranked vendors follow alphabetically.
        self.assertEqual(collisions['RESC1005X35N']['vendors'], ['panasonic-erj', 'murata-ferrite'])
        self.assertEqual(doc['familyIds']['murata-ferrite'], 'murata-ferrites')


if __name__ == '__main__':
    unittest.main()
