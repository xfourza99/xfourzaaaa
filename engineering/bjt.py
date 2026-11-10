"""DC bias analysis for a voltage-divider common-emitter BJT stage.

All values are SI units unless the field name says otherwise: volts, ohms and
amps. The web layer is responsible for converting display units.
"""

import math
from dataclasses import dataclass

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
}
FIELDS = tuple(FIELD_LABELS)

VCE_SAT = 0.2

CUTOFF_WARNING = "Transistor is in cutoff: base bias is at or below VBE."
SATURATION_WARNING = (
    "Transistor is saturated: results use VCE = 0.2 V (saturation estimate)."
)


class ValidationError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class BiasInput:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class ApproxResult:
    ve: float
    ic: float
    vce: float
    beta_re_over_rb: float
    valid: bool


@dataclass(frozen=True)
class BiasResult:
    vbb: float
    rb: float
    vb: float
    ve: float
    vc: float
    ib: float
    ic: float
    ie: float
    vce: float
    region: str
    warning: str | None


def analyze(bias: BiasInput) -> BiasResult:
    vbb = bias.vcc * bias.r2 / (bias.r1 + bias.r2)
    rb = bias.r1 * bias.r2 / (bias.r1 + bias.r2)

    if vbb <= bias.vbe:
        return BiasResult(
            vbb=vbb,
            rb=rb,
            vb=vbb,
            ve=0.0,
            vc=bias.vcc,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vce=bias.vcc,
            region="cutoff",
            warning=CUTOFF_WARNING,
        )

    ib = (vbb - bias.vbe) / (rb + (1 + bias.beta) * bias.re)
    ic = bias.beta * ib
    ie = (1 + bias.beta) * ib
    ve = ie * bias.re
    vc = bias.vcc - ic * bias.rc
    vb = bias.vbe + ve
    vce = vc - ve

    if vce < VCE_SAT:
        det = (rb + bias.re) * (bias.rc + bias.re) - bias.re**2
        ib = (
            (vbb - bias.vbe) * (bias.rc + bias.re)
            - bias.re * (bias.vcc - VCE_SAT)
        ) / det
        ic = (
            (rb + bias.re) * (bias.vcc - VCE_SAT)
            - bias.re * (vbb - bias.vbe)
        ) / det
        ie = ib + ic
        vb = vbb - ib * rb
        ve = ie * bias.re
        vc = bias.vcc - ic * bias.rc
        return BiasResult(
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
            warning=SATURATION_WARNING,
        )

    return BiasResult(
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


def analyze_approximate(bias: BiasInput) -> ApproxResult:
    vbb = bias.vcc * bias.r2 / (bias.r1 + bias.r2)
    rb = bias.r1 * bias.r2 / (bias.r1 + bias.r2)
    ve = vbb - bias.vbe
    ic = ve / bias.re
    vce = bias.vcc - ic * (bias.rc + bias.re)
    ratio = bias.beta * bias.re / rb
    return ApproxResult(
        ve=ve,
        ic=ic,
        vce=vce,
        beta_re_over_rb=ratio,
        valid=ratio >= 10,
    )


def ic_difference_percent(exact_ic: float, approx_ic: float) -> float | None:
    if exact_ic == 0:
        return None
    return abs(exact_ic - approx_ic) / abs(exact_ic) * 100


def validate(values: dict[str, float]) -> BiasInput:
    for field, label in FIELD_LABELS.items():
        if not math.isfinite(values[field]):
            raise ValidationError(field, f"{label} must be a finite number")

    if values["vcc"] <= 0:
        raise ValidationError("vcc", "VCC must be greater than zero")

    for field in ("r1", "r2", "rc", "re"):
        if values[field] <= 0:
            raise ValidationError(
                field, f"{FIELD_LABELS[field]} must be greater than zero"
            )

    if values["beta"] < 1:
        raise ValidationError("beta", "beta must be at least 1")

    if values["vbe"] <= 0:
        raise ValidationError("vbe", "VBE must be greater than zero")

    if values["vbe"] >= values["vcc"]:
        raise ValidationError("vbe", "VBE must be less than VCC")

    return BiasInput(**{field: values[field] for field in FIELDS})
