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


from engineering.bjt import analyze_approximate, ic_difference_percent

LOW_BETA_RE = BiasInput(
    vcc=12.0, r1=1_000.0, r2=1_000.0, rc=1_000.0, re=10.0,
    beta=10.0, vbe=0.7,
)


class TestApproximation(unittest.TestCase):
    def test_beta_independent_approximation(self):
        approx = analyze_approximate(ACTIVE)
        self.assertAlmostEqual(approx.ve, 1.4052631579, places=9)
        self.assertAlmostEqual(approx.ic, 0.0014052631578947367, places=12)
        self.assertAlmostEqual(approx.vce, 3.99, places=9)
        self.assertAlmostEqual(approx.beta_re_over_rb, 18.191489, places=5)
        self.assertTrue(approx.valid)

    def test_approximation_invalid_when_beta_re_is_small(self):
        self.assertFalse(analyze_approximate(LOW_BETA_RE).valid)

    def test_difference_percent(self):
        approx = analyze_approximate(ACTIVE)
        self.assertAlmostEqual(
            ic_difference_percent(analyze(ACTIVE).ic, approx.ic), 6.163743, places=5
        )

    def test_difference_is_none_when_exact_current_is_zero(self):
        self.assertIsNone(ic_difference_percent(0.0, 0.001))


from engineering.bjt import ValidationError, validate

VALID_VALUES = {
    "vcc": 12.0, "r1": 47_000.0, "r2": 10_000.0, "rc": 4_700.0,
    "re": 1_000.0, "beta": 150.0, "vbe": 0.7,
}


class TestValidation(unittest.TestCase):
    def assert_invalid(self, field, message, **changes):
        values = {**VALID_VALUES, **changes}
        with self.assertRaises(ValidationError) as caught:
            validate(values)
        self.assertEqual(caught.exception.field, field)
        self.assertEqual(caught.exception.message, message)

    def test_valid_values_become_bias_input(self):
        self.assertEqual(validate(VALID_VALUES), ACTIVE)

    def test_vcc_must_be_positive(self):
        self.assert_invalid("vcc", "VCC must be greater than zero", vcc=0.0)

    def test_each_resistor_must_be_positive(self):
        for field, label in (("r1", "R1"), ("r2", "R2"), ("rc", "RC"), ("re", "RE")):
            self.assert_invalid(field, f"{label} must be greater than zero", **{field: 0.0})

    def test_beta_must_be_at_least_one(self):
        self.assert_invalid("beta", "beta must be at least 1", beta=0.5)

    def test_vbe_must_be_positive(self):
        self.assert_invalid("vbe", "VBE must be greater than zero", vbe=0.0)

    def test_vbe_must_be_below_vcc(self):
        self.assert_invalid("vbe", "VBE must be less than VCC", vbe=12.0)

    def test_non_finite_values_are_rejected(self):
        self.assert_invalid("vcc", "VCC must be a finite number", vcc=float("inf"))
