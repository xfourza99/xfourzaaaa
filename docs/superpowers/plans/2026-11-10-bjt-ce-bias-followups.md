# BJT CE Bias Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the one Important review finding — the approximation is called "valid" outside the active region — and add the approved static circuit diagram to the page.

**Architecture:** Template and CSS changes only; the engineering module, routes and form parsing are unchanged. Route tests pin the new copy, and a GET test pins the SVG.

**Tech Stack:** Python 3.12, Flask, Jinja2, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

**Predecessor plan:** `docs/superpowers/plans/2026-11-10-bjt-ce-bias-app.md` (tasks 1-6 complete).

## Global Constraints

- No new dependencies; Flask stays the only runtime dependency.
- Tests use `unittest`; the existing 24 tests must stay green.
- No JavaScript, database, login, AC or transient analysis.
- The circuit diagram is a static inline SVG: it must not show live or submitted values and must not be editable.
- Engineering logic stays in `engineering/bjt.py`; no math moves into templates.
- `VCE_SAT = 0.2` volts and all unit conventions stay unchanged.
- Git is not on PATH. Use `& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe'`.
- Leave `electrical.py` and `test_electrical.py` untouched.

## Review Focus

- Cutoff and saturation must never print "approximation is valid" while also showing the "not meaningful here" note.
- An active-region result with `beta * RE / RB < 10` must still say the approximation is outside its usual validity range.
- The diagram must contain no submitted values; it is a fixed reference drawing, not a live schematic.
- The diagram must render on both the empty form page and a results page, and must not disturb the form or results tables.
- The SVG must scale on narrow screens via `viewBox`, `width: 100%` and `height: auto`.

---

### Task 1: Region-aware approximation validity

**Files:**
- Modify: `templates/index.html:114-121`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: `result.region`, `approx.valid`, `approx.beta_re_over_rb` from the existing route context.
- Produces: no new Python API; copy and tests only.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_app.py` inside `TestRoutes`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_app.py" -v`
Expected: the saturation and cutoff tests FAIL because the page still prints "approximation is valid". The active and low-beta tests PASS, pinning existing behavior.

- [ ] **Step 3: Make the validity copy region-aware**

Replace the `{% if approx.valid %} ... {% endif %}` block in `templates/index.html` with:

```jinja
      {% if result.region == 'active' %}
        {% if approx.valid %}
        &mdash; approximation is valid (ratio &ge; 10).
        {% else %}
        &mdash; approximation is outside its usual validity range (ratio &lt; 10).
        {% endif %}
      {% else %}
      &mdash; not applicable outside the active region (ratio condition
      {% if approx.valid %}met{% else %}not met{% endif %}).
      {% endif %}
```

Keep the ratio line and the existing `approx_note` paragraph unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_app.py" -v`
Expected: PASS (12 route/parsing tests).

- [ ] **Step 5: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add templates/index.html tests/test_app.py
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "fix: make approximation validity region-aware"
```

---

### Task 2: Static circuit diagram

**Files:**
- Modify: `templates/index.html` (insert the figure after `</header>`, before the error message)
- Modify: `static/style.css`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: nothing; the SVG is static markup.
- Produces: `figure.schematic` with an inline `<svg>` carrying the IDs `bias-circuit-title`, `bias-circuit-desc` and `bias-circuit-arrow`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py` inside `TestRoutes`:

```python
    def test_page_includes_static_circuit_diagram(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="bias-circuit-title"', page)
        self.assertIn('id="bias-circuit-desc"', page)
        self.assertIn('id="bias-circuit-arrow"', page)
        for label in (">VCC<", ">VB<", ">VC<", ">VE<", ">R1<", ">R2<", ">RC<", ">RE<", ">Q1<"):
            self.assertIn(label, page)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python -m unittest discover -s tests -p "test_app.py" -v`
Expected: FAIL — `id="bias-circuit-title"` is absent.

- [ ] **Step 3: Insert the static SVG**

Insert this markup immediately after the `</header>` element in `templates/index.html`:

```html
    <figure class="schematic">
      <svg viewBox="0 0 640 420" role="img"
           aria-labelledby="bias-circuit-title bias-circuit-desc"
           xmlns="http://www.w3.org/2000/svg">
        <title id="bias-circuit-title">Voltage-divider biased NPN common-emitter circuit</title>
        <desc id="bias-circuit-desc">VCC feeds R1 and RC. R1 and R2 form the base voltage divider, RC is the collector resistor, RE is the emitter resistor, and Q1 is the NPN transistor. VB, VC and VE mark the base, collector and emitter voltages.</desc>
        <defs>
          <marker id="bias-circuit-arrow" viewBox="0 0 10 10" refX="9" refY="5"
                  markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#1f2933"/>
          </marker>
        </defs>
        <g fill="none" stroke="#1f2933" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
          <line x1="190" y1="50" x2="345" y2="50"/>
          <line x1="267" y1="50" x2="267" y2="32"/>

          <line x1="190" y1="50" x2="190" y2="90"/>
          <rect x="178" y="90" width="24" height="60" rx="3" fill="#ffffff"/>
          <line x1="190" y1="150" x2="190" y2="220"/>

          <line x1="190" y1="220" x2="190" y2="270"/>
          <rect x="178" y="270" width="24" height="60" rx="3" fill="#ffffff"/>
          <line x1="190" y1="330" x2="190" y2="380"/>

          <line x1="190" y1="220" x2="300" y2="220"/>
          <line x1="300" y1="195" x2="300" y2="245"/>

          <line x1="300" y1="205" x2="345" y2="180"/>
          <line x1="345" y1="180" x2="345" y2="150"/>

          <line x1="345" y1="50" x2="345" y2="90"/>
          <rect x="333" y="90" width="24" height="60" rx="3" fill="#ffffff"/>
          <line x1="345" y1="150" x2="345" y2="180"/>

          <line x1="300" y1="235" x2="340" y2="257"
                marker-end="url(#bias-circuit-arrow)"/>
          <line x1="340" y1="257" x2="345" y2="260"/>

          <line x1="345" y1="260" x2="345" y2="300"/>
          <rect x="333" y="300" width="24" height="60" rx="3" fill="#ffffff"/>
          <line x1="345" y1="360" x2="345" y2="380"/>

          <line x1="190" y1="380" x2="345" y2="380"/>
          <line x1="267" y1="380" x2="267" y2="392"/>
          <line x1="251" y1="392" x2="283" y2="392"/>
          <line x1="258" y1="398" x2="276" y2="398"/>
          <line x1="264" y1="404" x2="270" y2="404"/>
        </g>
        <g class="node">
          <circle cx="267" cy="50" r="4"/>
          <circle cx="190" cy="220" r="4"/>
          <circle cx="345" cy="180" r="4"/>
          <circle cx="345" cy="260" r="4"/>
        </g>
        <g class="diagram-label">
          <text x="267" y="24" text-anchor="middle">VCC</text>
          <text x="166" y="125" text-anchor="end">R1</text>
          <text x="166" y="305" text-anchor="end">R2</text>
          <text x="372" y="125">RC</text>
          <text x="372" y="335">RE</text>
          <text x="360" y="228">Q1</text>
          <text x="360" y="244" class="small">NPN</text>
          <text x="204" y="210">VB</text>
          <text x="356" y="172">VC</text>
          <text x="356" y="282">VE</text>
        </g>
      </svg>
      <figcaption>
        Voltage-divider bias network for an NPN common-emitter stage (DC bias only).
      </figcaption>
    </figure>
```

- [ ] **Step 4: Style the diagram**

Append to `static/style.css`:

```css
.schematic {
  margin: 0 0 1.5rem;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f8fafc;
}

.schematic svg {
  display: block;
  width: 100%;
  max-width: 520px;
  height: auto;
  margin: 0 auto;
}

.schematic text {
  fill: var(--ink);
  font-family: inherit;
  font-size: 14px;
}

.schematic .small {
  fill: var(--muted);
  font-size: 11px;
}

.schematic .node circle {
  fill: var(--ink);
  stroke: none;
}

.schematic figcaption {
  margin-top: 0.5rem;
  color: var(--muted);
  font-size: 0.85rem;
  text-align: center;
}
```

- [ ] **Step 5: Run the full suite**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: PASS (29 tests).

- [ ] **Step 6: Commit**

```powershell
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' add templates/index.html static/style.css tests/test_app.py
& 'C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe' commit -m "feat: add static bias circuit diagram"
```
