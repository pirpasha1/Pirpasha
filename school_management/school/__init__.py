"""School Management System - Flask application factory."""
import os
import secrets
from datetime import date, datetime

from flask import Flask, abort, flash, g, redirect, request, session, url_for

from . import db

TERMS = ["Term 1", "Term 2"]
COMPETENCY_LEVELS = {1: "Beginning", 2: "Developing", 3: "Proficient", 4: "Advanced"}
INDICATOR_GRADES = {"A": "Outstanding", "B": "Very Good", "C": "Good", "D": "Needs Improvement"}
ATTENDANCE_STATUS = {"P": "Present", "A": "Absent", "L": "Leave"}
CHAPTER_STATUS = ["Not Started", "In Progress", "Completed"]
GENDERS = ["Male", "Female", "Other"]
CATEGORIES = ["General", "OBC", "SC", "ST", "EWS", "Other"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


def _secret_key(instance_path):
    path = os.path.join(instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as fh:
            fh.write(secrets.token_hex(32))
    with open(path) as fh:
        return fh.read().strip()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        DATABASE=os.environ.get("SCHOOL_DB", os.path.join(app.instance_path, "school.db")),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _secret_key(app.instance_path)

    db.init_db(app.config["DATABASE"])
    app.teardown_appcontext(db.close_db)

    from .views import academics, attendance, curriculum, exams, main, reports, students
    for module in (main, students, academics, attendance, exams, curriculum, reports):
        app.register_blueprint(module.bp)

    _register_hooks(app)
    return app


PUBLIC_ENDPOINTS = {"main.login", "static"}


def _register_hooks(app):
    @app.before_request
    def load_user_and_check():
        g.user = None
        uid = session.get("user_id")
        if uid:
            g.user = db.query("SELECT * FROM users WHERE id = ? AND active = 1", (uid,), one=True)
            if g.user is None:
                session.clear()
        if request.endpoint not in PUBLIC_ENDPOINTS and g.user is None:
            return redirect(url_for("main.login", next=request.full_path))
        if request.method == "POST" and not app.config.get("CSRF_DISABLED"):
            token = request.form.get("csrf_token")
            if not token or token != session.get("csrf_token"):
                abort(400, "Your session expired. Please go back, refresh the page and try again.")

    @app.context_processor
    def inject_globals():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(16)
        settings = db.get_settings()
        return {
            "csrf_token": lambda: session["csrf_token"],
            "settings": settings,
            "current_user": g.get("user"),
            "is_admin": bool(g.get("user") and g.user["role"] == "admin"),
            "TERMS": TERMS,
            "COMPETENCY_LEVELS": COMPETENCY_LEVELS,
            "INDICATOR_GRADES": INDICATOR_GRADES,
            "ATTENDANCE_STATUS": ATTENDANCE_STATUS,
            "CHAPTER_STATUS": CHAPTER_STATUS,
            "GENDERS": GENDERS,
            "CATEGORIES": CATEGORIES,
            "BLOOD_GROUPS": BLOOD_GROUPS,
            "today": date.today().isoformat(),
        }

    @app.template_filter("dmy")
    def format_date(value):
        """Show ISO dates (2026-04-01) as 01-04-2026, the format staff are used to."""
        if not value:
            return ""
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            return value

    @app.template_filter("num")
    def format_number(value):
        if value is None or value == "":
            return ""
        try:
            f = float(value)
        except (TypeError, ValueError):
            return value
        return str(int(f)) if f == int(f) else f"{f:.1f}"

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def friendly_error(err):
        from flask import render_template
        return render_template("error.html", error=err), err.code


def admin_required():
    """Call at the top of a view to restrict it to administrators."""
    if not g.user or g.user["role"] != "admin":
        flash("Only the administrator can do this.", "error")
        abort(403, "Only the administrator can open this page.")
