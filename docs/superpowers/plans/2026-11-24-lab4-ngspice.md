# Lab 4 — ngspice `.op` / `.ac` / `.tran` Cross-check

**Goal:** Add a real ngspice simulation of the reference voltage-divider CE
stage beside the existing analytical solution, without changing any of the
three Lab 3 analytical modes.

**Architecture:** A new, side-effect-free adapter (`engineering/ngspice.py`)
builds a netlist from validated floats, runs `ngspice_con -b` in a per-request
temporary directory, parses `wrdata` output, and returns dataclasses. The route
calls it only for the divider mode and only when the user ticks the box. A
failure degrades to a warning so the analytical result always renders.

**Tech Stack:** Python 3.12, Flask, `unittest`, ngspice 47 (`ngspice_con`).

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`
(the Lab 3 design; this plan is additive to it)

**Status:** implemented and verified.

## Global Constraints

- No new Python dependencies; Flask stays the only runtime dependency.
- `electrical.py` analytical functions and the fixed/emitter modes are
  unchanged; ngspice is divider-only and opt-in.
- The netlist is built from validated floats only — never from user text.
- The simulator is located via PATH, then `C:\Spice64\bin\ngspice_con.exe`,
  then `C:\Program Files\ngspice\bin\ngspice_con.exe`.
- Every run happens in a `TemporaryDirectory` so the threaded dev server cannot
  collide, with a 15 s timeout and `shell=False`.
- A missing or broken simulator must not break the page.
- Tests use `unittest`; the pre-existing 31 tests must stay green.

## Review Focus

- Analytical numbers must be identical whether or not the box is ticked.
- Fixed and emitter modes must ignore `simulate` entirely.
- The comparison must explain *why* SPICE differs (self-consistent VBE).
- `f_high` must never echo the sweep edge as if it were a corner.
- Transient gain must be measured on the collector node, not the still-charging
  coupling-capacitor node.

---

### Task 1: Simulator adapter

**Files:** Create `engineering/ngspice.py`

**Interfaces:**
- `find_ngspice() -> str | None`
- `build_netlist(*, vcc, r1, r2, rc, re, beta) -> str`
- `simulate_divider(...) -> SpiceResult`
- `SpiceResult(op: OpResult, ac: AcResult, tran: TranResult, executable: str)`
- Raises `SimulationError` with an install hint when unavailable.

- [x] Locate the binary (`shutil.which` then known paths).
- [x] Build a `.control` netlist: `op`, `ac dec 10 10 1e6`, `tran 10u 3m`,
      each followed by `wrdata` with `set wr_singlescale` / `set wr_vecnames`.
- [x] Model card `NPN(IS=1e-14 BF=beta VAF=100 CJC=3p CJE=10p TF=0.3n)`.
- [x] Parse `wrdata` by header name, not column index.
- [x] Run with timeout, no shell, hidden console window.

### Task 2: Route integration

**Files:** Modify `app.py`

- [x] Initialise `spice`, `spice_rows`, `spice_error`, `spice_note` to `None`
      before the mode dispatch so fixed/emitter stay unaffected.
- [x] On `mode == divider` and `form["simulate"]`, call `simulate_divider`.
- [x] Catch `SimulationError` into `spice_error`; never raise to the user.
- [x] `_spice_rows()` pairs VB/VE/VC/IC/VCE and computes percent differences.
- [x] Pass the four context keys through `render_page` defaults.

### Task 3: UI

**Files:** Modify `templates/index.html`, `static/style.css`

- [x] Checkbox `name="simulate"` rendered only for the divider mode.
- [x] Cross-check table: Quantity / Analytical / ngspice / Difference.
- [x] AC and transient table: gain, corners, swing, transient gain, clipping.
- [x] Show simulated VBE beside the entered VBE, plus the explanatory note.
- [x] Render the whole section only when a result or an error exists.
- [x] `.field.checkbox` styling consistent with the existing form.

### Task 4: Tests

**Files:** Create `tests/test_ngspice.py`; modify `tests/test_app.py`

- [x] Netlist-builder unit tests (values, model BF, invalid inputs).
- [x] Integration tests guarded by `skipUnless(find_ngspice())`.
- [x] Route tests patch `app.simulate_divider`, so they never need the binary.
- [x] Assert fixed mode ignores `simulate` and never renders the section.
- [x] Assert a `SimulationError` still returns 200 with the analytical result.

### Task 5: Docs

- [x] README: requirements, Lab 4 section, model caveat, project layout.
- [x] Scope section distinguishes analytical DC-only from the optional SPICE run.

## Verification

```
python -m unittest discover -s tests -v     # 48 tests, OK
```

Live divider run (`VCC 12, R1 47k, R2 10k, RC 4.7k, RE 1k, beta 150, VBE 0.7`):

| Quantity | Analytical | ngspice | Δ |
|----------|-----------|---------|---|
| VB | 2.032 V | 2.033 V | 0.0% |
| VE | 1.332 V | 1.371 V | 2.9% |
| VC | 5.779 V | 5.599 V | 3.1% |
| IC | 1.324 mA | 1.363 mA | 2.9% |
| VCE | 4.446 V | 4.228 V | 4.9% |

AC: 222.4 V/V (46.9 dB) at 1 kHz, lower corner 100 Hz, upper corner beyond the
1 MHz sweep. Transient: 4.39 V peak-to-peak, gain 219.6 V/V, no clipping.
Simulated VBE 0.662 V versus the entered 0.700 V — the expected model-vs-fixed
assumption difference.
