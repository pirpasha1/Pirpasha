"""Classes, subjects and teachers."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .. import admin_required, services
from ..db import execute, query

bp = Blueprint("academics", __name__)

TEACHER_FIELDS = ["emp_code", "name", "gender", "dob", "phone", "email", "qualification", "designation",
                  "joining_date", "address", "status"]


# ---------------------------------------------------------------- classes

@bp.route("/classes", methods=["GET", "POST"])
def classes():
    if request.method == "POST":
        admin_required()
        grade = request.form.get("grade", "").strip()
        sections = [s.strip().upper() for s in request.form.get("section", "A").split(",") if s.strip()]
        if not grade or not sections:
            flash("Please enter the class (e.g. 6) and section (e.g. A).", "error")
        else:
            made = []
            for sec in sections:
                if query("SELECT 1 FROM classes WHERE grade = ? AND section = ?", (grade, sec), one=True):
                    flash(f"Class {grade}-{sec} already exists.", "error")
                    continue
                cid = execute("INSERT INTO classes(grade, section, class_teacher_id, room) VALUES (?,?,?,?)",
                              (grade, sec, request.form.get("class_teacher_id") or None,
                               request.form.get("room", "").strip() or None))
                if request.form.get("all_subjects"):
                    for s in services.all_subjects():
                        execute("INSERT OR IGNORE INTO class_subjects(class_id, subject_id) VALUES (?,?)",
                                (cid, s["id"]))
                made.append(f"{grade}-{sec}")
            if made:
                flash(f"Class {', '.join(made)} created.", "success")
        return redirect(url_for("academics.classes"))
    return render_template("academics/classes.html", classes=services.all_classes(),
                           teachers=services.all_teachers(True))


@bp.route("/classes/<int:class_id>", methods=["GET", "POST"])
def class_detail(class_id):
    klass = services.get_class(class_id)
    if not klass:
        abort(404)
    if request.method == "POST":
        admin_required()
        action = request.form.get("action")
        if action == "update":
            grade = request.form.get("grade", "").strip() or klass["grade"]
            section = request.form.get("section", "").strip().upper() or klass["section"]
            clash = query("SELECT 1 FROM classes WHERE grade = ? AND section = ? AND id != ?",
                          (grade, section, class_id), one=True)
            if clash:
                flash(f"Class {grade}-{section} already exists.", "error")
            else:
                execute("UPDATE classes SET grade = ?, section = ?, class_teacher_id = ?, room = ? WHERE id = ?",
                        (grade, section, request.form.get("class_teacher_id") or None,
                         request.form.get("room", "").strip() or None, class_id))
                flash("Class details saved.", "success")
        elif action == "add_subject":
            sid = request.form.get("subject_id", type=int)
            if sid:
                execute("INSERT OR IGNORE INTO class_subjects(class_id, subject_id, teacher_id) VALUES (?,?,?)",
                        (class_id, sid, request.form.get("teacher_id") or None))
                flash("Subject added to class.", "success")
        elif action == "update_subjects":
            for cs in query("SELECT id FROM class_subjects WHERE class_id = ?", (class_id,)):
                execute("UPDATE class_subjects SET teacher_id = ? WHERE id = ?",
                        (request.form.get(f"teacher_{cs['id']}") or None, cs["id"]))
            flash("Subject teachers saved.", "success")
        elif action == "remove_subject":
            execute("DELETE FROM class_subjects WHERE id = ? AND class_id = ?",
                    (request.form.get("cs_id", type=int), class_id))
            flash("Subject removed from class (marks already entered are kept).", "success")
        elif action == "renumber":
            for i, s in enumerate(query("SELECT id FROM students WHERE class_id = ? AND status = 'Active' "
                                        "ORDER BY name", (class_id,)), start=1):
                execute("UPDATE students SET roll_no = ? WHERE id = ?", (i, s["id"]))
            flash("Roll numbers re-assigned in alphabetical order.", "success")
        elif action == "delete":
            if services.class_students(class_id, active_only=False):
                flash("This class still has students. Move them to another class first.", "error")
            else:
                execute("DELETE FROM classes WHERE id = ?", (class_id,))
                flash(f"Class {services.class_label(klass)} deleted.", "success")
                return redirect(url_for("academics.classes"))
        return redirect(url_for("academics.class_detail", class_id=class_id))
    mapped = query("""SELECT cs.id AS cs_id, cs.teacher_id, s.* FROM class_subjects cs
                      JOIN subjects s ON s.id = cs.subject_id WHERE cs.class_id = ? ORDER BY s.name""", (class_id,))
    students = services.class_students(class_id)
    return render_template("academics/class_detail.html", klass=klass, mapped=mapped, students=students,
                           subjects=services.all_subjects(), teachers=services.all_teachers(True),
                           boys=sum(1 for s in students if s["gender"] == "Male"),
                           girls=sum(1 for s in students if s["gender"] == "Female"))


# --------------------------------------------------------------- subjects

@bp.route("/subjects", methods=["GET", "POST"])
def subjects():
    if request.method == "POST":
        admin_required()
        action = request.form.get("action", "add")
        sid = request.form.get("subject_id", type=int)
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip() or None
        if action == "delete" and sid:
            execute("DELETE FROM subjects WHERE id = ?", (sid,))
            flash("Subject deleted.", "success")
        elif not name:
            flash("Please enter the subject name.", "error")
        elif query("SELECT 1 FROM subjects WHERE name = ? AND id != ?", (name, sid or 0), one=True):
            flash(f"Subject '{name}' already exists.", "error")
        elif action == "update" and sid:
            execute("UPDATE subjects SET name = ?, code = ? WHERE id = ?", (name, code, sid))
            flash("Subject updated.", "success")
        else:
            execute("INSERT INTO subjects(name, code) VALUES (?, ?)", (name, code))
            flash(f"Subject '{name}' added.", "success")
        return redirect(url_for("academics.subjects"))
    rows = query("""SELECT s.*,
                    (SELECT COUNT(*) FROM class_subjects cs WHERE cs.subject_id = s.id) AS classes,
                    (SELECT COUNT(*) FROM chapters ch WHERE ch.subject_id = s.id) AS chapters,
                    (SELECT COUNT(*) FROM competencies c WHERE c.subject_id = s.id) AS competencies
                    FROM subjects s ORDER BY s.name""")
    return render_template("academics/subjects.html", subjects=rows)


# --------------------------------------------------------------- teachers

@bp.route("/teachers")
def teachers():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "Active")
    sql = "SELECT * FROM teachers WHERE 1=1"
    args = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if q:
        sql += " AND (name LIKE ? OR emp_code LIKE ? OR phone LIKE ? OR qualification LIKE ?)"
        args += [f"%{q}%"] * 4
    rows = query(sql + " ORDER BY name", args)
    loads = {r["teacher_id"]: r for r in query(
        """SELECT cs.teacher_id, COUNT(*) AS n,
                  GROUP_CONCAT(s.name || ' (' || c.grade || '-' || c.section || ')', ', ') AS detail
           FROM class_subjects cs JOIN subjects s ON s.id = cs.subject_id JOIN classes c ON c.id = cs.class_id
           WHERE cs.teacher_id IS NOT NULL GROUP BY cs.teacher_id""")}
    return render_template("academics/teachers.html", teachers=rows, loads=loads, q=q, status=status)


@bp.route("/teachers/new", methods=["GET", "POST"])
@bp.route("/teachers/<int:teacher_id>/edit", methods=["GET", "POST"])
def edit_teacher(teacher_id=None):
    admin_required()
    teacher = query("SELECT * FROM teachers WHERE id = ?", (teacher_id,), one=True) if teacher_id else None
    if teacher_id and not teacher:
        abort(404)
    if request.method == "POST":
        data = {f: (request.form.get(f) or "").strip() or None for f in TEACHER_FIELDS}
        data["status"] = data["status"] or "Active"
        errors = []
        if not data["name"]:
            errors.append("Teacher name is required.")
        if data["emp_code"] and query("SELECT 1 FROM teachers WHERE emp_code = ? AND id != ?",
                                      (data["emp_code"], teacher_id or 0), one=True):
            errors.append(f"Employee code {data['emp_code']} is already used.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("academics/teacher_form.html", teacher=data, teacher_id=teacher_id)
        if teacher_id:
            execute(f"UPDATE teachers SET {', '.join(f + ' = ?' for f in TEACHER_FIELDS)} WHERE id = ?",
                    [data[f] for f in TEACHER_FIELDS] + [teacher_id])
            flash("Teacher details updated.", "success")
        else:
            teacher_id = execute(f"INSERT INTO teachers ({', '.join(TEACHER_FIELDS)}) "
                                 f"VALUES ({', '.join('?' * len(TEACHER_FIELDS))})", [data[f] for f in TEACHER_FIELDS])
            flash(f"Teacher {data['name']} added.", "success")
        return redirect(url_for("academics.view_teacher", teacher_id=teacher_id))
    return render_template("academics/teacher_form.html", teacher=teacher or {"status": "Active"},
                           teacher_id=teacher_id)


@bp.route("/teachers/<int:teacher_id>")
def view_teacher(teacher_id):
    t = query("SELECT * FROM teachers WHERE id = ?", (teacher_id,), one=True)
    if not t:
        abort(404)
    classes_taught = query("""SELECT s.name AS subject, c.id AS class_id, c.grade, c.section FROM class_subjects cs
                              JOIN subjects s ON s.id = cs.subject_id JOIN classes c ON c.id = cs.class_id
                              WHERE cs.teacher_id = ? ORDER BY c.grade, c.section""", (teacher_id,))
    class_teacher_of = query("SELECT * FROM classes WHERE class_teacher_id = ?", (teacher_id,))
    login = query("SELECT username FROM users WHERE teacher_id = ?", (teacher_id,), one=True)
    return render_template("academics/teacher_view.html", t=t, classes_taught=classes_taught,
                           class_teacher_of=class_teacher_of, login=login)


@bp.route("/teachers/<int:teacher_id>/delete", methods=["POST"])
def delete_teacher(teacher_id):
    admin_required()
    t = query("SELECT name FROM teachers WHERE id = ?", (teacher_id,), one=True)
    if t:
        execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
        flash(f"Teacher {t['name']} deleted.", "success")
    return redirect(url_for("academics.teachers"))
