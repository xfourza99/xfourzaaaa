"""Flask interface for the BJT common-emitter DC bias calculator."""

from flask import Flask, render_template, request

from electrical import (
    FIELD_LABELS,
    MODE_DIVIDER,
    MODE_EMITTER,
    MODE_FIELDS,
    MODE_FIXED,
    MODES,
    RESISTOR_FIELDS,
    ValidationError,
    analyze_emitter_bias,
    analyze_fixed_bias,
    analyze_voltage_divider,
    validate_inputs,
)
from engineering.bjt import (
    BiasInput,
    analyze_approximate,
    ic_difference_percent,
)
from engineering.ngspice import SimulationError, simulate_divider

MODE_LABELS = {
    MODE_DIVIDER: "Voltage Divider",
    MODE_FIXED: "Fixed Bias",
    MODE_EMITTER: "Emitter Bias",
}

APPROX_NOTE = (
    "The approximation assumes the active region; it is not meaningful here."
)

SPICE_NOTE = (
    "ngspice solves the transistor model self-consistently, so its "
    "base-emitter voltage differs from the fixed VBE the analytical solution "
    "assumes. The IC and VCE differences above are expected, not an error."
)


def parse_form(form, mode: str) -> dict[str, float]:
    """Read the fields required by ``mode`` and convert kilohms to ohms once."""
    if mode not in MODE_FIELDS:
        raise ValidationError("mode", "Unknown circuit mode")

    values = {}
    for field in MODE_FIELDS[mode]:
        raw = (form.get(field) or "").strip()
        if not raw:
            raise ValidationError(field, f"{FIELD_LABELS[field]} is required")
        try:
            value = float(raw)
        except ValueError:
            raise ValidationError(
                field, f"{FIELD_LABELS[field]} must be a number"
            ) from None
        if field in RESISTOR_FIELDS:
            value *= 1000.0
        values[field] = value
    return values


def _spice_rows(result: dict, spice) -> list[dict]:
    """Pair analytical and simulated quantities for the comparison table."""
    rows: list[dict] = []

    def add(label: str, unit: str, analytical: float, simulated: float) -> None:
        delta = None
        if analytical:
            delta = abs(analytical - simulated) / abs(analytical) * 100.0
        rows.append(
            {
                "label": label,
                "unit": unit,
                "analytical": analytical,
                "spice": simulated,
                "delta": delta,
            }
        )

    add("VB", "v", result["vb"], spice.op.vb)
    add("VE", "v", result["ve"], spice.op.ve)
    add("VC", "v", result["vc"], spice.op.vc)
    add("IC", "a", result["ic"], spice.op.ic)
    add("VCE", "v", result["vce"], spice.op.vce)
    return rows


def create_app() -> Flask:
    app = Flask(__name__)

    app.add_template_filter(lambda value: f"{value:.3f} V", "volts")
    app.add_template_filter(lambda value: f"{value * 1e3:.3f} mA", "milliamps")
    app.add_template_filter(lambda value: f"{value * 1e6:.2f} µA", "microamps")
    app.add_template_filter(lambda value: f"{value / 1e3:.3f} kΩ", "kilohms")

    def render_page(**context):
        context.setdefault("mode", MODE_DIVIDER)
        context.setdefault("mode_labels", MODE_LABELS)
        context.setdefault("spice", None)
        context.setdefault("spice_rows", None)
        context.setdefault("spice_error", None)
        context.setdefault("spice_note", None)
        return render_template("index.html", **context)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            mode = (request.args.get("mode") or MODE_DIVIDER).strip()
            if mode not in MODES:
                return (
                    render_page(
                        form={},
                        result=None,
                        approx=None,
                        ic_diff=None,
                        approx_note=None,
                        error_field="mode",
                        error_message="Unknown circuit mode",
                    ),
                    400,
                )
            return render_page(
                form={},
                mode=mode,
                result=None,
                approx=None,
                ic_diff=None,
                approx_note=None,
                error_field=None,
                error_message=None,
            )

        mode = (request.form.get("mode") or "").strip()
        try:
            if mode not in MODE_FIELDS:
                raise ValidationError("mode", "Unknown circuit mode")

            values = parse_form(request.form, mode)
            validate_inputs(mode, values)

            spice = None
            spice_rows = None
            spice_error = None
            spice_note = None

            if mode == MODE_DIVIDER:
                result = analyze_voltage_divider(**values)
                approx = analyze_approximate(BiasInput(**values))
                ic_diff = ic_difference_percent(result["ic"], approx.ic)
                approx_note = (
                    APPROX_NOTE if result["region"] != "active" else None
                )
                if request.form.get("simulate"):
                    try:
                        spice = simulate_divider(
                            vcc=values["vcc"],
                            r1=values["r1"],
                            r2=values["r2"],
                            rc=values["rc"],
                            re=values["re"],
                            beta=values["beta"],
                        )
                        spice_rows = _spice_rows(result, spice)
                        spice_note = SPICE_NOTE
                        if result["region"] == "saturation":
                            spice_note += (
                                " The analytical VCE is pinned at the 0.2 V"
                                " saturation convention, while the model"
                                " resolves its own, usually lower, saturation"
                                " voltage."
                            )
                    except SimulationError as error:
                        spice_error = str(error)
            elif mode == MODE_FIXED:
                result = analyze_fixed_bias(**values)
                approx = None
                ic_diff = None
                approx_note = None
            elif mode == MODE_EMITTER:
                result = analyze_emitter_bias(**values)
                approx = None
                ic_diff = None
                approx_note = None
            else:
                raise ValidationError("mode", "Unknown circuit mode")
        except ValidationError as error:
            render_mode = mode if mode in MODE_FIELDS else MODE_DIVIDER
            return (
                render_page(
                    form=request.form,
                    mode=render_mode,
                    result=None,
                    approx=None,
                    ic_diff=None,
                    approx_note=None,
                    error_field=error.field,
                    error_message=error.message,
                ),
                400,
            )

        return render_page(
            form=request.form,
            mode=mode,
            result=result,
            approx=approx,
            ic_diff=ic_diff,
            approx_note=approx_note,
            spice=spice,
            spice_rows=spice_rows,
            spice_error=spice_error,
            spice_note=spice_note,
            error_field=None,
            error_message=None,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
