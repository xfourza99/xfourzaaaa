# BJT Common-Emitter DC Bias Web App — Design

Date: 2026-11-10
Course: ENG29 2121
Status: approved by the human partner

## Intent and why

The lab deliverable is a working Flask web app that computes the DC operating
point of a voltage-divider-biased common-emitter BJT stage. Students enter the
bias values and see the operating point with units, a region label, warnings,
and an independent cross-check. The app must be small enough to finish, test
and demonstrate in one lab session.

## Goals

- Single page: input `VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE`.
- Output the DC operating point with units: `VBB`, `RB`, `VB`, `VE`, `VC`,
  `IB`, `IC`, `IE`, `VCE`.
- Validate inputs per field with clear messages.
- Label the region as active, cutoff or saturation and warn when the point is
  outside the active region.
- Show an independent, beta-independent approximation side by side with the
  exact calculation, including the validity ratio and the difference in `IC`.
- Separate engineering logic, Flask routes, templates, CSS and tests.
- Run on localhost and be committed to the existing GitHub repository.

## Non-goals

- No AC analysis, gain, input/output impedance or frequency response.
- No transient analysis, simulation or waveform plots.
- No schematic editor, netlist import or component library.
- No FET, op-amp or other topologies.
- No database, accounts, saved runs or deployment configuration.

## Anti-goals

- A result the app cannot justify from the shown formulas.
- Silent clamping or hiding of cutoff/saturation.
- Engineering math embedded in templates or routes.
- Treating the beta-independent approximation as exact.

## Constraints

- Python 3.12 is available; Flask is not yet installed.
- Git is installed but not on PATH; use
  `C:\Users\B6814182\AppData\Local\Programs\Git\cmd\git.exe`.
- Remote is `https://github.com/xfourza99/xfourzaaaa.git`.
- Existing `electrical.py` and `test_electrical.py` are unrelated and stay
  untouched.
- Tests use `unittest`, matching the existing repository style.
- The only runtime dependency is Flask.

## Approaches

1. **Server-rendered Flask with a pure-Python engineering module (chosen).**
   Math is importable and testable without HTTP, routes stay thin, and it
   matches the required separation.
2. **Browser-side JavaScript calculation.** Rejected: the engineering logic
   would leave Python and the test suite, contradicting the brief.
3. **Blueprints, database, saved runs.** Rejected: seven inputs, one user, no
   persistence requirement.

For the cross-check, the chosen approach is the beta-independent approximation.
A Shockley-equation nodal solver was rejected: it needs `IS` and `n`, an
iterative solver and a larger test surface for little lab value.

## Decided design

### Files

```
app.py                  create_app(), GET/POST "/", form parsing, unit conversion, filters
engineering/bjt.py      BiasInput, BiasResult, ValidationError, analyze(), analyze_approximate()
templates/index.html    form, results, comparison, formulas
static/style.css        one responsive stylesheet, no framework
tests/test_bjt.py       engineering tests
tests/test_app.py       route tests
requirements.txt        Flask
README.md               run steps, formulas, worked example
```

### Units

The engineering module uses SI units: volts, ohms, amps. The form accepts volts
and kilohms; the route converts once. Display uses V, mA, microamps and kohms.

### Exact calculation

```
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

### Independent approximation

```
VE_approx  = VBB - VBE
IE_approx  = VE_approx / RE
IC_approx  = IE_approx
VCE_approx = VCC - IC_approx * (RC + RE)
```

Show `beta * RE / RB`, label the approximation valid when the ratio is at
least 10, and show the percent difference in `IC`.

### Regions

- **Cutoff** when `VBB <= VBE`: `IB = IC = IE = 0`, `VCE = VCC`, warning only.
- **Saturation** when the active solution gives `VCE < 0.2 V`: warn, then
  re-solve with `VCE` pinned at 0.2 V using the base and collector loop
  equations with `IE = IC + IB`. This is the saturation estimate with base
  current included.
- Otherwise **active**.

### Validation

Per-field messages, re-rendered form, HTTP 400. Required, numeric, finite,
`VCC > 0`, all resistors `> 0`, `beta >= 1`, `0 < VBE < VCC`. No arbitrary
upper bounds.

### UI

One page: seven labeled inputs, Calculate button, region badge, quantity
table, exact-versus-approximate comparison, validity note, and the formulas
used. No JavaScript, login or storage.

### Tests

- One hand-worked fixture, independent of the app code and documented in the
  test.
- Cutoff case and saturation case.
- Saturation estimate consistency (`IE = IC + IB`, `VCE = 0.2`).
- Approximation validity flag and percent difference.
- Every validation rule.
- Routes: GET form, valid POST, invalid POST returning 400 with messages.

### Demo and commit

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Open `http://127.0.0.1:5000`. Commit with conventional messages; attempt a
push to `origin` (credentials may be required).

## Left to the builder

- Visual styling details and exact table wording.
- Additional worked fixtures beyond the primary one.
- README prose and screenshots, if useful.
