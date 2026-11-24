import unittest
from unittest.mock import patch

from app import create_app, parse_form
from engineering.ngspice import (
    AcResult,
    OpResult,
    SimulationError,
    SpiceResult,
    TranResult,
)

FORM = {
    "mode": "divider",
    "vcc": "12", "r1": "47", "r2": "10", "rc": "4.7",
    "re": "1", "beta": "150", "vbe": "0.7",
}

FAKE_SPICE = SpiceResult(
    op=OpResult(vb=2.033, vc=5.599, ve=1.371, ic=1.3627e-3, ib=8.77e-6),
    ac=AcResult(gain_db=46.94, gain=222.41, f_low=100.0, f_high=None),
    tran=TranResult(vpp_out=4.393, gain=219.6, clipped=False),
    executable="ngspice_con",
)


class TestParseForm(unittest.TestCase):
    def test_converts_kilohms_to_ohms(self):
        values = parse_form(FORM, "divider")
        self.assertEqual(values["r1"], 47_000.0)
        self.assertEqual(values["re"], 1_000.0)


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_renders_all_fields(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', response.get_data(as_text=True))

    def test_active_submission_shows_operating_point(self):
        response = self.client.post("/", data=FORM)
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Active", page)
        self.assertIn("4.446", page)
        self.assertIn("1.324", page)

    def test_cutoff_submission_warns(self):
        response = self.client.post("/", data={**FORM, "r1": "100", "r2": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cutoff", response.get_data(as_text=True))

    def test_saturation_submission_warns_and_notes_approximation(self):
        response = self.client.post("/", data={**FORM, "r1": "10", "r2": "47"})
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Saturation", page)
        self.assertIn("not meaningful", page)

    def test_zero_vcc_returns_400_with_message(self):
        response = self.client.post("/", data={**FORM, "vcc": "0"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("VCC must be greater than zero", response.get_data(as_text=True))

    def test_non_numeric_resistor_returns_400(self):
        response = self.client.post("/", data={**FORM, "r1": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("R1 must be a number", response.get_data(as_text=True))

    def test_blank_field_returns_400(self):
        response = self.client.post("/", data={**FORM, "beta": "  "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("beta is required", response.get_data(as_text=True))

    def test_active_submission_calls_approximation_valid(self):
        page = self.client.post("/", data=FORM).get_data(as_text=True)
        self.assertIn("approximation is valid", page)

    def test_saturation_submission_does_not_claim_approximation_valid(self):
        page = self.client.post("/", data={**FORM, "r1": "10", "r2": "47"})
        page = page.get_data(as_text=True)
        self.assertIn("not applicable outside the active region", page)
        self.assertNotIn("approximation is valid", page)

    def test_cutoff_submission_does_not_claim_approximation_valid(self):
        page = self.client.post("/", data={**FORM, "r1": "100", "r2": "1"})
        page = page.get_data(as_text=True)
        self.assertIn("not applicable outside the active region", page)
        self.assertNotIn("approximation is valid", page)

    def test_active_low_beta_approximation_is_flagged(self):
        data = {
            **FORM, "r1": "1", "r2": "1", "rc": "0.01",
            "re": "0.001", "beta": "10",
        }
        page = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn("outside its usual validity range", page)

    def test_page_includes_static_circuit_diagram(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="bias-circuit-title"', page)
        self.assertIn('id="bias-circuit-desc"', page)
        self.assertIn('id="bias-circuit-arrow"', page)
        for label in (
            ">VCC<", ">VB<", ">VC<", ">VE<", ">R1<", ">R2<", ">RC<",
            ">RE<", ">Q1<",
        ):
            self.assertIn(label, page)


class TestSimulationRoutes(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_divider_form_offers_simulation_checkbox(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('name="simulate"', page)

    def test_fixed_form_has_no_simulation_checkbox(self):
        page = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertNotIn('name="simulate"', page)

    def test_divider_without_simulation_has_no_spice_section(self):
        page = self.client.post("/", data=FORM).get_data(as_text=True)
        self.assertNotIn("ngspice cross-check", page)

    def test_simulation_results_render_the_comparison(self):
        with patch("app.simulate_divider", return_value=FAKE_SPICE):
            page = self.client.post(
                "/", data={**FORM, "simulate": "1"}
            ).get_data(as_text=True)
        self.assertIn("ngspice cross-check", page)
        self.assertIn("Gain at 1 kHz", page)
        self.assertIn("222.4", page)
        self.assertIn("Simulated VBE", page)

    def test_simulation_failure_degrades_gracefully(self):
        with patch(
            "app.simulate_divider",
            side_effect=SimulationError("ngspice was not found."),
        ):
            response = self.client.post("/", data={**FORM, "simulate": "1"})
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("ngspice was not found.", page)
        self.assertIn("1.324", page)

    def test_simulation_is_ignored_for_fixed_mode(self):
        data = {
            "mode": "fixed", "vcc": "12", "rb": "470", "rc": "4.7",
            "beta": "150", "vbe": "0.7", "simulate": "1",
        }
        with patch("app.simulate_divider") as simulate:
            page = self.client.post("/", data=data).get_data(as_text=True)
        simulate.assert_not_called()
        self.assertNotIn("ngspice cross-check", page)
