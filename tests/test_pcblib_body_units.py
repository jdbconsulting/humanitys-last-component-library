"""Regression checks against Altium's unit-qualified 3D-body parameters.

hlcl/coupon/amaya.PcbDoc (saved by Altium) contains, for example,
OVERALLHEIGHT=19.685mil for a 0.5 mm chip, ARCRESOLUTION=0.5mil,
and MODEL.3D.DZ=0mil. Binary polygon vertices still use raw units.
"""

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hlcl" / "house"))

from altium_pcblib.binary import BinaryWriter
from altium_pcblib.primitives import Coord, CoordPoint
from altium_pcblib.records import PcbComponentBody
from altium_pcblib.writer import _write_body


def read_body_record(body):
    writer = BinaryWriter()
    _write_body(writer, body)
    record = writer.getvalue()
    # u32 record size, 13-byte common header, 5 reserved bytes,
    # u32 parameter byte count, NUL-terminated parameter string.
    assert struct.unpack_from("<I", record)[0] == len(record) - 4
    length = struct.unpack_from("<I", record, 22)[0]
    text = record[26:26 + length]
    assert text.endswith(b"\0")
    params = dict(item.split("=", 1) for item in text[:-1].decode("ascii").strip("|").split("|"))
    return params, record[26 + length:]


class ComponentBodyUnitsTests(unittest.TestCase):
    def test_all_body_lengths_have_explicit_mil_units(self):
        body = PcbComponentBody(
            arc_resolution=Coord.from_mil(0.5),
            cavity_height=Coord.from_mil(2),
            standoff_height=Coord.from_mil(3),
            overall_height=Coord.from_mm(0.5),
            model_2d_x=Coord.from_mil(-4.25),
            model_2d_y=Coord.from_mil(5.125),
            model_3d_dz=Coord.from_mil(6.5),
            model_3d_rot_z=90.0,
            model_id="{EXAMPLE}",
        )
        params, _ = read_body_record(body)
        expected = {
            "ARCRESOLUTION": "0.5mil",
            "CAVITYHEIGHT": "2mil",
            "STANDOFFHEIGHT": "3mil",
            "OVERALLHEIGHT": "19.685mil",
            "MODEL.2D.X": "-4.25mil",
            "MODEL.2D.Y": "5.125mil",
            "MODEL.3D.DZ": "6.5mil",
        }
        for key, value in expected.items():
            with self.subTest(parameter=key):
                self.assertEqual(params[key], value)
        self.assertEqual(params["MODEL.3D.ROTZ"], "90")
        self.assertEqual(params["MODELID"], "{EXAMPLE}")
        self.assertEqual(params["MODEL.EMBED"], "TRUE")
        self.assertEqual(params["ISSHAPEBASED"], "FALSE")

    def test_chip_heights_decode_to_millimetres(self):
        for height_mm in (0.065, 0.13, 0.35, 0.5, 1.0, 2.85):
            with self.subTest(height_mm=height_mm):
                params, _ = read_body_record(PcbComponentBody(overall_height=Coord.from_mm(height_mm)))
                text = params["OVERALLHEIGHT"]
                self.assertTrue(text.endswith("mil"), text)
                decoded_mm = float(text[:-3]) * 0.0254
                # Conversion to Altium's integer coordinate truncates by <1 raw unit.
                self.assertAlmostEqual(decoded_mm, height_mm, delta=0.00000254)
                self.assertEqual(params["STANDOFFHEIGHT"], "0mil")
                self.assertEqual(params["MODEL.3D.DZ"], "0mil")

    def test_binary_outline_coordinates_stay_in_raw_units(self):
        body = PcbComponentBody(outline=[CoordPoint(Coord.from_mil(-10), Coord.from_mil(20))])
        _, outline = read_body_record(body)
        count, x, y = struct.unpack("<Idd", outline)
        self.assertEqual(count, 1)
        self.assertEqual((x, y), (-100000.0, 200000.0))


if __name__ == "__main__":
    unittest.main()
