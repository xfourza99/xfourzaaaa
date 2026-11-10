"""DC bias analysis for a voltage-divider common-emitter BJT stage.

All values are SI units unless the field name says otherwise: volts, ohms and
amps. The web layer is responsible for converting display units.
"""

from dataclasses import dataclass

VCE_SAT = 0.2

CUTOFF_WARNING = "Transistor is in cutoff: base bias is at or below VBE."
SATURATION_WARNING = (
    "Transistor is saturated: results use VCE = 0.2 V (saturation estimate)."
)


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
