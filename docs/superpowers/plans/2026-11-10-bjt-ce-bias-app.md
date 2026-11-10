# BJT Common-Emitter DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Flask web app that computes the DC operating point of a voltage-divider-biased common-emitter BJT stage, validates inputs, flags cutoff/saturation, and cross-checks with a beta-independent approximation.

**Architecture:** Pure-Python engineering module (`engineering/bjt.py`) holds all math in SI units. `app.py` parses the form, converts kilohms to ohms, calls the module, and renders one Jinja page. Routes are thin; templates and CSS contain no engineering math. `unittest` covers the math and the routes.

**Tech Stack:** Python 3.12, Flask, Jinja2, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

## Global Constraints

- Python 3.12; only runtime dependency is Flask.
- Engineering module uses SI units: volts, ohms, amps.
- The web form accepts volts and kilohms; conversion happens once in `app.py`.
- Tests use `unittest`, run with `python -m unittest discover -s tests -v`.
- No JavaScript, database, login, AC or transient analysis.
- `VCE_SAT = 0.2` volts.
- Leave `electrical.py` and `test_electrical.py` untouched.
- Git is not on PATH. Use `& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe'` for every git command.
- Remote: `https://github.com/xfourza99/xfourzaaaa.git`.
- Commit after every task with a conventional message.

## Review Focus

- `VBB` exactly equal to `VBE` must take the cutoff path, not divide into a zero or negative base current.
- Cutoff gives `IC = 0`; the percent-difference helper must return `None` and the page must render without a division error.
- Blank, whitespace, non-numeric or malformed form fields must return HTTP 400 with a field message, never HTTP 500.
- Saturation results must be labeled and the approximation must carry a "not meaningful here" note, since the beta-independent model assumes the active region.
- A `VBE` close to `VCC` and a `VBB` only just above `VBE` give a tiny `IB`; the result must stay finite and still be classified as active.

---

### Task 1: Environment and exact active-region calculation

**Files:**
- Create: `requirements.txt`
- Create: `engineering/__init__.py`
- Create: `engineering/bjt.py`
- Create: `tests/test_bjt.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `BiasInput(vcc, r1, r2, rc, re, beta, vbe)` frozen dataclass, all `float`, SI units.
  - `BiasResult(vbb, rb, vb, ve, vc, ib, ic, ie, vce, region, warning)` frozen dataclass; `region` is `"active" | "cutoff" | "saturation"`, `warning` is `str | None`.
  - `analyze(bias: BiasInput) -> BiasResult`.

- [ ] **Step 1: Create the environment and dependency file**

`requirements.txt`:

```text
Flask>=3.0,<4
```

Run:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_bjt.py`:

```python
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
        self.assertAlmostEqual(result.ib, 8.8245e-06, places=12)
        self.assertAlmostEqual(result.ic, 0.0013236752, places=12)
        self.assertAlmostEqual(result.ie, 0.0013324997, places=12)
        self.assertAlmostEqual(result.ve, 1.3324997246, places=9)
        self.assertAlmostEqual(result.vc, 5.7787264515, places=9)
        self.assertAlmostEqual(result.vb, 2.0324997246, places=9)
        self.assertAlmostEqual(result.vce, 4.4462267269, places=9)
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engineering'`.

- [ ] **Step 4: Implement the data types and active-region calculation**

In `engineering/bjt.py`, implement the frozen dataclasses from Interfaces and `analyze`, using the spec formulas:

```text
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
IB  = (VBB - VBE) / (RB + (1 + beta) * RE)
IC  = beta * IB
IE  = (1 + beta) * IB
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VBE + VE
VCE = VC - VE
```

`engineering/__init__.py` stays empty. For this task `analyze` always returns `region="active"` and `warning=None`; region branching comes in Task 2.

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: PASS (1 test).

- [ ] **Step 6: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add requirements.txt engineering tests
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "feat: add exact BJT bias calculation"
```

---

### Task 2: Cutoff and saturation regions

**Files:**
- Modify: `engineering/bjt.py`
- Modify: `tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInput`, `BiasResult`, `analyze` from Task 1.
- Produces: `VCE_SAT = 0.2` and region-aware `analyze`; same signature.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bjt.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: FAIL — cutoff/saturation tests report `'active'` instead.

- [ ] **Step 3: Add region branching**

Extend `analyze`:

- If `VBB <= VBE`: return cutoff with `ib = ic = ie = 0`, `ve = 0`, `vb = VBB`, `vc = VCC`, `vce = VCC`, `region="cutoff"`, warning `"Transistor is in cutoff: base bias is at or below VBE."`
- Otherwise compute the active solution from Task 1. If active `VCE >= VCE_SAT`, keep `region="active"`, `warning=None`.
- If active `VCE < VCE_SAT`, re-solve with `VCE` pinned at `VCE_SAT` using the base and collector loops with `IE = IC + IB`:

```text
IB * (RB + RE) + IC * RE = VBB - VBE
IB * RE + IC * (RC + RE) = VCC - VCE_SAT

det = (RB + RE) * (RC + RE) - RE**2
IB  = ((VBB - VBE) * (RC + RE) - RE * (VCC - VCE_SAT)) / det
IC  = ((RB + RE) * (VCC - VCE_SAT) - RE * (VBB - VBE)) / det
IE  = IB + IC
VB  = VBB - IB * RB
VE  = IE * RE
VC  = VCC - IC * RC
VCE = VCE_SAT
```

Return `region="saturation"` with warning `"Transistor is saturated: results use VCE = 0.2 V (saturation estimate)."`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add engineering/bjt.py tests/test_bjt.py
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "feat: detect cutoff and saturation"
```

---

### Task 3: Independent approximation and comparison

**Files:**
- Modify: `engineering/bjt.py`
- Modify: `tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInput` from Task 1.
- Produces:
  - `ApproxResult(ve, ic, vce, beta_re_over_rb, valid)` frozen dataclass.
  - `analyze_approximate(bias: BiasInput) -> ApproxResult`.
  - `ic_difference_percent(exact_ic: float, approx_ic: float) -> float | None` — `None` when `exact_ic == 0`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bjt.py`:

```python
from engineering.bjt import analyze_approximate, ic_difference_percent

LOW_BETA_RE = BiasInput(
    vcc=12.0, r1=1_000.0, r2=1_000.0, rc=1_000.0, re=10.0,
    beta=10.0, vbe=0.7,
)


class TestApproximation(unittest.TestCase):
    def test_beta_independent_approximation(self):
        approx = analyze_approximate(ACTIVE)
        self.assertAlmostEqual(approx.ve, 1.4052631579, places=9)
        self.assertAlmostEqual(approx.ic, 0.0014052632, places=12)
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: FAIL with `ImportError: cannot import name 'analyze_approximate'`.

- [ ] **Step 3: Implement the approximation**

Use `VBB` and `RB` from the same Thevenin values as Task 1:

```text
VE_APPROX  = VBB - VBE
IE_APPROX  = VE_APPROX / RE
IC_APPROX  = IE_APPROX
VCE_APPROX = VCC - IC_APPROX * (RC + RE)
ratio      = beta * RE / RB
valid      = ratio >= 10
```

`ic_difference_percent` returns `None` if `exact_ic == 0`, else `abs(exact_ic - approx_ic) / abs(exact_ic) * 100`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add engineering/bjt.py tests/test_bjt.py
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "feat: add independent beta-independent cross-check"
```

---

### Task 4: Input validation

**Files:**
- Modify: `engineering/bjt.py`
- Modify: `tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasInput` from Task 1.
- Produces:
  - `ValidationError(ValueError)` with `.field: str` and `.message: str`; `str(error)` is the message.
  - `FIELD_LABELS = {"vcc": "VCC", "r1": "R1", "r2": "R2", "rc": "RC", "re": "RE", "beta": "beta", "vbe": "VBE"}`
  - `validate(values: Mapping[str, float]) -> BiasInput` — checks finite values and ranges, raises `ValidationError`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bjt.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: FAIL with `ImportError: cannot import name 'ValidationError'`.

- [ ] **Step 3: Implement validation**

`validate` checks, in this order, and raises `ValidationError(field, message)` on the first failure:

1. `math.isfinite` for every field → `"{label} must be a finite number"`.
2. `vcc > 0` → `"VCC must be greater than zero"`.
3. every resistor `> 0` → `"{label} must be greater than zero"`.
4. `beta >= 1` → `"beta must be at least 1"`.
5. `vbe > 0` → `"VBE must be greater than zero"`.
6. `vbe < vcc` → `"VBE must be less than VCC"`.

Return `BiasInput(**values)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_bjt.py" -v`
Expected: PASS (16 tests).

- [ ] **Step 5: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add engineering/bjt.py tests/test_bjt.py
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "feat: validate bias inputs"
```

---

### Task 5: Flask routes, form and page

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_app.py`

**Interfaces:**
- Consumes: `BiasInput`, `analyze`, `analyze_approximate`, `ic_difference_percent`, `validate`, `ValidationError`, `FIELD_LABELS` from Tasks 1-4.
- Produces:
  - `parse_form(form: Mapping[str, str]) -> dict[str, float]` — requires all seven keys, strips whitespace, parses floats, multiplies `r1`, `r2`, `rc`, `re` by 1000; raises `ValidationError` with `"{label} is required"` or `"{label} must be a number"`.
  - `create_app() -> Flask` with `GET /` and `POST /`.
  - Template filters `volts`, `milliamps`, `microamps`, `kilohms`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_app.py" -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Implement `parse_form` and `create_app`**

`app.py`:

- `FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")`
- `RESISTOR_FIELDS = ("r1", "r2", "rc", "re")`
- `parse_form` reads `form.get(field)`, strips it, raises `ValidationError(field, f"{FIELD_LABELS[field]} is required")` when empty, catches `ValueError` to raise `"{label} must be a number"`, and scales resistors by `1000.0`.
- `create_app` registers filters:
  - `volts`: `f"{value:.3f} V"`
  - `milliamps`: `f"{value * 1e3:.3f} mA"`
  - `microamps`: `f"{value * 1e6:.2f} µA"`
  - `kilohms`: `f"{value / 1e3:.3f} kΩ"`
- `GET /`: render `index.html` with `form={}`, `result=None`, `approx=None`, `ic_diff=None`, `approx_note=None`.
- `POST /`: `parse_form` then `validate`, `analyze`, `analyze_approximate`, `ic_difference_percent`. Set `approx_note = "The approximation assumes the active region; it is not meaningful here."` when `result.region != "active"`. Catch `ValidationError` and re-render with `status=400`, passing `form=request.form` and `error_field`/`error_message`.
- Module bottom: `app = create_app()` and `if __name__ == "__main__": app.run(debug=True)`.

`templates/index.html`: one page with a `<form method="post">` containing seven numeric inputs named as above, labels `VCC (V)`, `R1 (kΩ)`, `R2 (kΩ)`, `RC (kΩ)`, `RE (kΩ)`, `beta`, `VBE (V)`, and a submit button. When `result` exists, show:

- region badge with `{{ result.region|capitalize }}`,
- warning paragraph when `result.warning`,
- table of `VBB`, `RB`, `VB`, `VE`, `VC`, `IB`, `IC`, `IE`, `VCE` using the filters,
- exact-versus-approximate comparison: `VE`, `IC`, `VCE`, ratio `{{ "%.1f"|format(approx.beta_re_over_rb) }}`, and `{{ "%.1f"|format(ic_diff) }}%` when `ic_diff is not none`, otherwise `n/a`,
- `approx_note` paragraph when set,
- a "Formulas" section listing the exact and approximate equations from the spec.

When `error_message` exists, show it next to the matching field and at the top.

`static/style.css`: a single stylesheet with a centered card, a responsive form grid, readable tables, and distinct colors for active, cutoff and saturation badges. No framework.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: PASS (24 tests).

- [ ] **Step 5: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add app.py templates static tests/test_app.py
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "feat: add Flask interface for BJT bias"
```

---

### Task 6: README, localhost demo and push

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: the running app from Task 5.
- Produces: documented run and test commands, a worked example, and a pushed commit.

- [ ] **Step 1: Write `README.md`**

Include:

- Title and one-paragraph purpose.
- Requirements: Python 3.12.
- Setup:
  ```powershell
  python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
  .venv\Scripts\python app.py
  ```
  then open `http://127.0.0.1:5000`.
- Tests: `.venv\Scripts\python -m unittest discover -s tests -v`.
- Inputs and units: V, kΩ, beta, VBE.
- Exact formulas and the beta-independent approximation from the spec.
- Worked example: `VCC=12 V`, `R1=47 kΩ`, `R2=10 kΩ`, `RC=4.7 kΩ`, `RE=1 kΩ`, `beta=150`, `VBE=0.7 V` gives `IC≈1.324 mA`, `VCE≈4.446 V`, active; approximation `IC≈1.405 mA`, `VCE=3.99 V`, `6.2%` difference.
- Region rules and the `VCE_SAT = 0.2 V` estimate.
- Scope note: DC only; no AC, transient, schematic editor or FET.

- [ ] **Step 2: Run the full suite**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: PASS (24 tests), no failures or errors.

- [ ] **Step 3: Start the server and verify localhost**

Run:

```powershell
$server = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "app.py" -PassThru
Start-Sleep -Seconds 2
(Invoke-WebRequest http://127.0.0.1:5000 -UseBasicParsing).StatusCode
Stop-Process -Id $server.Id
```

Expected: `200`.

- [ ] **Step 4: Commit the README**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add README.md
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "docs: document BJT bias app usage and formulas"
```

- [ ] **Step 5: Push and report**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' push origin main
```

Expected: push succeeds. If credentials are missing, report that the commits are local and give the exact command to push.
