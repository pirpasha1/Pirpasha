from datetime import date, datetime
from io import BytesIO

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from .. import admin_required, services
from ..db import execute, get_db, query

bp = Blueprint("students", __name__, url_prefix="/students")

FIELDS = ["admission_no", "admission_date", "name", "gender", "dob", "class_id", "roll_no", "father_name",
          "mother_name", "guardian_phone", "email", "address", "category", "religion", "blood_group",
          "mother_tongue", "apaar_id", "previous_school", "status", "leaving_date", "remarks"]

# Excel import columns: (header shown in template, database field, required)
IMPORT_COLUMNS = [
    ("Admission No", "admission_no", True), ("Student Name", "name", True), ("Class", "grade", True),
    ("Section", "section", True), ("Roll No", "roll_no", False), ("Gender", "gender", False),
    ("Date of Birth (DD-MM-YYYY)", "dob", False), ("Admission Date (DD-MM-YYYY)", "admission_date", False),
    ("Father's Name", "father_name", False), ("Mother's Name", "mother_name", False),
    ("Phone", "guardian_phone", False), ("Email", "email", False), ("Address", "address", False),
    ("Category", "category", False), ("Religion", "religion", False), ("Blood Group", "blood_group", False),
    ("Mother Tongue", "mother_tongue", False), ("APAAR ID", "apaar_id", False),
    ("Previous School", "previous_school", False),
]


def next_admission_no():
    rows = query("SELECT admission_no FROM students")
    nums = [int(r["admission_no"]) for r in rows if str(r["admission_no"]).isdigit()]
    return str(max(nums) + 1) if nums else "1001"


def parse_date(value):
    """Accept dates typed or pasted in the formats staff commonly use."""
    if value is None or value == "":
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"'{text}' is not a valid date (use DD-MM-YYYY)")


@bp.route("/")
def list_students():
    class_id = request.args.get("class_id", type=int)
    status = request.args.get("status", "Active")
    gender = request.args.get("gender", "")
    q = request.args.get("q", "").strip()
    sql = """SELECT s.*, c.grade, c.section FROM students s LEFT JOIN classes c ON c.id = s.class_id WHERE 1=1"""
    args = []
    if class_id:
        sql += " AND s.class_id = ?"
        args.append(class_id)
    if status:
        sql += " AND s.status = ?"
        args.append(status)
    if gender:
        sql += " AND s.gender = ?"
        args.append(gender)
    if q:
        sql += " AND (s.name LIKE ? OR s.admission_no LIKE ? OR s.father_name LIKE ? OR s.guardian_phone LIKE ?)"
        args += [f"%{q}%"] * 4
    sql += f" ORDER BY {services.CLASS_ORDER}, s.roll_no IS NULL, s.roll_no, s.name"
    students = query(sql, args)
    return render_template("students/list.html", students=students, classes=services.all_classes(),
                           class_id=class_id, status=status, gender=gender, q=q)


def _form_values():
    data = {f: (request.form.get(f) or "").strip() or None for f in FIELDS}
    data["status"] = data["status"] or "Active"
    errors = []
    if not data["name"]:
        errors.append("Student name is required.")
    if not data["admission_no"]:
        errors.append("Admission number is required.")
    for f in ("roll_no", "class_id"):
        if data[f]:
            try:
                data[f] = int(data[f])
            except ValueError:
                errors.append(f"{f.replace('_', ' ').title()} must be a number.")
    return data, errors


@bp.route("/new", methods=["GET", "POST"])
@bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id=None):
    student = None
    if student_id:
        student = query("SELECT * FROM students WHERE id = ?", (student_id,), one=True)
        if not student:
            abort(404)
    if request.method == "POST":
        data, errors = _form_values()
        dup = query("SELECT id FROM students WHERE admission_no = ? AND id != ?",
                    (data["admission_no"], student_id or 0), one=True)
        if dup:
            errors.append(f"Admission number {data['admission_no']} is already used by another student.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("students/form.html", student=data, classes=services.all_classes(),
                                   student_id=student_id)
        if student_id:
            sets = ", ".join(f"{f} = ?" for f in FIELDS)
            execute(f"UPDATE students SET {sets} WHERE id = ?", [data[f] for f in FIELDS] + [student_id])
            flash(f"Details of {data['name']} updated.", "success")
        else:
            student_id = execute(f"INSERT INTO students ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
                                 [data[f] for f in FIELDS])
            flash(f"{data['name']} admitted successfully (Admission No {data['admission_no']}).", "success")
            if request.form.get("add_another"):
                return redirect(url_for("students.edit_student", class_id=data["class_id"] or ""))
        return redirect(url_for("students.view_student", student_id=student_id))
    if student is None:
        class_id = request.args.get("class_id", type=int)
        roll = None
        if class_id:
            roll = (query("SELECT MAX(roll_no) FROM students WHERE class_id = ? AND status = 'Active'",
                          (class_id,), one=True)[0] or 0) + 1
        student = {"admission_no": next_admission_no(), "admission_date": date.today().isoformat(),
                   "status": "Active", "class_id": class_id, "roll_no": roll}
    return render_template("students/form.html", student=dict(student), classes=services.all_classes(),
                           student_id=student_id)


@bp.route("/<int:student_id>")
def view_student(student_id):
    student = query("""SELECT s.*, c.grade, c.section FROM students s LEFT JOIN classes c ON c.id = s.class_id
                       WHERE s.id = ?""", (student_id,), one=True)
    if not student:
        abort(404)
    card = services.report_card(student_id)
    recent_absences = query("""SELECT date, status FROM attendance WHERE student_id = ? AND status != 'P'
                               ORDER BY date DESC LIMIT 10""", (student_id,))
    return render_template("students/view.html", s=student, card=card, absences=recent_absences)


@bp.route("/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    admin_required()
    s = query("SELECT name FROM students WHERE id = ?", (student_id,), one=True)
    if s:
        execute("DELETE FROM students WHERE id = ?", (student_id,))
        flash(f"Student {s['name']} and all their records were deleted.", "success")
    return redirect(url_for("students.list_students"))


@bp.route("/import", methods=["GET", "POST"])
def import_students():
    admin_required()
    report = None
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename.lower().endswith(".xlsx"):
            flash("Please choose an Excel file (.xlsx). Download the template below if you need one.", "error")
            return redirect(url_for("students.import_students"))
        try:
            wb = load_workbook(upload, data_only=True)
        except Exception:
            flash("Could not read that file. Please save it as an Excel Workbook (.xlsx) and try again.", "error")
            return redirect(url_for("students.import_students"))
        report = _import_rows(wb.active, update=bool(request.form.get("update")))
    return render_template("students/import.html", report=report, columns=IMPORT_COLUMNS)


def _import_rows(ws, update=False):
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"added": 0, "updated": 0, "errors": ["The sheet is empty."]}
    header = [str(h or "").strip().lower() for h in rows[0]]
    col = {}
    for title, field, _req in IMPORT_COLUMNS:
        key = title.lower()
        short = key.split(" (")[0]
        for i, h in enumerate(header):
            if h == key or h == short or h.split(" (")[0] == short:
                col[field] = i
                break
    missing = [t for t, f, req in IMPORT_COLUMNS if req and f not in col]
    if missing:
        return {"added": 0, "updated": 0,
                "errors": [f"Missing column(s): {', '.join(missing)}. Please use the template."]}
    classes = {(str(c["grade"]).strip().lower(), str(c["section"]).strip().lower()): c["id"]
               for c in services.all_classes()}
    db = get_db()
    added = updated = 0
    errors = []
    for n, row in enumerate(rows[1:], start=2):
        if not row or all(v in (None, "") for v in row):
            continue

        def val(field):
            i = col.get(field)
            if i is None or i >= len(row) or row[i] is None:
                return None
            v = row[i]
            if isinstance(v, float) and v == int(v):
                v = int(v)
            return v if isinstance(v, (datetime, date)) else str(v).strip() or None

        try:
            rec = {f: val(f) for _t, f, _r in IMPORT_COLUMNS}
            if not rec["admission_no"] or not rec["name"]:
                raise ValueError("Admission No and Student Name are required")
            key = (str(rec.pop("grade") or "").lower(), str(rec.pop("section") or "").lower())
            if key not in classes:
                raise ValueError(f"class {key[0]}-{key[1].upper()} does not exist. Create it under Classes first")
            rec["class_id"] = classes[key]
            rec["dob"] = parse_date(rec["dob"])
            rec["admission_date"] = parse_date(rec["admission_date"])
            if rec["roll_no"] is not None:
                rec["roll_no"] = int(rec["roll_no"])
            existing = db.execute("SELECT id FROM students WHERE admission_no = ?",
                                  (rec["admission_no"],)).fetchone()
            fields = list(rec)
            if existing:
                if not update:
                    raise ValueError(f"admission no {rec['admission_no']} already exists (skipped)")
                db.execute(f"UPDATE students SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
                           [rec[f] for f in fields] + [existing["id"]])
                updated += 1
            else:
                db.execute(f"INSERT INTO students ({', '.join(fields)}) VALUES ({', '.join('?' * len(fields))})",
                           [rec[f] for f in fields])
                added += 1
        except (ValueError, TypeError) as exc:
            errors.append(f"Row {n}: {exc}")
    db.commit()
    return {"added": added, "updated": updated, "errors": errors}


@bp.route("/import/template")
def import_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    for i, (title, _f, req) in enumerate(IMPORT_COLUMNS, start=1):
        c = ws.cell(row=1, column=i, value=title)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="C00000" if req else "1F4E79")
        ws.column_dimensions[c.column_letter].width = max(14, len(title) + 2)
    ws.append(["1001", "Example Student (delete this row)", "6", "A", 1, "Female", "15-06-2014", "01-04-2026",
               "Father Name", "Mother Name", "9876543210", "", "Village / Town", "General", "", "B+",
               "Hindi", "", ""])
    notes = wb.create_sheet("Instructions")
    for line in ["How to fill this sheet:",
                 "1. Red columns are compulsory: Admission No, Student Name, Class, Section.",
                 "2. Class and Section must match a class already created in the system (e.g. Class 6, Section A).",
                 "3. Dates can be written as DD-MM-YYYY, e.g. 15-06-2014.",
                 "4. Gender: Male / Female / Other.",
                 "5. Delete the example row, keep the heading row, then upload the file."]:
        notes.append([line])
    notes.column_dimensions["A"].width = 100
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="student-import-template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.route("/promote", methods=["GET", "POST"])
def promote():
    admin_required()
    from_id = request.values.get("from_class", type=int)
    if request.method == "POST":
        to_id = request.form.get("to_class", type=int)
        ids = request.form.getlist("student_ids", type=int)
        action = request.form.get("action", "promote")
        if not ids:
            flash("Please tick at least one student.", "error")
        elif action == "left":
            for sid in ids:
                execute("UPDATE students SET status = 'Left', leaving_date = ? WHERE id = ?",
                        (date.today().isoformat(), sid))
            flash(f"{len(ids)} student(s) marked as Left / TC issued.", "success")
        elif action == "passed_out":
            for sid in ids:
                execute("UPDATE students SET status = 'Passed Out', leaving_date = ? WHERE id = ?",
                        (date.today().isoformat(), sid))
            flash(f"{len(ids)} student(s) marked as Passed Out.", "success")
        elif not to_id:
            flash("Please choose the class to move students into.", "error")
        else:
            for sid in ids:
                execute("UPDATE students SET class_id = ? WHERE id = ?", (to_id, sid))
            klass = services.get_class(to_id)
            flash(f"{len(ids)} student(s) moved to Class {services.class_label(klass)}.", "success")
        return redirect(url_for("students.promote", from_class=from_id))
    students = services.class_students(from_id) if from_id else []
    return render_template("students/promote.html", classes=services.all_classes(), from_id=from_id,
                           students=students)
