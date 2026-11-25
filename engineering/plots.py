"""Server-side SVG plots for the Lab 4 dashboard.

Only ngspice sample arrays are plotted. The SVG is generated from finite
floats with fixed labels, so it can be inserted into the template as-is;
there is no client-side plotting library and no animation.
"""

from __future__ import annotations

import math
from typing import Iterable

from engineering.ngspice import AcResult, TranResult

_MARGIN = {"left": 58, "right": 58, "top": 26, "bottom": 44}
_BLUE = "#1d4ed8"
_TEAL = "#0f766e"
_ORANGE = "#c2410c"
_INK = "#16233a"
_MUTED = "#5a6b82"
_GRID = "#dce5ef"


def _finite_pairs(xs: Iterable[float], ys: Iterable[float]) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for x, y in zip(xs, ys):
        if math.isfinite(x) and math.isfinite(y):
            pairs.append((float(x), float(y)))
    return pairs


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def _hz(value: float) -> str:
    if value >= 1e6:
        return f"{value / 1e6:g} MHz"
    if value >= 1e3:
        return f"{value / 1e3:g} kHz"
    return f"{value:g} Hz"


def _open_svg(title_id: str, title: str, desc: str, width: int, height: int) -> list[str]:
    return [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{title_id} {title_id}-desc" '
        'xmlns="http://www.w3.org/2000/svg">',
        f"<title id=\"{title_id}\">{title}</title>",
        f"<desc id=\"{title_id}-desc\">{desc}</desc>",
    ]


def _legend(parts: list[tuple[str, str]], x: float, y: float) -> str:
    items = []
    for color, label in parts:
        items.append(
            f'<line x1="{_fmt(x)}" y1="{_fmt(y)}" x2="{_fmt(x + 14)}" '
            f'y2="{_fmt(y)}" stroke="{color}" stroke-width="3"/>'
            f'<text x="{_fmt(x + 20)}" y="{_fmt(y + 4)}" fill="{_INK}" '
            f'font-size="11">{label}</text>'
        )
        x += 20 + len(label) * 6.2 + 12
    return "".join(items)


def dc_load_line_svg(
    *,
    vcc: float,
    rc_ohm: float,
    re_ohm: float,
    beta: float,
    icq_a: float,
    vceq_v: float,
    source: str,
) -> str:
    """DC load line on IC-versus-VCE axes with a labelled operating point."""
    width, height = 640, 300
    left, right = 68, 28
    top, bottom = 28, 52
    title_id = "dc-load-line-title"
    desc = (
        "Collector current in milliamps versus collector-emitter voltage in "
        "volts. The load line crosses the VCE axis at VCC and the IC axis at "
        "the saturation current. The Q marker reports ICQ and VCEQ from the "
        f"active engine ({source})."
    )
    lines = _open_svg(
        title_id,
        "DC load line with operating point",
        desc,
        width,
        height,
    )

    finite = all(
        math.isfinite(value)
        for value in (vcc, rc_ohm, re_ohm, beta, icq_a, vceq_v)
    )
    if not finite or vcc <= 0 or rc_ohm <= 0 or re_ohm < 0 or beta < 1:
        lines.append(
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'fill="{_MUTED}" font-size="13">Valid DC inputs are required to '
            "plot the load line.</text>"
        )
        lines.append("</svg>")
        return "".join(lines)

    # IE = IC * (1 + 1/beta), the same relation used by the analytical model.
    emitter_factor = 1.0 + 1.0 / beta if re_ohm > 0 else 0.0
    load_slope_ohm = rc_ohm + re_ohm * emitter_factor
    ic_max_ma = vcc / load_slope_ohm * 1e3
    icq_ma = icq_a * 1e3
    x_max = max(vcc, vceq_v, 1.0)
    y_max = max(ic_max_ma, icq_ma, 0.1) * 1.08
    qx_v = min(max(vceq_v, 0.0), x_max)
    qy_ma = min(max(icq_ma, 0.0), y_max)

    def px(value: float) -> float:
        return left + value / x_max * (width - left - right)

    def py(value: float) -> float:
        return top + (y_max - value) / y_max * (height - top - bottom)

    for index in range(6):
        x_value = x_max * index / 5
        x = px(x_value)
        lines.append(
            f'<line x1="{_fmt(x)}" y1="{top}" x2="{_fmt(x)}" '
            f'y2="{height - bottom}" stroke="{_GRID}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{_fmt(x)}" y="{height - bottom + 18}" '
            f'text-anchor="middle" fill="{_MUTED}" font-size="11">'
            f"{x_value:.1f}</text>"
        )
        y_value = y_max * index / 5
        y = py(y_value)
        lines.append(
            f'<line x1="{left}" y1="{_fmt(y)}" x2="{width - right}" '
            f'y2="{_fmt(y)}" stroke="{_GRID}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{left - 8}" y="{_fmt(y + 4)}" text-anchor="end" '
            f'fill="{_MUTED}" font-size="11">{y_value:.2f}</text>'
        )

    qx, qy = px(qx_v), py(qy_ma)
    lines.append(
        f'<line x1="{left}" y1="{_fmt(qy)}" x2="{_fmt(qx)}" y2="{_fmt(qy)}" '
        f'stroke="{_ORANGE}" stroke-width="1" stroke-dasharray="4 4"/>'
    )
    lines.append(
        f'<line x1="{_fmt(qx)}" y1="{_fmt(qy)}" x2="{_fmt(qx)}" '
        f'y2="{height - bottom}" stroke="{_ORANGE}" stroke-width="1" '
        'stroke-dasharray="4 4"/>'
    )
    lines.append(
        f'<line x1="{_fmt(px(0))}" y1="{_fmt(py(ic_max_ma))}" '
        f'x2="{_fmt(px(vcc))}" y2="{_fmt(py(0))}" stroke="{_BLUE}" '
        'stroke-width="2.5" stroke-linejoin="round"/>'
    )
    lines.append(
        f'<circle cx="{_fmt(qx)}" cy="{_fmt(qy)}" r="7" fill="{_ORANGE}" '
        'stroke="#ffffff" stroke-width="2"/>'
    )
    lines.append(
        f'<circle cx="{_fmt(qx)}" cy="{_fmt(qy)}" r="2" fill="#ffffff"/>'
    )

    q_label = f"Q: ICQ={icq_ma:.3f} mA, VCEQ={qx_v:.3f} V"
    right_side = qx > left + (width - left - right) * 0.62
    label_x = qx - 10 if right_side else qx + 10
    label_y = qy - 12 if qy > top + 22 else qy + 22
    lines.append(
        f'<text x="{_fmt(label_x)}" y="{_fmt(label_y)}" '
        f'text-anchor="{"end" if right_side else "start"}" '
        f'fill="{_INK}" font-size="12" font-weight="600">{q_label}</text>'
    )
    lines.append(
        f'<text x="{width // 2}" y="{height - 6}" text-anchor="middle" '
        f'fill="{_MUTED}" font-size="11">VCE (V)</text>'
    )
    lines.append(
        f'<text transform="translate(16 {height // 2}) rotate(-90)" '
        f'text-anchor="middle" fill="{_MUTED}" font-size="11">IC (mA)</text>'
    )
    lines.append(
        _legend(
            [(_BLUE, "DC load line"), (_ORANGE, f"Q-point ({source})")],
            left + 6,
            top + 14,
        )
    )
    lines.append("</svg>")
    return "".join(lines)


def dc_compare_svg(rows: list[dict]) -> str:
    """Grouped bars comparing the analytical and simulated DC quantities."""
    width, height = 640, 236
    left, right = 82, 74
    top, bottom = _MARGIN["top"], _MARGIN["bottom"] // 2
    lines = _open_svg(
        "dc-compare-title",
        "Analytical versus ngspice DC operating point",
        "Paired bars for VB, VE, VC, IC and VCE.",
        width,
        height,
    )
    usable_rows = rows[:5]
    if not usable_rows:
        lines.append(
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'fill="{_MUTED}" font-size="13">Run ngspice to compare the DC values.</text>'
        )
    else:
        span = height - top - bottom
        step = span / len(usable_rows)
        for index, row in enumerate(usable_rows):
            analytical = abs(float(row["analytical"]))
            simulated = abs(float(row["spice"]))
            ceiling = max(analytical, simulated, 1e-12)
            center = top + step * (index + 0.5)
            for offset, color, value in (
                (-9.0, _BLUE, analytical),
                (3.0, "#12325a", simulated),
            ):
                bar_width = (width - left - right) * value / ceiling
                lines.append(
                    f'<rect x="{left}" y="{_fmt(center + offset - 4)}" '
                    f'width="{_fmt(max(bar_width, 1))}" height="8" rx="2" '
                    f'fill="{color}"/>'
                )
            lines.append(
                f'<text x="{left - 10}" y="{_fmt(center + 4)}" text-anchor="end" '
                f'fill="{_INK}" font-size="12" font-weight="600">{row["label"]}</text>'
            )
            delta = row["delta"]
            delta_text = f"{delta:.1f}%" if delta is not None else "n/a"
            lines.append(
                f'<text x="{width - right + 8}" y="{_fmt(center + 4)}" '
                f'fill="{_MUTED}" font-size="11">{delta_text}</text>'
            )
        lines.append(_legend([(_BLUE, "Analytical"), ("#12325a", "ngspice")], left, 12))
    lines.append("</svg>")
    return "".join(lines)


def bode_svg(ac: AcResult) -> str:
    """Magnitude and phase from the real .ac sweep, on a logarithmic x axis."""
    width, height = 640, 320
    left, right = _MARGIN["left"], _MARGIN["right"]
    top, bottom = _MARGIN["top"], _MARGIN["bottom"]
    points = _finite_pairs(ac.frequencies, ac.gain_db_points)
    phase_points = _finite_pairs(ac.frequencies, ac.phase_deg_points)
    lines = _open_svg(
        "bode-title",
        "Simulated Bode response",
        "Magnitude in decibels and phase in degrees versus logarithmic frequency.",
        width,
        height,
    )
    if len(points) < 2:
        lines.append(
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'fill="{_MUTED}" font-size="13">Run the AC sweep to plot the Bode response.</text>'
        )
        lines.append("</svg>")
        return "".join(lines)

    positive = [(x, y) for x, y in points if x > 0]
    if not positive:
        positive = [(1.0, y) for _, y in points]
    x_min, x_max = min(x for x, _ in positive), max(x for x, _ in positive)
    log_min, log_max = math.log10(x_min), math.log10(max(x_max, x_min * 10))
    db_values = [y for _, y in points]
    db_low, db_high = min(db_values), max(db_values)
    pad = max((db_high - db_low) * 0.12, 2.0)
    db_low, db_high = db_low - pad, db_high + pad
    phase_values = [y for _, y in phase_points] or [0.0]
    ph_low, ph_high = min(phase_values), max(phase_values)
    ph_pad = max((ph_high - ph_low) * 0.12, 5.0)
    ph_low, ph_high = ph_low - ph_pad, ph_high + ph_pad

    def px(freq: float) -> float:
        return left + (math.log10(max(freq, x_min)) - log_min) / (log_max - log_min) * (
            width - left - right
        )

    def py_db(value: float) -> float:
        return top + (db_high - value) / (db_high - db_low) * (height - top - bottom)

    def py_phase(value: float) -> float:
        return top + (ph_high - value) / (ph_high - ph_low) * (height - top - bottom)

    for decade in range(math.floor(log_min), math.ceil(log_max) + 1):
        freq = 10.0**decade
        if freq < x_min or freq > x_max:
            continue
        x = px(freq)
        lines.append(
            f'<line x1="{_fmt(x)}" y1="{top}" x2="{_fmt(x)}" '
            f'y2="{height - bottom}" stroke="{_GRID}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{_fmt(x)}" y="{height - bottom + 18}" text-anchor="middle" '
            f'fill="{_MUTED}" font-size="11">{_hz(freq)}</text>'
        )
    for index in range(5):
        value = db_low + (db_high - db_low) * index / 4
        y = py_db(value)
        lines.append(
            f'<line x1="{left}" y1="{_fmt(y)}" x2="{width - right}" y2="{_fmt(y)}" '
            f'stroke="{_GRID}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{left - 8}" y="{_fmt(y + 4)}" text-anchor="end" '
            f'fill="{_MUTED}" font-size="11">{value:.0f} dB</text>'
        )
        phase_value = ph_low + (ph_high - ph_low) * index / 4
        lines.append(
            f'<text x="{width - right + 8}" y="{_fmt(y + 4)}" '
            f'fill="{_MUTED}" font-size="11">{phase_value:.0f}°</text>'
        )

    probe_x = px(1000.0)
    if x_min <= 1000.0 <= x_max:
        lines.append(
            f'<line x1="{_fmt(probe_x)}" y1="{top}" x2="{_fmt(probe_x)}" '
            f'y2="{height - bottom}" stroke="{_MUTED}" stroke-width="1" '
            'stroke-dasharray="4 4"/>'
        )
        lines.append(
            f'<text x="{_fmt(probe_x + 5)}" y="{top + 12}" fill="{_MUTED}" '
            'font-size="11">1 kHz</text>'
        )

    dB_points = " ".join(f"{_fmt(px(x))},{_fmt(py_db(y))}" for x, y in points)
    ph_points = " ".join(
        f"{_fmt(px(x))},{_fmt(py_phase(y))}" for x, y in phase_points if x > 0
    )
    lines.append(
        f'<polyline points="{dB_points}" fill="none" stroke="{_BLUE}" '
        'stroke-width="2.5" stroke-linejoin="round"/>'
    )
    if ph_points:
        lines.append(
            f'<polyline points="{ph_points}" fill="none" stroke="{_TEAL}" '
            'stroke-width="2" stroke-linejoin="round"/>'
        )
    lines.append(
        f'<text x="{width // 2}" y="{height - 6}" text-anchor="middle" '
        f'fill="{_MUTED}" font-size="11">Frequency (Hz)</text>'
    )
    lines.append(
        f'<text transform="translate(16 {height // 2}) rotate(-90)" '
        f'text-anchor="middle" fill="{_MUTED}" font-size="11">Gain (dB)</text>'
    )
    lines.append(
        f'<text transform="translate({width - 12} {height // 2}) rotate(90)" '
        f'text-anchor="middle" fill="{_MUTED}" font-size="11">Phase (°)</text>'
    )
    lines.append(_legend([(_BLUE, "Gain (dB)"), (_TEAL, "Phase (°)")], left + 6, top + 16))
    lines.append("</svg>")
    return "".join(lines)


def waveforms_svg(tran: TranResult) -> str:
    """Vin and Vout versus time, from the real .tran samples."""
    width, height = 640, 320
    left, right = _MARGIN["left"], _MARGIN["right"]
    top, bottom = _MARGIN["top"], _MARGIN["bottom"]
    pairs = [
        (t, vin, vout)
        for t, vin, vout in zip(tran.times_s, tran.vin_v, tran.vout_v)
        if math.isfinite(t) and math.isfinite(vin) and math.isfinite(vout)
    ]
    lines = _open_svg(
        "waveforms-title",
        "Simulated input and collector output waveforms",
        "Vin in millivolts on the right axis and Vout in volts on the left axis, versus time in milliseconds.",
        width,
        height,
    )
    if len(pairs) < 2:
        lines.append(
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'fill="{_MUTED}" font-size="13">Run the transient analysis to plot the waveforms.</text>'
        )
        lines.append("</svg>")
        return "".join(lines)

    end_time = pairs[-1][0]
    start_time = max(pairs[0][0], end_time - 0.0012)
    window = [(t, vin, vout) for t, vin, vout in pairs if t >= start_time] or pairs
    t_min, t_max = window[0][0], window[-1][0]
    if t_max <= t_min:
        t_max = t_min + 1e-6
    vout_values = [vout for _, _, vout in window]
    vin_values = [vin for _, vin, _ in window]
    vout_low, vout_high = min(vout_values), max(vout_values)
    out_pad = max((vout_high - vout_low) * 0.18, 0.1)
    vout_low, vout_high = vout_low - out_pad, vout_high + out_pad
    vin_peak = max(abs(value) for value in vin_values) or 1e-3
    vin_low, vin_high = -vin_peak * 1.25, vin_peak * 1.25

    def px(time: float) -> float:
        return left + (time - t_min) / (t_max - t_min) * (width - left - right)

    def py_out(value: float) -> float:
        return top + (vout_high - value) / (vout_high - vout_low) * (height - top - bottom)

    def py_in(value: float) -> float:
        return top + (vin_high - value) / (vin_high - vin_low) * (height - top - bottom)

    for index in range(6):
        time = t_min + (t_max - t_min) * index / 5
        x = px(time)
        lines.append(
            f'<line x1="{_fmt(x)}" y1="{top}" x2="{_fmt(x)}" '
            f'y2="{height - bottom}" stroke="{_GRID}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{_fmt(x)}" y="{height - bottom + 18}" text-anchor="middle" '
            f'fill="{_MUTED}" font-size="11">{time * 1e3:.2f}</text>'
        )
    for index in range(5):
        value = vout_low + (vout_high - vout_low) * index / 4
        y = py_out(value)
        lines.append(
            f'<line x1="{left}" y1="{_fmt(y)}" x2="{width - right}" y2="{_fmt(y)}" '
            f'stroke="{_GRID}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{left - 8}" y="{_fmt(y + 4)}" text-anchor="end" '
            f'fill="{_MUTED}" font-size="11">{value:.1f}</text>'
        )
        vin_value = vin_low + (vin_high - vin_low) * index / 4
        lines.append(
            f'<text x="{width - right + 8}" y="{_fmt(y + 4)}" '
            f'fill="{_MUTED}" font-size="11">{vin_value * 1e3:.0f}</text>'
        )
    lines.append(
        f'<text x="{width // 2}" y="{height - 6}" text-anchor="middle" '
        f'fill="{_MUTED}" font-size="11">Time (ms)</text>'
    )

    vin_points = " ".join(f"{_fmt(px(t))},{_fmt(py_in(v))}" for t, v, _ in window)
    vout_points = " ".join(f"{_fmt(px(t))},{_fmt(py_out(v))}" for t, _, v in window)
    lines.append(
        f'<polyline points="{vin_points}" fill="none" stroke="{_TEAL}" '
        'stroke-width="2" stroke-linejoin="round"/>'
    )
    lines.append(
        f'<polyline points="{vout_points}" fill="none" stroke="{_ORANGE}" '
        'stroke-width="2.5" stroke-linejoin="round"/>'
    )
    lines.append(
        f'<text transform="translate(16 {height // 2}) rotate(-90)" '
        f'text-anchor="middle" fill="{_MUTED}" font-size="11">Vout (V)</text>'
    )
    lines.append(
        f'<text transform="translate({width - 12} {height // 2}) rotate(90)" '
        f'text-anchor="middle" fill="{_MUTED}" font-size="11">Vin (mV)</text>'
    )
    lines.append(_legend([(_TEAL, "Vin (mV)"), (_ORANGE, "Vout (V)")], left + 6, top + 16))
    lines.append("</svg>")
    return "".join(lines)
