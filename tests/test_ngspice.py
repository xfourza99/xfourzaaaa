import math
import unittest

from engineering.ngspice import (
    AC_STOP_HZ,
    SimulationError,
    build_netlist,
    find_ngspice,
    simulate_divider,
)

STAGE = dict(vcc=12.0, r1=47_000.0, r2=10_000.0, rc=4_700.0, re=1_000.0, beta=150.0)


class TestFindNgspice(unittest.TestCase):
    def test_returns_a_path_or_none(self):
        found = find_ngspice()
        self.assertTrue(found is None or isinstance(found, str))


class TestBuildNetlist(unittest.TestCase):
    def test_contains_the_stage_and_model(self):
        netlist = build_netlist(**STAGE)
        self.assertIn("R1 vcc vb 47000", netlist)
        self.assertIn("R2 vb 0 10000", netlist)
        self.assertIn("RC vcc vc 4700", netlist)
        self.assertIn("RE ve 0 1000", netlist)
        self.assertIn("BF=150", netlist)
        self.assertIn(".control", netlist)
        for command in ("op", "ac dec", "tran", "wrdata"):
            self.assertIn(command, netlist)

    def test_beta_reaches_the_model_card(self):
        netlist = build_netlist(**{**STAGE, "beta": 42.0})
        self.assertIn("BF=42", netlist)

    def test_rejects_zero_resistance(self):
        with self.assertRaises(SimulationError):
            build_netlist(**{**STAGE, "re": 0.0})

    def test_rejects_non_finite_values(self):
        with self.assertRaises(SimulationError):
            build_netlist(**{**STAGE, "vcc": math.inf})


@unittest.skipUnless(find_ngspice(), "ngspice_con is not installed")
class TestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = simulate_divider(**STAGE)

    def test_operating_point_is_physically_sane(self):
        op = self.result.op
        self.assertAlmostEqual(op.vbe, 0.66, delta=0.05)
        self.assertGreater(op.vce, 0.2)
        self.assertLess(op.ic, 0.012)

    def test_operating_point_is_close_to_the_analytical_solution(self):
        # The analytical solution assumes VBE = 0.7 V; the model solves it.
        op = self.result.op
        self.assertAlmostEqual(op.ic * 1e3, 1.324, delta=0.15)
        self.assertAlmostEqual(op.vce, 4.446, delta=0.40)

    def test_ac_reports_gain_at_the_probe_frequency(self):
        self.assertGreater(self.result.ac.gain, 100.0)
        self.assertGreater(self.result.ac.gain_db, 40.0)

    def test_upper_corner_is_not_the_sweep_edge(self):
        f_high = self.result.ac.f_high
        self.assertTrue(f_high is None or f_high < AC_STOP_HZ)

    def test_transient_swing_is_not_clipped(self):
        self.assertGreater(self.result.tran.vpp_out, 1.0)
        self.assertFalse(self.result.tran.clipped)

    def test_transient_gain_agrees_with_ac_gain(self):
        ratio = self.result.tran.gain / self.result.ac.gain
        self.assertAlmostEqual(ratio, 1.0, delta=0.15)


if __name__ == "__main__":
    unittest.main()
