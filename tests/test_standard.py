"""Database-standard formatting, validation and extra-parameter selection.

Run after npm run regen: python -m unittest discover -s tests
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'hlcl'), str(ROOT/'hlcl/vendors')]
import _config
import _standard as std


def config_with_extras(family, extras):
    raw = json.loads((ROOT/'hlcl/factory-defaults.json').read_text())
    raw['families'][family] = {'enabled': True, 'options': {'extra_parameters': extras},
                               'overrides': {}}
    return patch.object(_config, 'current', return_value=_config.from_dict(raw))


def record(kind, **fields):
    row = {c: '' for c in std.COMMON + std.TYPE_FIELDS[kind]}
    row.update({'Comment': 'X1', 'MPN': 'X1', 'MFG': 'ACME', 'Package': '0402'}, **fields)
    return row


class StandardTests(unittest.TestCase):
    def test_formatters_match_documented_examples(self):
        self.assertEqual(std.resistor_description('THICK FILM', std.ohms(10000), '1%', '0402'),
                         'RESISTOR THICK FILM 10K OHM 1% 0402')
        self.assertEqual(std.resistor_description('THICK FILM', '0', '', '0402'),
                         'RESISTOR JUMPER 0 OHM 0402')
        self.assertEqual(std.capacitor_description(std.capacitance(100000), '10%', '16V', 'X7R', '0402'),
                         'CAPACITOR CERAMIC 100NF 10% 16V X7R 0402')
        self.assertEqual(std.inductor_description('MULTILAYER', std.inductance(4700), '20%',
                                                  std.dcr(0.1), '0402'),
                         'INDUCTOR MULTILAYER 4.7UH 20% 0.1 OHM 0402')
        self.assertEqual(std.ferrite_description(std.impedance(60), std.current(1), '0402'),
                         'FERRITE BEAD 60 OHM 1A 0402')
        self.assertEqual([std.ohms(v) for v in (100, 4700, 1e6, 0.2)], ['100', '4.7k', '1M', '0.2'])
        self.assertEqual([std.dcr(v) for v in (0.1, 0.0021)], ['0.1', '2.1m'])
        self.assertEqual([std.current(v) for v in (0.05, 1.5)], ['50mA', '1.5A'])
        self.assertEqual([std.impedance(v) for v in (60, 1000)], ['60OHM', '1KOHM'])

    def test_rule_violations_are_rejected(self):
        good = record('R', Description='RESISTOR THICK FILM 10K OHM 1% 0402', Value='10k',
                      Tolerance='1%', Voltage='50V', Tcr='+/-100', Tr='-55:155')
        std.check('R', good)
        for column, bad in [('Description', 'RESISTOR THICK FILM 10k OHM 1% 0402'),
                            ('Description', 'RESISTOR THICK FILM 10K OHM 1% 0402.'),
                            ('Description', 'RES THICK FILM 10K 1% 0402'),
                            ('MFG', 'Acme'), ('Tcr', '+/-100 ppm'), ('Tolerance', '±1%'),
                            ('Value', '10kΩ'), ('Tr', '-55 to 155'), ('Voltage', '50')]:
            with self.subTest(column=column, value=bad), self.assertRaises(ValueError):
                std.check('R', dict(good, **{column: bad}))

    def test_extras_follow_the_family_option(self):
        row = record('C', Description='CAPACITOR CERAMIC 1NF 5% 50V C0G 0402', Value='1nF',
                     **{'Datasheet': 'https://example.com/x.pdf', 'Features': 'C0G'})
        supported = ('features', 'rating_conditions', 'datasheet')
        with config_with_extras('fam', []):
            extras = std.enabled_extras('fam', supported)
        self.assertEqual(std.headers('C', extras), std.COMMON + std.TYPE_FIELDS['C'])
        with config_with_extras('fam', ['datasheet', 'features']):
            extras = std.enabled_extras('fam', supported)
        self.assertEqual(extras, ['features', 'datasheet'])  # EXTRAS order, not tick order
        self.assertEqual(std.cells('C', extras, row)[-2:], ['C0G', 'https://example.com/x.pdf'])
        with config_with_extras('fam', ['srf']), self.assertRaises(ValueError):
            std.enabled_extras('fam', supported)

    def test_missing_standard_columns_are_rejected(self):
        row = record('FB', Description='FERRITE BEAD 60 OHM 1A 0402', Value='60OHM')
        del row['DCR']
        with self.assertRaises(ValueError):
            std.cells('FB', [], row)


if __name__ == '__main__':
    unittest.main()
