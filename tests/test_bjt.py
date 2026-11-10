import unittest

from engineering.bjt import BiasInput, analyze

ACTIVE = BiasInput(
    vcc=12.0, r1=47_000.0, r2=10_000.0, rc=4_700.0, re=1_000.0,
    beta=150.0, vbe=0.7,
)


class TestExactActiveRegion(unittest.TestCase):
    def test_voltage_divider_bias_operating_point(self):
        result = analyze(ACTIVE)
        self.assertEqual(result.region, "active")
        self.assertIsNone(result.warning)
        self.assertAlmostEqual(result.vbb, 2.1052631579, places=9)
        self.assertAlmostEqual(result.rb, 8245.6140350877, places=6)
        self.assertAlmostEqual(result.ib, 8.824501487275531e-06, places=12)
        self.assertAlmostEqual(result.ic, 0.0013236752230913298, places=12)
        self.assertAlmostEqual(result.ie, 0.0013324997245786052, places=12)
        self.assertAlmostEqual(result.ve, 1.3324997246, places=9)
        self.assertAlmostEqual(result.vc, 5.7787264515, places=9)
        self.assertAlmostEqual(result.vb, 2.0324997246, places=9)
        self.assertAlmostEqual(result.vce, 4.4462267269, places=9)
