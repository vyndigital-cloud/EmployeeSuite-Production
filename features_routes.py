from flask import Blueprint, render_template, request

features_bp = Blueprint("features", __name__, url_prefix="/features")


@features_bp.route("/welcome")
def welcome():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template("features/welcome.html", shop=shop, host=host)


@features_bp.route("/csv-exports")
def csv_exports():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template("features/csv_exports.html", shop=shop, host=host)


@features_bp.route("/scheduled-reports")
def scheduled_reports():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")
    success = request.args.get("success", "")
    error = request.args.get("error", "")

    return render_template(
        "features/scheduled_reports.html",
        shop=shop,
        host=host,
        success=success,
        error=error,
    )


@features_bp.route("/dashboard")
def comprehensive_dashboard():
    shop = request.args.get("shop", "")
    host = request.args.get("host", "")

    return render_template("features/dashboard.html", shop=shop, host=host)

