import unittest

from app import create_app, parse_form

FORM = {
    "vcc": "12", "r1": "47", "r2": "10", "rc": "4.7",
    "re": "1", "beta": "150", "vbe": "0.7",
}


class TestParseForm(unittest.TestCase):
    def test_converts_kilohms_to_ohms(self):
        values = parse_form(FORM)
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

    def test_page_includes_circuit_photo(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('src="/static/bjt-ce-bias-circuit.png"', page)
