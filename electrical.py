"""DC bias analysis for NPN common-emitter BJT circuits.

All values passed to and returned from these functions are SI units:
volts, ohms and amps. The web layer converts kilohms to ohms once before
calling the analysis functions.
"""

import math

VCE_SAT = 0.2

MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
MODES = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rb": "RB",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
}

MODE_FIELDS = {
    MODE_DIVIDER: ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    MODE_FIXED: ("vcc", "rb", "rc", "beta", "vbe"),
    MODE_EMITTER: ("vcc", "rb", "rc", "re", "beta", "vbe"),
}

RESISTOR_FIELDS = ("r1", "r2", "rb", "rc", "re")

DIVIDER_CUTOFF_WARNING = (
    "Transistor is in cutoff: base bias is at or below VBE."
)
DIVIDER_SATURATION_WARNING = (
    "Transistor is saturated: results use VCE = 0.2 V (saturation estimate)."
)
FORWARD_ACTIVE_IB_WARNING = (
    "Forward-active model may not be valid: IB <= 0 A."
)
FORWARD_ACTIVE_VCE_WARNING = (
    "Forward-active model may not be valid: VCE <= 0.2 V."
)


class ValidationError(ValueError):
    """A validation problem tied to one form field."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


def _result(
    *,
    vbb: float,
    rb: float,
    vb: float,
    ve: float,
    vc: float,
    ib: float,
    ic: float,
    ie: float,
    vce: float,
    region: str,
    warning: str | None,
) -> dict[str, float | str | None]:
    """Build a result dict with the same keys for every bias mode."""
    return {
        "vbb": vbb,
        "rb": rb,
        "vb": vb,
        "ve": ve,
        "vc": vc,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "vce": vce,
        "region": region,
        "warning": warning,
    }


def validate_inputs(mode: str, values: dict[str, float]) -> None:
    """Validate SI-unit values for the selected bias mode.

    Presence and numeric conversion are handled by the web layer; this
    function owns the physical rules shared by all three modes.
    """
    if mode not in MODE_FIELDS:
        raise ValidationError("mode", "Unknown circuit mode")

    fields = MODE_FIELDS[mode]
    for field in fields:
        if field not in values:
            raise ValidationError(
                field, f"{FIELD_LABELS[field]} is required"
            )
        if not math.isfinite(values[field]):
            raise ValidationError(
                field, f"{FIELD_LABELS[field]} must be a finite number"
            )

    if values["vcc"] <= 0:
        raise ValidationError("vcc", "VCC must be greater than zero")

    for field in RESISTOR_FIELDS:
        if field in fields and values[field] <= 0:
            raise ValidationError(
                field,
                f"{FIELD_LABELS[field]} must be greater than zero",
            )

    if values["beta"] < 1:
        raise ValidationError("beta", "beta must be at least 1")

    if values["vbe"] <= 0:
        raise ValidationError("vbe", "VBE must be greater than zero")

    if values["vbe"] >= values["vcc"]:
        raise ValidationError("vbe", "VBE must be less than VCC")


def _forward_active_region(
    ib: float, vce: float
) -> tuple[str, str | None]:
    """Return the region label and warning for fixed/emitter bias."""
    if ib <= 0:
        return "cutoff", FORWARD_ACTIVE_IB_WARNING
    if vce <= VCE_SAT:
        return "saturation", FORWARD_ACTIVE_VCE_WARNING
    return "active", None


def analyze_voltage_divider(
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> dict[str, float | str | None]:
    """Voltage-divider bias, preserving the original exact/cutoff/saturation
    behavior and result values.
    """
    vbb = vcc * r2 / (r1 + r2)
    rb = r1 * r2 / (r1 + r2)

    if vbb <= vbe:
        return _result(
            vbb=vbb,
            rb=rb,
            vb=vbb,
            ve=0.0,
            vc=vcc,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vce=vcc,
            region="cutoff",
            warning=DIVIDER_CUTOFF_WARNING,
        )

    ib = (vbb - vbe) / (rb + (1 + beta) * re)
    ic = beta * ib
    ie = (1 + beta) * ib
    ve = ie * re
    vc = vcc - ic * rc
    vb = vbe + ve
    vce = vc - ve

    if vce < VCE_SAT:
        det = (rb + re) * (rc + re) - re**2
        ib = (
            (vbb - vbe) * (rc + re) - re * (vcc - VCE_SAT)
        ) / det
        ic = (
            (rb + re) * (vcc - VCE_SAT) - re * (vbb - vbe)
        ) / det
        ie = ib + ic
        vb = vbb - ib * rb
        ve = ie * re
        vc = vcc - ic * rc
        return _result(
            vbb=vbb,
            rb=rb,
            vb=vb,
            ve=ve,
            vc=vc,
            ib=ib,
            ic=ic,
            ie=ie,
            vce=VCE_SAT,
            region="saturation",
            warning=DIVIDER_SATURATION_WARNING,
        )

    return _result(
        vbb=vbb,
        rb=rb,
        vb=vb,
        ve=ve,
        vc=vc,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        region="active",
        warning=None,
    )


def analyze_fixed_bias(
    vcc: float,
    rb: float,
    rc: float,
    beta: float,
    vbe: float,
) -> dict[str, float | str | None]:
    """Fixed bias: IB = (VCC - VBE) / RB and VE = 0."""
    ib = (vcc - vbe) / rb
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = 0.0
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    region, warning = _forward_active_region(ib, vce)

    return _result(
        vbb=vcc,
        rb=rb,
        vb=vb,
        ve=ve,
        vc=vc,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        region=region,
        warning=warning,
    )


def analyze_emitter_bias(
    vcc: float,
    rb: float,
    rc: float,
    re: float,
    beta: float,
    vbe: float,
) -> dict[str, float | str | None]:
    """Emitter bias: IB = (VCC - VBE) / [RB + (beta + 1) * RE]."""
    ib = (vcc - vbe) / (rb + (beta + 1) * re)
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve
    region, warning = _forward_active_region(ib, vce)

    return _result(
        vbb=vcc,
        rb=rb,
        vb=vb,
        ve=ve,
        vc=vc,
        ib=ib,
        ic=ic,
        ie=ie,
        vce=vce,
        region=region,
        warning=warning,
    )


def analyze_dc(voltage_v, resistance_ohm):
    if resistance_ohm <= 0:
        raise ValueError("resistance_ohm must be greater than zero")
    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
    voltage_v = float(input("Enter voltage (V): "))
    resistance_ohm = float(input("Enter resistance (ohm): "))
    result = analyze_dc(voltage_v, resistance_ohm)
    print(f"Current: {result['current_a']} A")
    print(f"Power: {result['power_w']} W")
