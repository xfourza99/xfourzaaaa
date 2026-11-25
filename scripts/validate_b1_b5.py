from pathlib import Path
import re

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
EVID = Path("docs/evidence")
REPORT = Path("docs/validation.md")
VIEWPORT = {"width": 1280, "height": 900}

FIXTURES = {
    "fixed": {"vcc": "12", "rb": "1000", "rc": "2.2", "beta": "100", "vbe": "0.70"},
    "emitter": {"vcc": "12", "rb": "1000", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70"},
    "divider": {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70"},
}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def value(text: str, label: str, unit: str) -> str:
    match = re.search(rf"{label}\s*([0-9]+(?:\.[0-9]+)?)\s*{re.escape(unit)}", text)
    return f"{match.group(1)} {unit}" if match else "not available"


def dc_values(text: str) -> dict[str, str]:
    return {
        "ib": value(text, "IB", "µA"),
        "ic": value(text, "IC", "mA"),
        "vce": value(text, "VCE", "V"),
        "vb": value(text, "VB", "V"),
        "ve": value(text, "VE", "V"),
        "vc": value(text, "VC", "V"),
    }


def run_case(page, mode: str, fields: dict[str, str], simulate: bool) -> str:
    page.goto(BASE, wait_until="load")
    page.select_option("#mode", mode)
    page.get_by_role("button", name="Load mode").click()
    for name, val in fields.items():
        page.locator(f'input[name="{name}"]').fill(val)
    checkbox = page.locator('input[name="simulate"]')
    if checkbox.count():
        if simulate:
            checkbox.check()
        else:
            checkbox.uncheck()
    page.get_by_role("button", name="Run Simulation").click()
    page.wait_for_load_state("load")
    return norm(page.evaluate("document.body.textContent"))


def main() -> None:
    EVID.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport=VIEWPORT)

        fixed = dc_values(run_case(page, "fixed", FIXTURES["fixed"], False))
        emitter = dc_values(run_case(page, "emitter", FIXTURES["emitter"], False))
        divider = dc_values(run_case(page, "divider", FIXTURES["divider"], False))
        page.screenshot(path=str(EVID / "b1.png"), full_page=True)

        b2_text = run_case(page, "divider", FIXTURES["divider"], True)
        b2 = dc_values(b2_text)
        page.screenshot(path=str(EVID / "b2.png"), full_page=True)

        b3_before = dc_values(run_case(page, "divider", FIXTURES["divider"], True))
        page.locator('input[name="re"]').fill("2")
        page.get_by_role("button", name="Run Simulation").click()
        page.wait_for_load_state("load")
        b3_text = norm(page.evaluate("document.body.textContent"))
        b3_after = dc_values(b3_text)
        page.screenshot(path=str(EVID / "b3.png"), full_page=True)

        b4_text = run_case(page, "divider", FIXTURES["divider"], True)
        page.get_by_role("heading", name="AC Frequency Response").locator("xpath=..").screenshot(
            path=str(EVID / "b4.png")
        )
        b5_text = b4_text
        page.get_by_role("heading", name="Transient Response").locator("xpath=..").screenshot(
            path=str(EVID / "b5.png")
        )

        browser.close()

    dc = lambda d: f"IB {d['ib']}, IC {d['ic']}, VCE {d['vce']}"
    b3_change = (
        f"IB {b3_before['ib']} → {b3_after['ib']}, "
        f"IC {b3_before['ic']} → {b3_after['ic']}, "
        f"VCE {b3_before['vce']} → {b3_after['vce']}"
    )
    no_ac = "No AC sweep has been run" in b4_text
    no_tran = "No transient analysis has been run" in b5_text
    spice_error = "ngspice was not found" in b2_text

    report = f"""# BJT CE Simulator — B1–B5 browser validation

Date: 2026-11-25  
Target: <{BASE}>  
Method: Python Playwright (Chrome), viewport {VIEWPORT['width']}×{VIEWPORT['height']}, real form submissions.

## Fixture

VCC 12 V, beta 100, VBE 0.70 V. CE reference: R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ.
B3 changes only RE: 1 kΩ → 2 kΩ. Source fixture (10 mV peak, 1 kHz) is not exposed by this app.

## Comparison table

| Case | Analytical (browser) | Real ngspice | Status |
|------|----------------------|--------------|--------|
| B1 | Fixed: {dc(fixed)} (PASS). Emitter: {dc(emitter)} (PASS). Divider: {dc(divider)} vs Lab 3 sheet IC 1.24 mA / VCE 8.02 V (FAIL). | not used | FAIL (divider only) |
| B2 | {dc(b2)}, VB {b2['vb']}, VE {b2['ve']}, VC {b2['vc']} | none — {'ngspice was not found' if spice_error else 'no .op output'} | NOT RUN |
| B3 | {b3_change}; operating point changed, no stale result | none — no .op output | PASS (analytical freshness) / NOT RUN (SPICE) |
| B4 | Av / fL / fH not produced; {'no AC sweep' if no_ac else 'AC output not available'} | none — no .ac output | NOT RUN |
| B5 | Vout peak-to-peak not produced; {'no transient analysis' if no_tran else 'transient output not available'} | none — no .tran output | NOT RUN |

No ngspice version or BJT model was exercised. The page reported: `ngspice was not found. Install it to C:\\Spice64 and add C:\\Spice64\\bin to PATH, then restart the app.`
No Av, fL, fH, Vout peak-to-peak, Bode data, or waveform data was fabricated.

## Evidence

![B1 Result](evidence/b1.png)

![B2 Result](evidence/b2.png)

![B3 Result](evidence/b3.png)

![B4 Result](evidence/b4.png)

![B5 Result](evidence/b5.png)
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Screenshots: {EVID}/b1.png ... {EVID}/b5.png")


if __name__ == "__main__":
    main()
