"""Optional ngspice cross-check for the voltage-divider CE stage.

The analytical solution in :mod:`electrical` stays authoritative; this module
only produces a second opinion from a real SPICE solve. It is deliberately
isolated: importing it has no side effects and calling it never mutates the
analytical result.

All values passed in and returned are SI units (volts, ohms, amps). The
netlist is written from validated floats only - no user text is ever
interpolated into it.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Known install locations, tried after PATH.
CANDIDATES = (
    r"C:\Spice64\bin\ngspice_con.exe",
    r"C:\Program Files\ngspice\bin\ngspice_con.exe",
    r"C:\Program Files (x86)\ngspice\bin\ngspice_con.exe",
)

TIMEOUT_SECONDS = 15.0

# Model card parameters. BF is taken from the form's beta; the rest are fixed
# so the AC and transient analyses have junction capacitances to work with.
MODEL_IS = 1e-14
MODEL_VAF = 100.0
MODEL_CJC = 3e-12
MODEL_CJE = 10e-12
MODEL_TF = 0.3e-9

AC_START_HZ = 10.0
AC_STOP_HZ = 1e6
AC_POINTS_PER_DECADE = 10
AC_PROBE_HZ = 1000.0

TRAN_STEP_S = 10e-6
TRAN_STOP_S = 3e-3
TRAN_PROBE_HZ = 1000.0
TRAN_INPUT_AMPLITUDE_V = 10e-3

INSTALL_HINT = (
    "ngspice was not found. Install it to C:\\Spice64 and add "
    "C:\\Spice64\\bin to PATH, then restart the app."
)


class SimulationError(RuntimeError):
    """The simulator could not be located, timed out, or produced no data."""


@dataclass(frozen=True)
class OpResult:
    vb: float
    vc: float
    ve: float
    ic: float
    ib: float

    @property
    def vce(self) -> float:
        return self.vc - self.ve

    @property
    def vbe(self) -> float:
        return self.vb - self.ve


@dataclass(frozen=True)
class AcResult:
    gain_db: float
    gain: float
    f_low: float | None
    f_high: float | None
    # Sweep samples, kept so the UI can plot a real Bode response.
    phase_deg: float = 0.0
    frequencies: tuple[float, ...] = ()
    gain_db_points: tuple[float, ...] = ()
    phase_deg_points: tuple[float, ...] = ()


@dataclass(frozen=True)
class TranResult:
    vpp_out: float
    gain: float
    clipped: bool
    # Steady-state window, kept so the UI can plot real waveforms.
    times_s: tuple[float, ...] = ()
    vin_v: tuple[float, ...] = ()
    vout_v: tuple[float, ...] = ()


@dataclass(frozen=True)
class SpiceResult:
    op: OpResult
    ac: AcResult
    tran: TranResult
    executable: str


def find_ngspice() -> str | None:
    """Return a usable ``ngspice_con`` path, or ``None``."""
    found = shutil.which("ngspice_con")
    if found:
        return found
    for candidate in CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


def _fmt(value: float) -> str:
    if not math.isfinite(value):
        raise SimulationError("Netlist values must be finite numbers.")
    return f"{value:.6g}"


def build_netlist(
    *,
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
) -> str:
    """Build the divider-stage netlist used for all three analyses."""
    if beta < 1:
        raise SimulationError("beta must be at least 1.")
    if min(vcc, r1, r2, rc, re) <= 0:
        raise SimulationError("VCC and every resistor must be greater than zero.")

    lines = [
        "* Lab 4 ngspice cross-check - voltage-divider CE stage",
        f"VCC vcc 0 {_fmt(vcc)}",
        f"R1 vcc vb {_fmt(r1)}",
        f"R2 vb 0 {_fmt(r2)}",
        f"RC vcc vc {_fmt(rc)}",
        f"RE ve 0 {_fmt(re)}",
        "CE ve 0 100u",
        "Q1 vc vb ve QNPN",
        (
            ".model QNPN NPN(IS={is_} BF={bf} VAF={vaf} "
            "CJC={cjc} CJE={cje} TF={tf})"
        ).format(
            is_=_fmt(MODEL_IS),
            bf=_fmt(beta),
            vaf=_fmt(MODEL_VAF),
            cjc=_fmt(MODEL_CJC),
            cje=_fmt(MODEL_CJE),
            tf=_fmt(MODEL_TF),
        ),
        f"VIN in 0 DC 0 AC 1 SIN(0 {_fmt(TRAN_INPUT_AMPLITUDE_V)} {_fmt(TRAN_PROBE_HZ)})",
        "CIN in vb 10u",
        "COUT vc out 10u",
        "RL out 0 100k",
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        "op",
        "wrdata op.txt v(vb) v(vc) v(ve) @q1[ic] @q1[ib]",
        f"ac dec {AC_POINTS_PER_DECADE} {_fmt(AC_START_HZ)} {_fmt(AC_STOP_HZ)}",
        "wrdata ac.txt vdb(out) vp(out)",
        f"tran {_fmt(TRAN_STEP_S)} {_fmt(TRAN_STOP_S)}",
        "wrdata tran.txt v(in) v(vc)",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def _read_wrdata(path: Path) -> dict[str, list[float]]:
    """Parse a ``wrdata`` file into ``{column_name: values}``."""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="ascii", errors="replace").strip()
    if not text:
        return {}
    rows = [line.split() for line in text.splitlines() if line.strip()]
    if len(rows) < 2:
        return {}
    header, body = rows[0], rows[1:]
    columns: dict[str, list[float]] = {name: [] for name in header}
    for row in body:
        if len(row) != len(header):
            continue
        try:
            values = [float(cell) for cell in row]
        except ValueError:
            continue
        for name, value in zip(header, values):
            columns[name].append(value)
    return columns


def _first(columns: dict[str, list[float]], name: str) -> float:
    values = columns.get(name)
    if not values:
        raise SimulationError(f"Simulation output is missing '{name}'.")
    return values[0]


def _index_at_hz(freqs: list[float], target: float) -> int:
    return min(range(len(freqs)), key=lambda i: abs(freqs[i] - target))


def _analyse_ac(columns: dict[str, list[float]]) -> AcResult:
    freqs = columns.get("frequency") or []
    db = columns.get("vdb(out)") or []
    phase = columns.get("vp(out)") or []
    if not freqs or len(freqs) != len(db):
        raise SimulationError("AC output is missing or malformed.")
    if not phase:
        phase = [0.0] * len(freqs)
    if len(phase) != len(freqs):
        phase = [0.0] * len(freqs)

    index = _index_at_hz(freqs, AC_PROBE_HZ)
    gain_db = db[index]
    gain = 10 ** (gain_db / 20.0)

    threshold = gain_db - 3.0
    f_low = next((f for f, value in zip(freqs, db) if value >= threshold), None)
    f_high = next(
        (f for f, value in zip(reversed(freqs), reversed(db)) if value >= threshold),
        None,
    )
    # The sweep edge is not a corner: report "beyond sweep" instead of a
    # number that merely echoes AC_STOP_HZ.
    if f_high is not None and f_high >= freqs[-1]:
        f_high = None
    return AcResult(
        gain_db=gain_db,
        gain=gain,
        f_low=f_low,
        f_high=f_high,
        phase_deg=phase[index],
        frequencies=tuple(freqs),
        gain_db_points=tuple(db),
        phase_deg_points=tuple(phase),
    )


def _analyse_tran(
    columns: dict[str, list[float]], *, vcc: float, ve: float
) -> TranResult:
    times = columns.get("time") or []
    out = columns.get("v(vc)") or []
    if not times or len(times) != len(out):
        raise SimulationError("Transient output is missing or malformed.")

    window = times[-1] - 1.0 / TRAN_PROBE_HZ
    samples = [value for time, value in zip(times, out) if time >= window]
    if not samples:
        raise SimulationError("Transient output has no steady-state samples.")

    vpp = max(samples) - min(samples)
    input_vpp = 2.0 * TRAN_INPUT_AMPLITUDE_V
    clipped = max(samples) > vcc - 0.05 or min(samples) < ve + 0.25

    # Keep the full transient trace, paired sample by sample. The steady-state
    # window is what the summary measures and what the plot displays.
    pairs = [
        (time, vin, vout)
        for time, vin, vout in zip(
            times, columns.get("v(in)") or [], columns.get("v(vc)") or []
        )
        if time >= window
    ]
    return TranResult(
        vpp_out=vpp,
        gain=vpp / input_vpp,
        clipped=clipped,
        times_s=tuple(time for time, _, _ in pairs),
        vin_v=tuple(vin for _, vin, _ in pairs),
        vout_v=tuple(vout for _, _, vout in pairs),
    )


def simulate_divider(
    *,
    vcc: float,
    r1: float,
    r2: float,
    rc: float,
    re: float,
    beta: float,
) -> SpiceResult:
    """Run ``.op``, ``.ac`` and ``.tran`` for the divider stage.

    Raises :class:`SimulationError` when ngspice is unavailable or the run
    produced no usable data, so the caller can degrade gracefully.
    """
    executable = find_ngspice()
    if not executable:
        raise SimulationError(INSTALL_HINT)

    netlist = build_netlist(vcc=vcc, r1=r1, r2=r2, rc=rc, re=re, beta=beta)

    with tempfile.TemporaryDirectory(prefix="ngspice-") as tmp:
        workdir = Path(tmp)
        (workdir / "circuit.cir").write_text(netlist, encoding="ascii")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            completed = subprocess.run(
                [executable, "-b", "circuit.cir"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                creationflags=creationflags,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SimulationError(
                f"ngspice did not finish within {TIMEOUT_SECONDS:.0f} s."
            ) from exc
        except OSError as exc:
            raise SimulationError(f"Could not start ngspice: {exc}") from exc

        op = _read_wrdata(workdir / "op.txt")
        ac = _read_wrdata(workdir / "ac.txt")
        tran = _read_wrdata(workdir / "tran.txt")

        if not op:
            detail = (completed.stdout or completed.stderr or "").strip()
            tail = detail[-400:] if detail else "no output"
            raise SimulationError(f"ngspice produced no operating point. {tail}")

        op_result = OpResult(
            vb=_first(op, "v(vb)"),
            vc=_first(op, "v(vc)"),
            ve=_first(op, "v(ve)"),
            ic=abs(_first(op, "@q1[ic]")),
            ib=abs(_first(op, "@q1[ib]")),
        )
        return SpiceResult(
            op=op_result,
            ac=_analyse_ac(ac),
            tran=_analyse_tran(tran, vcc=vcc, ve=op_result.ve),
            executable=executable,
        )
