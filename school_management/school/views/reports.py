"""Reports centre: every report can be downloaded as PDF or Excel."""
from datetime import date

from flask import Blueprint, abort, render_template, request, send_file

from .. import COMPETENCY_LEVELS, TERMS, services
from ..db import get_settings, query
from ..exports import small_table, table_pdf, table_xlsx

bp = Blueprint("reports", __name__, url_prefix="/reports")

PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _dmy(v):
    if not v:
        return ""
    try:
        return date.fromisoformat(str(v)[:10]).strftime("%d-%m-%Y")
    except ValueError:
        return v


def _n(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return int(v) if v == int(v) else round(v, 1)
    return v


def _send(fmt, filename, title, headers, rows, subtitle=None, extra_pdf=None, extra_sheets=None, wide=None):
    settings = get_settings()
    if fmt == "xlsx":
        buf = table_xlsx(settings, title, headers, rows, subtitle, sheets=extra_sheets)
        return send_file(buf, as_attachment=True, download_name=f"{filename}.xlsx", mimetype=XLSX)
    buf = table_pdf(settings, title, headers, [[_pdf_val(v) for v in r] for r in rows], subtitle,
                    extra=extra_pdf, wide=wide)
    return send_file(buf, as_attachment=True, download_name=f"{filename}.pdf", mimetype=PDF)


def _pdf_val(v):
    return "" if v is None else v


@bp.route("/")
def index():
    return render_template("reports/index.html", classes=services.all_classes(), exams=services.exams_for_year(),
                           subjects=services.all_subjects(), month=date.today().strftime("%Y-%m"))


@bp.route("/students")
def students():
    fmt = request.args.get("fmt", "pdf")
    class_id = request.args.get("class_id", type=int)
    status = request.args.get("status", "Active")
    detailed = fmt == "xlsx"
    sql = "SELECT s.*, c.grade, c.section FROM students s LEFT JOIN classes c ON c.id = s.class_id WHERE 1=1"
    args = []
    if class_id:
        sql += " AND s.class_id = ?"
        args.append(class_id)
    if status:
        sql += " AND s.status = ?"
        args.append(status)
    rows = query(sql + f" ORDER BY {services.CLASS_ORDER}, s.roll_no IS NULL, s.roll_no, s.name", args)
    if detailed:
        headers = ["Admission No", "Admission Date", "Name", "Class", "Roll No", "Gender", "Date of Birth",
                   "Father's Name", "Mother's Name", "Phone", "Email", "Address", "Category", "Religion",
                   "Blood Group", "Mother Tongue", "APAAR ID", "Previous School", "Status"]
        data = [[r["admission_no"], _dmy(r["admission_date"]), r["name"],
                 f"{r['grade']}-{r['section']}" if r["grade"] else "", r["roll_no"], r["gender"], _dmy(r["dob"]),
                 r["father_name"], r["mother_name"], r["guardian_phone"], r["email"], r["address"], r["category"],
                 r["religion"], r["blood_group"], r["mother_tongue"], r["apaar_id"], r["previous_school"],
                 r["status"]] for r in rows]
    else:
        headers = ["#", "Adm No", "Name", "Class", "Roll", "Gender", "DOB", "Father's Name", "Phone"]
        data = [[i, r["admission_no"], r["name"], f"{r['grade']}-{r['section']}" if r["grade"] else "",
                 r["roll_no"], r["gender"], _dmy(r["dob"]), r["father_name"], r["guardian_phone"]]
                for i, r in enumerate(rows, start=1)]
    klass = services.get_class(class_id) if class_id else None
    title = f"Student List - Class {services.class_label(klass)}" if klass else "Student List - All Classes"
    boys = sum(1 for r in rows if r["gender"] == "Male")
    girls = sum(1 for r in rows if r["gender"] == "Female")
    sub = f"Total: {len(rows)} (Boys {boys}, Girls {girls}) | Status: {status or 'All'}"
    return _send(fmt, "student-list", title, headers, data, sub, wide=False if not detailed else None)


@bp.route("/teachers")
def teachers():
    fmt = request.args.get("fmt", "pdf")
    rows = services.all_teachers()
    headers = ["Emp Code", "Name", "Gender", "Designation", "Qualification", "Phone", "Email", "Joining Date",
               "Status"]
    data = [[r["emp_code"], r["name"], r["gender"], r["designation"], r["qualification"], r["phone"], r["email"],
             _dmy(r["joining_date"]), r["status"]] for r in rows]
    return _send(fmt, "teacher-list", "Teaching Staff", headers, data, f"Total: {len(rows)}")


@bp.route("/classes")
def classes():
    fmt = request.args.get("fmt", "pdf")
    rows = []
    for c in services.all_classes():
        boys = query("SELECT COUNT(*) FROM students WHERE class_id = ? AND status='Active' AND gender='Male'",
                     (c["id"],), one=True)[0]
        girls = query("SELECT COUNT(*) FROM students WHERE class_id = ? AND status='Active' AND gender='Female'",
                      (c["id"],), one=True)[0]
        subjects = ", ".join(f"{s['name']}{' (' + s['teacher'] + ')' if s['teacher'] else ''}"
                             for s in query("""SELECT s.name, t.name AS teacher FROM class_subjects cs
                                              JOIN subjects s ON s.id = cs.subject_id
                                              LEFT JOIN teachers t ON t.id = cs.teacher_id
                                              WHERE cs.class_id = ? ORDER BY s.name""", (c["id"],)))
        rows.append([services.class_label(c), c["class_teacher"], c["room"], boys, girls, c["strength"], subjects])
    headers = ["Class", "Class Teacher", "Room", "Boys", "Girls", "Total", "Subjects (Teacher)"]
    return _send(fmt, "class-wise-strength", "Class-wise Strength & Subjects", headers, rows, wide=True)


@bp.route("/attendance")
def attendance():
    fmt = request.args.get("fmt", "pdf")
    class_id = request.args.get("class_id", type=int)
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    klass = services.get_class(class_id) if class_id else None
    if not klass:
        abort(404)
    y, m = (int(x) for x in month.split("-"))
    data = services.attendance_register(class_id, y, m)
    headers = ["Roll", "Name"] + [str(d.day) for d in data["dates"]] + ["P", "A", "L", "%"]
    rows = [[r["student"]["roll_no"], r["student"]["name"]] + r["cells"] + [r["P"], r["A"], r["L"], _n(r["pct"])]
            for r in data["rows"]]
    title = f"Attendance Register - Class {services.class_label(klass)} - {data['month_name']}"
    sub = f"Working days: {data['working_days']} | P = Present, A = Absent, L = Leave"
    return _send(fmt, f"attendance-{klass['grade']}{klass['section']}-{month}", title, headers, rows, sub, wide=True)


@bp.route("/attendance-summary")
def attendance_summary():
    """Session-to-date attendance percentage for every student of a class (or all classes)."""
    fmt = request.args.get("fmt", "pdf")
    class_id = request.args.get("class_id", type=int)
    below = request.args.get("below", type=float)
    classes = [services.get_class(class_id)] if class_id else services.all_classes()
    headers = ["Class", "Roll", "Adm No", "Name", "Present", "Absent", "Leave", "Days Marked", "%"]
    rows = []
    for c in classes:
        if c is None:
            abort(404)
        for s in services.class_students(c["id"]):
            a = services.attendance_summary(s["id"])
            if below is not None and (a["pct"] is None or a["pct"] >= below):
                continue
            rows.append([services.class_label(c), s["roll_no"], s["admission_no"], s["name"], a["present"],
                         a["absent"], a["leave"], a["total"], _n(a["pct"])])
    st = get_settings()
    title = "Attendance Summary" + (f" - Students below {below:g}%" if below is not None else "")
    sub = f"Session {_dmy(st['session_start'])} to {_dmy(st['session_end'])}"
    return _send(fmt, "attendance-summary", title, headers, rows, sub)


@bp.route("/marks")
def marks():
    fmt = request.args.get("fmt", "pdf")
    exam_id = request.args.get("exam_id", type=int)
    class_id = request.args.get("class_id", type=int)
    klass = services.get_class(class_id) if class_id else None
    if not klass or not exam_id:
        abort(404)
    data = services.marksheet(exam_id, class_id)
    exam = data["exam"]
    headers = ["Roll", "Name"] + [s["name"] for s in data["subjects"]] + ["Total", "%", "Grade", "Rank", "Result"]
    rows = [[r["student"]["roll_no"], r["student"]["name"]] + [_n(c) for c in r["cells"]] +
            [f"{_n(r['total'])}/{_n(r['max_total'])}" if r["max_total"] else "", _n(r["pct"]), r["grade"],
             r["rank"], r["result"]] for r in data["rows"]]
    stat_headers = ["Subject", "Appeared", "Passed", "Average", "Highest", "Lowest"]
    stat_rows = [[st["subject"]["name"], st["appeared"], st["passed"], _n(st["avg"]), _n(st["high"]), _n(st["low"])]
                 for st in data["subject_stats"]]
    title = f"Mark Sheet - {exam['name']} - Class {services.class_label(klass)}"
    sub = f"Maximum marks per subject: {_n(exam['max_marks'])} | Academic Year {exam['academic_year']}"
    return _send(fmt, f"marksheet-{klass['grade']}{klass['section']}-{exam['name'].replace(' ', '_')}",
                 title, headers, rows, sub, wide=True,
                 extra_pdf=[small_table(stat_headers, stat_rows)],
                 extra_sheets=[("Subject Analysis", stat_headers, stat_rows)])


@bp.route("/result-analysis")
def result_analysis():
    fmt = request.args.get("fmt", "pdf")
    exam_id = request.args.get("exam_id", type=int)
    exam = query("SELECT * FROM exams WHERE id = ?", (exam_id,), one=True) if exam_id else None
    if not exam:
        abort(404)
    data = services.result_analysis(exam_id)
    grades = [g for _, g in services.GRADE_SCALE]
    headers = ["Class", "Strength", "Appeared", "Passed", "Pass %", "Class Avg %", "Topper", "Topper %"] + grades
    rows = [[services.class_label(r["class"]), r["strength"], r["appeared"], r["passed"], _n(r["pass_pct"]),
             _n(r["avg_pct"]), r["top"]["student"]["name"] if r["top"] else "",
             _n(r["top"]["pct"]) if r["top"] else ""] + [r["grades"][g] for g in grades] for r in data]
    return _send(fmt, f"result-analysis-{exam['name'].replace(' ', '_')}", f"Result Analysis - {exam['name']}",
                 headers, rows, f"Academic Year {exam['academic_year']}", wide=True)


@bp.route("/chapters")
def chapters():
    fmt = request.args.get("fmt", "pdf")
    class_id = request.args.get("class_id", type=int)
    klass = services.get_class(class_id) if class_id else None
    if not klass:
        abort(404)
    data = services.chapter_progress(class_id, request.args.get("subject_id", type=int))
    headers = ["Subject", "Ch. No", "Chapter Title", "Status", "Started", "Completed", "Periods (Planned/Taken)",
               "Teacher", "Remarks"]
    rows = [[r["subject"], r["chapter_no"], r["title"], r["status"] or "Not Started", _dmy(r["start_date"]),
             _dmy(r["end_date"]), f"{r['planned_periods'] or '-'} / {r['periods_taken'] or '-'}", r["teacher"],
             r["remarks"]] for r in data["rows"]]
    s_headers = ["Subject", "Total Chapters", "Completed", "In Progress", "Not Started", "Completion %"]
    s_rows = [[k, v["total"], v["Completed"], v["In Progress"], v["Not Started"], v["pct"]]
              for k, v in data["summary"].items()]
    return _send(fmt, f"ncert-chapter-progress-{klass['grade']}{klass['section']}",
                 f"NCERT Chapter-wise Progress - Class {services.class_label(klass)}", headers, rows,
                 f"Academic Year {services.academic_year()}", wide=True,
                 extra_pdf=[small_table(s_headers, s_rows)], extra_sheets=[("Summary", s_headers, s_rows)])


@bp.route("/chapter-list")
def chapter_list():
    fmt = request.args.get("fmt", "pdf")
    grade = request.args.get("grade") or None
    sql = """SELECT ch.*, s.name AS subject FROM chapters ch JOIN subjects s ON s.id = ch.subject_id"""
    args = []
    if grade:
        sql += " WHERE ch.grade = ?"
        args.append(grade)
    rows = query(sql + " ORDER BY CAST(ch.grade AS INTEGER), ch.grade, s.name, ch.chapter_no", args)
    headers = ["Class", "Subject", "Ch. No", "Chapter Title", "Book", "Learning Outcomes", "Planned Periods"]
    data = [[r["grade"], r["subject"], r["chapter_no"], r["title"], r["book"], r["learning_outcomes"],
             r["planned_periods"]] for r in rows]
    return _send(fmt, "ncert-chapters", f"NCERT Chapters{' - Class ' + grade if grade else ''}", headers, data,
                 wide=True)


@bp.route("/competencies")
def competencies():
    fmt = request.args.get("fmt", "pdf")
    class_id = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    term = request.args.get("term") or TERMS[0]
    klass = services.get_class(class_id) if class_id else None
    subject = query("SELECT * FROM subjects WHERE id = ?", (subject_id,), one=True) if subject_id else None
    if not klass or not subject:
        abort(404)
    data = services.competency_matrix(class_id, subject_id, term)
    comps = data["competencies"]
    headers = ["Roll", "Name"] + [c["code"] or f"LO{i}" for i, c in enumerate(comps, start=1)]
    short = {1: "B", 2: "D", 3: "P", 4: "A"}
    rows = [[s["roll_no"], s["name"]] + [short.get(data["levels"].get((s["id"], c["id"])), "") for c in comps]
            for s in data["students"]]
    s_headers = ["Code", "Learning Outcome"] + list(COMPETENCY_LEVELS.values()) + ["Assessed", "Proficient+ %"]
    s_rows = [[x["competency"]["code"] or f"LO{i}", x["competency"]["description"]] +
              [x["counts"][k] for k in COMPETENCY_LEVELS] + [x["assessed"], _n(x["achieved_pct"])]
              for i, x in enumerate(data["summary"], start=1)]
    title = f"Learning Outcomes - {subject['name']} - Class {services.class_label(klass)} - {term}"
    sub = "B = Beginning, D = Developing, P = Proficient, A = Advanced"
    return _send(fmt, f"competencies-{klass['grade']}{klass['section']}-{subject['name'].replace(' ', '_')}",
                 title, headers, rows, sub, extra_pdf=[small_table(s_headers, s_rows)],
                 extra_sheets=[("Outcome Summary", s_headers, s_rows)], wide=True)


@bp.route("/indicators")
def indicators():
    fmt = request.args.get("fmt", "pdf")
    class_id = request.args.get("class_id", type=int)
    term = request.args.get("term") or TERMS[0]
    klass = services.get_class(class_id) if class_id else None
    if not klass:
        abort(404)
    data = services.indicator_matrix(class_id, term)
    headers = ["Roll", "Name"] + [i["name"] for i in data["indicators"]]
    rows = [[s["roll_no"], s["name"]] + [data["grades"].get((s["id"], i["id"]), "") for i in data["indicators"]]
            for s in data["students"]]
    return _send(fmt, f"indicators-{klass['grade']}{klass['section']}",
                 f"Assessment Indicators - Class {services.class_label(klass)} - {term}", headers, rows,
                 "A = Outstanding, B = Very Good, C = Good, D = Needs Improvement", wide=True)
