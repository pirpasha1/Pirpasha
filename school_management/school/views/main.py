import os
import shutil
import sqlite3
import tempfile
from datetime import date, timedelta

from flask import (Blueprint, after_this_request, current_app, flash, g, redirect, render_template, request,
                   send_file, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .. import admin_required, services
from ..db import execute, get_settings, query, save_setting, scalar

bp = Blueprint("main", __name__)

SETTING_FIELDS = [
    ("school_name", "School name", "text"),
    ("school_address", "Address", "text"),
    ("school_phone", "Phone", "text"),
    ("school_email", "Email", "email"),
    ("affiliation_no", "Affiliation / Board No.", "text"),
    ("udise_code", "UDISE Code", "text"),
    ("principal_name", "Principal's name", "text"),
    ("academic_year", "Current academic year (e.g. 2026-27)", "text"),
    ("session_start", "Session starts on", "date"),
    ("session_end", "Session ends on", "date"),
    ("pass_percentage", "Pass percentage per subject", "number"),
]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = query("SELECT * FROM users WHERE username = ? AND active = 1",
                     (request.form.get("username", "").strip().lower(),), one=True)
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            token = session.get("csrf_token")
            session.clear()
            session["user_id"] = user["id"]
            if token:
                session["csrf_token"] = token
            nxt = request.args.get("next") or ""
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("main.dashboard"))
        flash("Wrong username or password. Please try again.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.login"))


@bp.route("/")
def dashboard():
    today = date.today()
    counts = {
        "students": scalar("SELECT COUNT(*) FROM students WHERE status = 'Active'"),
        "boys": scalar("SELECT COUNT(*) FROM students WHERE status = 'Active' AND gender = 'Male'"),
        "girls": scalar("SELECT COUNT(*) FROM students WHERE status = 'Active' AND gender = 'Female'"),
        "teachers": scalar("SELECT COUNT(*) FROM teachers WHERE status = 'Active'"),
        "classes": scalar("SELECT COUNT(*) FROM classes"),
        "subjects": scalar("SELECT COUNT(*) FROM subjects"),
        "chapters": scalar("SELECT COUNT(*) FROM chapters"),
        "competencies": scalar("SELECT COUNT(*) FROM competencies"),
    }
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        stats = services.daily_attendance_stats(d.isoformat())
        week.append({"date": d, "stats": stats})
    classes = services.all_classes()
    todays_by_class = {r["class_id"]: r for r in query(
        """SELECT class_id, SUM(status = 'P') AS p, COUNT(*) AS total FROM attendance
           WHERE date = ? GROUP BY class_id""", (today.isoformat(),))}
    not_marked = [c for c in classes if c["strength"] and c["id"] not in todays_by_class]
    recent = query("""SELECT s.*, c.grade, c.section FROM students s LEFT JOIN classes c ON c.id = s.class_id
                      ORDER BY s.id DESC LIMIT 6""")
    default_pw = False
    if g.user["role"] == "admin":
        admin = query("SELECT password_hash FROM users WHERE username = 'admin'", one=True)
        default_pw = bool(admin and check_password_hash(admin["password_hash"], "admin123"))
    exams = services.exams_for_year()
    return render_template(
        "dashboard.html", counts=counts, week=week, classes=classes, todays_by_class=todays_by_class,
        not_marked=not_marked, recent=recent, today_stats=services.daily_attendance_stats(today.isoformat()),
        syllabus=services.syllabus_completion_overall(), default_pw=default_pw, exams=exams,
        max_strength=max([c["strength"] for c in classes] + [1]),
    )


@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = {"students": [], "teachers": [], "chapters": [], "competencies": []}
    if q:
        like = f"%{q}%"
        results["students"] = query(
            """SELECT s.*, c.grade, c.section FROM students s LEFT JOIN classes c ON c.id = s.class_id
               WHERE s.name LIKE ? OR s.admission_no LIKE ? OR s.father_name LIKE ? OR s.mother_name LIKE ?
                  OR s.guardian_phone LIKE ? OR s.apaar_id LIKE ?
               ORDER BY s.status, s.name LIMIT 100""", (like,) * 6)
        results["teachers"] = query(
            """SELECT * FROM teachers WHERE name LIKE ? OR emp_code LIKE ? OR phone LIKE ? OR email LIKE ?
                  OR qualification LIKE ? OR designation LIKE ? ORDER BY name LIMIT 50""", (like,) * 6)
        results["chapters"] = query(
            """SELECT ch.*, s.name AS subject FROM chapters ch JOIN subjects s ON s.id = ch.subject_id
               WHERE ch.title LIKE ? OR ch.learning_outcomes LIKE ? OR ch.book LIKE ?
               ORDER BY ch.grade, s.name, ch.chapter_no LIMIT 50""", (like,) * 3)
        results["competencies"] = query(
            """SELECT c.*, s.name AS subject FROM competencies c JOIN subjects s ON s.id = c.subject_id
               WHERE c.description LIKE ? OR c.code LIKE ? ORDER BY c.grade, s.name LIMIT 50""", (like,) * 2)
    total = sum(len(v) for v in results.values())
    return render_template("search.html", q=q, results=results, total=total)


@bp.route("/settings", methods=["GET", "POST"])
def settings_page():
    admin_required()
    if request.method == "POST":
        for key, _label, _type in SETTING_FIELDS:
            save_setting(key, request.form.get(key, "").strip())
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings_page"))
    has_students = scalar("SELECT COUNT(*) FROM students") > 0
    return render_template("admin/settings.html", fields=SETTING_FIELDS, values=get_settings(),
                           has_students=has_students)


@bp.route("/users", methods=["GET", "POST"])
def users():
    admin_required()
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not username or len(password) < 6:
            flash("Enter a username and a password of at least 6 characters.", "error")
        elif query("SELECT 1 FROM users WHERE username = ?", (username,), one=True):
            flash("That username is already taken.", "error")
        else:
            execute("INSERT INTO users(username, password_hash, full_name, role, teacher_id) VALUES (?,?,?,?,?)",
                    (username, generate_password_hash(password), request.form.get("full_name", "").strip(),
                     "admin" if request.form.get("role") == "admin" else "teacher",
                     request.form.get("teacher_id") or None))
            flash(f"Login created for '{username}'.", "success")
        return redirect(url_for("main.users"))
    rows = query("""SELECT u.*, t.name AS teacher FROM users u LEFT JOIN teachers t ON t.id = u.teacher_id
                    ORDER BY u.role, u.username""")
    return render_template("admin/users.html", users=rows, teachers=services.all_teachers(True))


@bp.route("/users/<int:user_id>/<action>", methods=["POST"])
def user_action(user_id, action):
    admin_required()
    user = query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        flash("User not found.", "error")
    elif action == "reset":
        password = request.form.get("password", "")
        if len(password) < 6:
            flash("New password must be at least 6 characters.", "error")
        else:
            execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(password), user_id))
            flash(f"Password changed for '{user['username']}'.", "success")
    elif user_id == g.user["id"]:
        flash("You cannot disable or delete your own login.", "error")
    elif action == "toggle":
        execute("UPDATE users SET active = 1 - active WHERE id = ?", (user_id,))
        flash(f"Login '{user['username']}' {'disabled' if user['active'] else 'enabled'}.", "success")
    elif action == "delete":
        execute("DELETE FROM users WHERE id = ?", (user_id,))
        flash(f"Login '{user['username']}' deleted.", "success")
    return redirect(url_for("main.users"))


@bp.route("/account/password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        current = request.form.get("current", "")
        new = request.form.get("new", "")
        if not check_password_hash(g.user["password_hash"], current):
            flash("Your current password is not correct.", "error")
        elif len(new) < 6:
            flash("The new password must be at least 6 characters.", "error")
        elif new != request.form.get("confirm", ""):
            flash("The two new passwords do not match.", "error")
        else:
            execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), g.user["id"]))
            flash("Your password has been changed.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("admin/password.html")


@bp.route("/backup")
def backup():
    admin_required()
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    src = sqlite3.connect(current_app.config["DATABASE"])
    dst = sqlite3.connect(tmp)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    @after_this_request
    def cleanup(response):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return response

    return send_file(tmp, as_attachment=True,
                     download_name=f"school-backup-{date.today().isoformat()}.db")


@bp.route("/restore", methods=["POST"])
def restore():
    admin_required()
    upload = request.files.get("backup")
    if not upload or not upload.filename:
        flash("Please choose a backup file first.", "error")
        return redirect(url_for("main.settings_page"))
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    upload.save(tmp)
    try:
        conn = sqlite3.connect(tmp)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        if not {"students", "users", "settings"} <= tables:
            raise sqlite3.DatabaseError("not a backup of this system")
    except sqlite3.DatabaseError:
        os.remove(tmp)
        flash("That file is not a valid backup from this system.", "error")
        return redirect(url_for("main.settings_page"))
    from ..db import close_db, init_db
    close_db()
    dbpath = current_app.config["DATABASE"]
    shutil.copy(dbpath, dbpath + ".before-restore")
    shutil.move(tmp, dbpath)
    init_db(dbpath)  # adds any tables introduced since the backup was taken
    session.clear()
    flash("Backup restored. Please log in again.", "success")
    return redirect(url_for("main.login"))


@bp.route("/demo-data", methods=["POST"])
def demo_data():
    admin_required()
    if scalar("SELECT COUNT(*) FROM students") > 0:
        flash("Sample data can only be loaded into an empty system.", "error")
    else:
        from ..demo import load_demo
        load_demo()
        flash("Sample data loaded. Explore freely - you can delete it later or start fresh.", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/help")
def help_page():
    return render_template("help.html")
