"""Flask interface for the BJT common-emitter DC bias calculator."""

from flask import Flask, render_template, request

from engineering.bjt import (
    FIELD_LABELS,
    ValidationError,
    analyze,
    analyze_approximate,
    ic_difference_percent,
    validate,
)

FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_FIELDS = ("r1", "r2", "rc", "re")

APPROX_NOTE = (
    "The approximation assumes the active region; it is not meaningful here."
)


def parse_form(form) -> dict[str, float]:
    values = {}
    for field in FIELDS:
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


def create_app() -> Flask:
    app = Flask(__name__)

    app.add_template_filter(lambda value: f"{value:.3f} V", "volts")
    app.add_template_filter(lambda value: f"{value * 1e3:.3f} mA", "milliamps")
    app.add_template_filter(lambda value: f"{value * 1e6:.2f} µA", "microamps")
    app.add_template_filter(lambda value: f"{value / 1e3:.3f} kΩ", "kilohms")

    def render_page(**context):
        return render_template("index.html", **context)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            return render_page(
                form={},
                result=None,
                approx=None,
                ic_diff=None,
                approx_note=None,
                error_field=None,
                error_message=None,
            )

        try:
            bias = validate(parse_form(request.form))
        except ValidationError as error:
            return (
                render_page(
                    form=request.form,
                    result=None,
                    approx=None,
                    ic_diff=None,
                    approx_note=None,
                    error_field=error.field,
                    error_message=error.message,
                ),
                400,
            )

        result = analyze(bias)
        approx = analyze_approximate(bias)
        ic_diff = ic_difference_percent(result.ic, approx.ic)
        approx_note = APPROX_NOTE if result.region != "active" else None
        return render_page(
            form=request.form,
            result=result,
            approx=approx,
            ic_diff=ic_diff,
            approx_note=approx_note,
            error_field=None,
            error_message=None,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
