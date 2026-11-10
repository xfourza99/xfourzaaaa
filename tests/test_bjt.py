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


CUTOFF = BiasInput(
    vcc=12.0, r1=100_000.0, r2=1_000.0, rc=4_700.0, re=1_000.0,
    beta=150.0, vbe=0.7,
)
SATURATED = BiasInput(
    vcc=12.0, r1=10_000.0, r2=47_000.0, rc=4_700.0, re=1_000.0,
    beta=150.0, vbe=0.7,
)
BOUNDARY = BiasInput(
    vcc=12.0, r1=11_300.0, r2=700.0, rc=4_700.0, re=1_000.0,
    beta=150.0, vbe=0.7,
)
NEAR_CUTOFF = BiasInput(
    vcc=12.0, r1=11_100.0, r2=700.0, rc=4_700.0, re=1_000.0,
    beta=150.0, vbe=0.7,
)


class TestRegions(unittest.TestCase):
    def test_near_cutoff_stays_finite_and_active(self):
        import math

        result = analyze(NEAR_CUTOFF)  # VBB = 0.7119 V, only just above VBE
        self.assertEqual(result.region, "active")
        self.assertGreater(result.ic, 0.0)
        for value in (result.ib, result.ic, result.ie, result.vce):
            self.assertTrue(math.isfinite(value))

    def test_cutoff_when_base_bias_is_at_or_below_vbe(self):
        result = analyze(CUTOFF)
        self.assertEqual(result.region, "cutoff")
        self.assertEqual(result.ib, 0.0)
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ie, 0.0)
        self.assertEqual(result.ve, 0.0)
        self.assertEqual(result.vc, 12.0)
        self.assertEqual(result.vce, 12.0)
        self.assertIn("cutoff", result.warning.lower())

    def test_boundary_vbb_equal_to_vbe_is_cutoff(self):
        result = analyze(BOUNDARY)  # VBB = 12 * 700 / 12000 = 0.7 exactly
        self.assertEqual(result.region, "cutoff")
        self.assertEqual(result.ic, 0.0)

    def test_saturation_estimate_pins_vce(self):
        result = analyze(SATURATED)
        self.assertEqual(result.region, "saturation")
        self.assertAlmostEqual(result.vce, 0.2, places=12)
        self.assertAlmostEqual(result.ib, 7.854932e-04, places=10)
        self.assertAlmostEqual(result.ic, 1.9323696e-03, places=10)
        self.assertAlmostEqual(result.ie, result.ib + result.ic, places=12)
        self.assertIn("saturat", result.warning.lower())
