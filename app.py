"""
app.py — Flask application entry point.
Handles all HTTP routes; delegates database work to PyMongo service modules.
"""
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

from database      import ping, get_db
from validation    import setup_collections, VALID_STATUSES
from parcel_service import (
    create_parcel, get_all_parcels, get_parcel_by_tracking_id,
    get_parcel_by_id, update_parcel, delete_parcel,
    update_status, get_tracking_history, get_destinations,
    STATUS_TRANSITIONS,
)
from aggregation import dashboard_summary, stats_for_range
from indexing    import list_indexes

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")


# ══════════════════════════════════════════════════════════
#  Startup
# ══════════════════════════════════════════════════════════
with app.app_context():
    try:
        ping()
        setup_collections()
        print("[OK] Connected to MongoDB and collections ready.")
    except Exception as exc:
        print(f"[WARN] Startup warning: {exc}")


# ══════════════════════════════════════════════════════════
#  Pages
# ══════════════════════════════════════════════════════════
@app.route("/")
def dashboard():
    try:
        summary = dashboard_summary()
    except Exception as exc:
        summary = {}
        flash(f"Dashboard data error: {exc}", "error")
    return render_template("dashboard.html", summary=summary)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            parcel = create_parcel(request.form.to_dict())
            flash(f"Parcel registered! Tracking ID: {parcel['trackingId']}", "success")
            return redirect(url_for("register"))
        except Exception as exc:
            flash(f"Error: {exc}", "error")
    return render_template("register.html", cities=_indian_cities())


@app.route("/manage")
def manage():
    status_f = request.args.get("status", "")
    dest_f   = request.args.get("destination", "")
    search   = request.args.get("search", "")
    parcels  = get_all_parcels(status_f, dest_f, search)
    return render_template(
        "manage.html",
        parcels=parcels,
        statuses=VALID_STATUSES,
        destinations=get_destinations(),
        selected_status=status_f,
        selected_dest=dest_f,
        search=search,
    )


@app.route("/track", methods=["GET", "POST"])
def track():
    parcel  = None
    history = []
    tid     = ""
    error   = ""
    # Support GET ?tid= from topbar quick-search
    if request.method == "GET" and request.args.get("tid"):
        tid    = request.args.get("tid", "").strip().upper()
        parcel = get_parcel_by_tracking_id(tid)
        if parcel:
            history = get_tracking_history(tid)
        else:
            error = f"No parcel found with tracking ID: {tid}"
    elif request.method == "POST":
        tid    = request.form.get("trackingId", "").strip().upper()
        parcel = get_parcel_by_tracking_id(tid)
        if parcel:
            history = get_tracking_history(tid)
        else:
            error = f"No parcel found with tracking ID: {tid}"
    return render_template("track.html", parcel=parcel, history=history,
                           tid=tid, error=error)


@app.route("/update-status", methods=["GET", "POST"])
def update_status_page():
    parcel      = None
    history     = []
    transitions = {}
    message     = ""
    error       = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "search":
            tid    = request.form.get("trackingId", "").strip().upper()
            parcel = get_parcel_by_tracking_id(tid)
            if parcel:
                history     = get_tracking_history(tid)
                transitions = STATUS_TRANSITIONS.get(parcel["status"], [])
            else:
                error = f"Parcel {tid} not found."

        elif action == "update":
            tid        = request.form.get("trackingId", "").strip().upper()
            new_status = request.form.get("new_status", "")
            location   = request.form.get("location", "").strip()
            remarks    = request.form.get("remarks", "").strip()
            try:
                parcel      = update_status(tid, new_status, location, remarks)
                history     = get_tracking_history(tid)
                transitions = STATUS_TRANSITIONS.get(parcel["status"], [])
                message     = f"Status updated to '{new_status}' successfully."
            except ValueError as exc:
                error  = str(exc)
                parcel = get_parcel_by_tracking_id(tid)
                if parcel:
                    history     = get_tracking_history(tid)
                    transitions = STATUS_TRANSITIONS.get(parcel["status"], [])

    return render_template(
        "update_status.html",
        parcel=parcel, history=history,
        transitions=transitions, message=message, error=error,
        cities=_indian_cities(),
    )


@app.route("/analytics")
def analytics():
    try:
        from aggregation import (count_by_status, top_destinations,
                                  daily_booking_trends, monthly_booking_trends,
                                  delivered_vs_pending, total_delivery_charges)
        data = {
            "byStatus":       count_by_status(),
            "topDest":        top_destinations(10),
            "daily":          daily_booking_trends(60),
            "monthly":        monthly_booking_trends(),
            "summary":        delivered_vs_pending(),
            "totalCharges":   total_delivery_charges(),
        }
    except Exception as exc:
        data  = {}
        flash(f"Analytics error: {exc}", "error")
    return render_template("analytics.html", data=data)


@app.route("/database-info")
def database_info():
    db       = get_db()
    col_info = []
    for name in ["parcels", "tracking_history"]:
        col  = db[name]
        info = db.command("collStats", name)
        col_info.append({
            "name":       name,
            "count":      info.get("count", 0),
            "size_kb":    round(info.get("size", 0) / 1024, 2),
            "indexes":    list_indexes().get(name, []),
        })

    # Fetch validator info
    validator_info = {}
    for name in ["parcels", "tracking_history"]:
        opts = db.command("listCollections", filter={"name": name})
        docs = list(opts["cursor"]["firstBatch"])
        if docs and "options" in docs[0]:
            validator_info[name] = docs[0]["options"].get("validator", {})
        else:
            validator_info[name] = {}

    return render_template("database_info.html",
                           col_info=col_info,
                           validator_info=validator_info)


# ══════════════════════════════════════════════════════════
#  Edit / Delete — Modal-friendly JSON-compatible endpoints
# ══════════════════════════════════════════════════════════
@app.route("/parcel/<parcel_id>")
def view_parcel(parcel_id):
    parcel = get_parcel_by_id(parcel_id)
    if not parcel:
        flash("Parcel not found.", "error")
        return redirect(url_for("manage"))
    history = get_tracking_history(parcel["trackingId"])
    return render_template("view_parcel.html", parcel=parcel, history=history)


@app.route("/parcel/<parcel_id>/edit", methods=["GET", "POST"])
def edit_parcel(parcel_id):
    parcel = get_parcel_by_id(parcel_id)
    if not parcel:
        flash("Parcel not found.", "error")
        return redirect(url_for("manage"))
    if request.method == "POST":
        try:
            update_parcel(parcel_id, request.form.to_dict())
            flash("Parcel updated successfully.", "success")
            return redirect(url_for("manage"))
        except Exception as exc:
            flash(f"Update error: {exc}", "error")
    return render_template("edit_parcel.html", parcel=parcel, cities=_indian_cities())


@app.route("/parcel/<parcel_id>/delete", methods=["POST"])
def delete_parcel_route(parcel_id):
    if delete_parcel(parcel_id):
        flash("Parcel deleted successfully.", "success")
    else:
        flash("Parcel not found.", "error")
    return redirect(url_for("manage"))


# ══════════════════════════════════════════════════════════
#  API endpoints (used by JavaScript / Chart.js)
# ══════════════════════════════════════════════════════════
@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(dashboard_summary())


@app.route("/api/parcel/<tracking_id>")
def api_parcel(tracking_id):
    parcel = get_parcel_by_tracking_id(tracking_id)
    if not parcel:
        return jsonify({"error": "Not found"}), 404
    return jsonify(parcel)


@app.route("/api/history/<tracking_id>")
def api_history(tracking_id):
    return jsonify(get_tracking_history(tracking_id))


@app.route("/api/indexes")
def api_indexes():
    return jsonify(list_indexes())


@app.route("/api/stats-range")
def api_stats_range():
    try:
        start = datetime.fromisoformat(request.args.get("start", ""))
        end   = datetime.fromisoformat(request.args.get("end", ""))
        return jsonify(stats_for_range(start, end))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ══════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════
def _indian_cities() -> list[str]:
    return [
        "Ahmedabad", "Bengaluru", "Bhopal", "Chennai", "Delhi",
        "Ghaziabad", "Hyderabad", "Indore", "Jaipur", "Kanpur",
        "Kolkata", "Lucknow", "Ludhiana", "Mumbai", "Nagpur",
        "Patna", "Pune", "Surat", "Vadodara", "Visakhapatnam",
    ]


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True", port=5000)
