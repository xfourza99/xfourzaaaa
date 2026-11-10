"""DC bias analysis for a voltage-divider common-emitter BJT stage.

All values are SI units unless the field name says otherwise: volts, ohms and
amps. The web layer is responsible for converting display units.
"""

from dataclasses import dataclass


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
    ib = (vbb - bias.vbe) / (rb + (1 + bias.beta) * bias.re)
    ic = bias.beta * ib
    ie = (1 + bias.beta) * ib
    ve = ie * bias.re
    vc = bias.vcc - ic * bias.rc
    vb = bias.vbe + ve
    vce = vc - ve
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
