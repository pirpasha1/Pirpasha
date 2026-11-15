"""NCERT chapters, chapter progress, learning outcomes / competencies and assessment indicators."""
from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from .. import CHAPTER_STATUS, INDICATOR_GRADES, TERMS, admin_required, services
from ..db import execute, get_db, query
from .students import parse_date

bp = Blueprint("curriculum", __name__)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --------------------------------------------------------------- chapters

@bp.route("/chapters", methods=["GET", "POST"])
def chapters():
    grade = request.values.get("grade", "")
    subject_id = request.values.get("subject_id", type=int)
    if request.method == "POST":
        action = request.form.get("action", "add")
        cid = request.form.get("chapter_id", type=int)
        if action == "delete" and cid:
            admin_required()
            execute("DELETE FROM chapters WHERE id = ?", (cid,))
            flash("Chapter deleted.", "success")
        else:
            f = request.form
            g_, sid = f.get("grade", "").strip(), f.get("subject_id", type=int)
            no, title = f.get("chapter_no", type=int), f.get("title", "").strip()
            if not (g_ and sid and no and title):
                flash("Class, subject, chapter number and chapter title are all required.", "error")
            elif query("SELECT 1 FROM chapters WHERE grade=? AND subject_id=? AND chapter_no=? AND id != ?",
                       (g_, sid, no, cid or 0), one=True):
                flash(f"Chapter {no} already exists for this class and subject.", "error")
            else:
                vals = (g_, sid, no, title, f.get("book", "").strip() or None,
                        f.get("learning_outcomes", "").strip() or None, f.get("planned_periods", type=int))
                if action == "update" and cid:
                    execute("""UPDATE chapters SET grade=?, subject_id=?, chapter_no=?, title=?, book=?,
                               learning_outcomes=?, planned_periods=? WHERE id=?""", vals + (cid,))
                    flash("Chapter updated.", "success")
                else:
                    execute("""INSERT INTO chapters(grade, subject_id, chapter_no, title, book, learning_outcomes,
                               planned_periods) VALUES (?,?,?,?,?,?,?)""", vals)
                    flash(f"Chapter {no}: {title} added.", "success")
                grade, subject_id = g_, sid
        return redirect(url_for("curriculum.chapters", grade=grade, subject_id=subject_id or ""))
    sql = """SELECT ch.*, s.name AS subject,
             (SELECT COUNT(*) FROM competencies c WHERE c.chapter_id = ch.id) AS comp_count
             FROM chapters ch JOIN subjects s ON s.id = ch.subject_id WHERE 1=1"""
    args = []
    if grade:
        sql += " AND ch.grade = ?"
        args.append(grade)
    if subject_id:
        sql += " AND ch.subject_id = ?"
        args.append(subject_id)
    rows = query(sql + " ORDER BY CAST(ch.grade AS INTEGER), ch.grade, s.name, ch.chapter_no", args)
    edit = None
    if request.args.get("edit", type=int):
        edit = query("SELECT * FROM chapters WHERE id = ?", (request.args.get("edit", type=int),), one=True)
    next_no = (max([r["chapter_no"] for r in rows]) + 1) if rows and grade and subject_id else 1
    return render_template("curriculum/chapters.html", chapters=rows, grade=grade, subject_id=subject_id,
                           grades=services.grades_list(), subjects=services.all_subjects(), edit=edit,
                           next_no=next_no)


CHAPTER_COLUMNS = ["Class", "Subject", "Chapter No", "Chapter Title", "Book Name", "Learning Outcomes",
                   "Planned Periods"]


@bp.route("/chapters/template")
def chapters_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "Chapters"
    for i, h in enumerate(CHAPTER_COLUMNS, start=1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="C00000" if i <= 4 else "1F4E79")
        ws.column_dimensions[c.column_letter].width = 40 if i in (4, 6) else 16
    ws.append(["6", "Mathematics", 1, "Patterns in Mathematics", "Ganita Prakash",
               "Identifies and extends patterns in numbers and shapes; One outcome per line or separated by ;",
               12])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="ncert-chapters-template.xlsx", mimetype=XLSX)


@bp.route("/chapters/import", methods=["POST"])
def chapters_import():
    admin_required()
    upload = request.files.get("file")
    if not upload or not upload.filename.lower().endswith(".xlsx"):
        flash("Please choose an Excel (.xlsx) file.", "error")
        return redirect(url_for("curriculum.chapters"))
    try:
        rows = list(load_workbook(upload, data_only=True).active.iter_rows(values_only=True))
    except Exception:
        flash("Could not read that Excel file.", "error")
        return redirect(url_for("curriculum.chapters"))
    subjects = {s["name"].lower(): s["id"] for s in services.all_subjects()}
    db = get_db()
    added, errors = 0, []
    for n, row in enumerate(rows[1:], start=2):
        if not row or all(v in (None, "") for v in row):
            continue
        row = list(row) + [None] * 7
        grade = str(int(row[0]) if isinstance(row[0], float) else row[0] or "").strip()
        subject = str(row[1] or "").strip()
        title = str(row[3] or "").strip()
        try:
            no = int(row[2])
        except (TypeError, ValueError):
            errors.append(f"Row {n}: chapter number missing or not a number")
            continue
        if not (grade and subject and title):
            errors.append(f"Row {n}: Class, Subject and Chapter Title are required")
            continue
        if subject.lower() not in subjects:
            subjects[subject.lower()] = db.execute("INSERT INTO subjects(name) VALUES (?)", (subject,)).lastrowid
        try:
            planned = int(row[6]) if row[6] not in (None, "") else None
        except (TypeError, ValueError):
            planned = None
        db.execute("""INSERT INTO chapters(grade, subject_id, chapter_no, title, book, learning_outcomes,
                      planned_periods) VALUES (?,?,?,?,?,?,?)
                      ON CONFLICT(grade, subject_id, chapter_no) DO UPDATE SET title=excluded.title,
                      book=excluded.book, learning_outcomes=excluded.learning_outcomes,
                      planned_periods=excluded.planned_periods""",
                   (grade, subjects[subject.lower()], no, title, row[4], row[5], planned))
        added += 1
    db.commit()
    flash(f"{added} chapter(s) imported or updated.", "success")
    for e in errors[:20]:
        flash(e, "error")
    return redirect(url_for("curriculum.chapters"))


@bp.route("/chapters/progress", methods=["GET", "POST"])
def chapter_progress():
    class_id = request.values.get("class_id", type=int)
    subject_id = request.values.get("subject_id", type=int)
    if request.method == "POST" and class_id:
        db = get_db()
        year = services.academic_year()
        errors = []
        for ch in services.chapter_progress(class_id, subject_id)["rows"]:
            k = ch["id"]
            status = request.form.get(f"status_{k}") or "Not Started"
            if status not in CHAPTER_STATUS:
                status = "Not Started"
            try:
                start = parse_date(request.form.get(f"start_{k}"))
                end = parse_date(request.form.get(f"end_{k}"))
            except ValueError as exc:
                errors.append(f"Chapter {ch['chapter_no']}: {exc}")
                continue
            periods = request.form.get(f"periods_{k}", type=int)
            db.execute("""INSERT INTO chapter_progress(class_id, chapter_id, academic_year, status, teacher_id,
                          start_date, end_date, periods_taken, remarks) VALUES (?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(class_id, chapter_id, academic_year) DO UPDATE SET status=excluded.status,
                          teacher_id=excluded.teacher_id, start_date=excluded.start_date, end_date=excluded.end_date,
                          periods_taken=excluded.periods_taken, remarks=excluded.remarks""",
                       (class_id, k, year, status, request.form.get(f"teacher_{k}") or None, start, end, periods,
                        (request.form.get(f"remarks_{k}") or "").strip() or None))
        db.commit()
        for e in errors:
            flash(e, "error")
        flash("Chapter progress saved.", "success")
        return redirect(url_for("curriculum.chapter_progress", class_id=class_id, subject_id=subject_id or ""))
    data = services.chapter_progress(class_id, subject_id) if class_id else None
    subjects = services.class_subjects(class_id) if class_id else []
    return render_template("curriculum/progress.html", classes=services.all_classes(), class_id=class_id,
                           subject_id=subject_id, subjects=subjects, data=data,
                           teachers=services.all_teachers(True))


# ----------------------------------------- learning outcomes / competencies

@bp.route("/competencies", methods=["GET", "POST"])
def competencies():
    grade = request.values.get("grade", "")
    subject_id = request.values.get("subject_id", type=int)
    if request.method == "POST":
        action = request.form.get("action", "add")
        cid = request.form.get("competency_id", type=int)
        if action == "delete" and cid:
            admin_required()
            execute("DELETE FROM competencies WHERE id = ?", (cid,))
            flash("Learning outcome deleted.", "success")
        else:
            f = request.form
            g_, sid, desc = f.get("grade", "").strip(), f.get("subject_id", type=int), f.get("description", "").strip()
            if not (g_ and sid and desc):
                flash("Class, subject and the learning outcome text are required.", "error")
            else:
                vals = (f.get("code", "").strip() or None, desc, g_, sid, f.get("chapter_id", type=int),
                        f.get("domain", "").strip() or None)
                if action == "update" and cid:
                    execute("UPDATE competencies SET code=?, description=?, grade=?, subject_id=?, chapter_id=?, "
                            "domain=? WHERE id=?", vals + (cid,))
                    flash("Learning outcome updated.", "success")
                else:
                    execute("INSERT INTO competencies(code, description, grade, subject_id, chapter_id, domain) "
                            "VALUES (?,?,?,?,?,?)", vals)
                    flash("Learning outcome added.", "success")
                grade, subject_id = g_, sid
        return redirect(url_for("curriculum.competencies", grade=grade, subject_id=subject_id or ""))
    sql = """SELECT c.*, s.name AS subject, ch.chapter_no, ch.title AS chapter FROM competencies c
             JOIN subjects s ON s.id = c.subject_id LEFT JOIN chapters ch ON ch.id = c.chapter_id WHERE 1=1"""
    args = []
    if grade:
        sql += " AND c.grade = ?"
        args.append(grade)
    if subject_id:
        sql += " AND c.subject_id = ?"
        args.append(subject_id)
    rows = query(sql + " ORDER BY CAST(c.grade AS INTEGER), c.grade, s.name, ch.chapter_no, c.code, c.id", args)
    chapters = []
    if grade and subject_id:
        chapters = query("SELECT * FROM chapters WHERE grade = ? AND subject_id = ? ORDER BY chapter_no",
                         (grade, subject_id))
    edit = None
    if request.args.get("edit", type=int):
        edit = query("SELECT * FROM competencies WHERE id = ?", (request.args.get("edit", type=int),), one=True)
        if edit:
            chapters = query("SELECT * FROM chapters WHERE grade = ? AND subject_id = ? ORDER BY chapter_no",
                             (edit["grade"], edit["subject_id"]))
    return render_template("curriculum/competencies.html", rows=rows, grade=grade, subject_id=subject_id,
                           grades=services.grades_list(), subjects=services.all_subjects(), chapters=chapters,
                           edit=edit)


@bp.route("/competencies/assess", methods=["GET", "POST"])
def assess_competencies():
    class_id = request.values.get("class_id", type=int)
    subject_id = request.values.get("subject_id", type=int)
    term = request.values.get("term") or TERMS[0]
    year = services.academic_year()
    if request.method == "POST" and class_id and subject_id:
        data = services.competency_matrix(class_id, subject_id, term)
        db = get_db()
        for s in data["students"]:
            for c in data["competencies"]:
                lvl = request.form.get(f"l_{s['id']}_{c['id']}", type=int)
                if lvl in (1, 2, 3, 4):
                    db.execute("""INSERT INTO competency_assessments(student_id, competency_id, academic_year, term,
                                  level) VALUES (?,?,?,?,?) ON CONFLICT(student_id, competency_id, academic_year, term)
                                  DO UPDATE SET level = excluded.level""", (s["id"], c["id"], year, term, lvl))
                else:
                    db.execute("""DELETE FROM competency_assessments WHERE student_id=? AND competency_id=?
                                  AND academic_year=? AND term=?""", (s["id"], c["id"], year, term))
        db.commit()
        flash("Competency levels saved.", "success")
        return redirect(url_for("curriculum.assess_competencies", class_id=class_id, subject_id=subject_id,
                                term=term))
    data = services.competency_matrix(class_id, subject_id, term) if class_id and subject_id else None
    return render_template("curriculum/assess_competencies.html", classes=services.all_classes(),
                           class_id=class_id, subject_id=subject_id, term=term, data=data,
                           subjects=services.class_subjects(class_id) if class_id else [],
                           klass=services.get_class(class_id) if class_id else None)


@bp.route("/competencies/report")
def competency_report():
    class_id = request.args.get("class_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    term = request.args.get("term") or TERMS[0]
    data = services.competency_matrix(class_id, subject_id, term) if class_id and subject_id else None
    return render_template("curriculum/competency_report.html", classes=services.all_classes(),
                           class_id=class_id, subject_id=subject_id, term=term, data=data,
                           subjects=services.class_subjects(class_id) if class_id else [])


# ---------------------------------------------------------- indicators

@bp.route("/indicators", methods=["GET", "POST"])
def indicators():
    if request.method == "POST":
        admin_required()
        action = request.form.get("action", "add")
        iid = request.form.get("indicator_id", type=int)
        if action == "delete" and iid:
            execute("DELETE FROM indicators WHERE id = ?", (iid,))
            flash("Indicator deleted.", "success")
        else:
            name = request.form.get("name", "").strip()
            area = request.form.get("area", "").strip() or "Co-Scholastic"
            if not name:
                flash("Please enter the indicator name.", "error")
            else:
                vals = (name, area, request.form.get("description", "").strip() or None,
                        request.form.get("display_order", type=int) or 0)
                if action == "update" and iid:
                    execute("UPDATE indicators SET name=?, area=?, description=?, display_order=? WHERE id=?",
                            vals + (iid,))
                    flash("Indicator updated.", "success")
                else:
                    execute("INSERT INTO indicators(name, area, description, display_order) VALUES (?,?,?,?)", vals)
                    flash(f"Indicator '{name}' added.", "success")
        return redirect(url_for("curriculum.indicators"))
    rows = query("SELECT * FROM indicators ORDER BY display_order, id")
    areas = sorted({r["area"] for r in rows} | {"Co-Scholastic", "Life Skills", "Personal & Social"})
    return render_template("curriculum/indicators.html", rows=rows, areas=areas)


@bp.route("/indicators/assess", methods=["GET", "POST"])
def assess_indicators():
    class_id = request.values.get("class_id", type=int)
    term = request.values.get("term") or TERMS[0]
    year = services.academic_year()
    if request.method == "POST" and class_id:
        data = services.indicator_matrix(class_id, term)
        db = get_db()
        for s in data["students"]:
            for ind in data["indicators"]:
                grade = request.form.get(f"g_{s['id']}_{ind['id']}")
                if grade in INDICATOR_GRADES:
                    db.execute("""INSERT INTO indicator_assessments(student_id, indicator_id, academic_year, term,
                                  grade) VALUES (?,?,?,?,?) ON CONFLICT(student_id, indicator_id, academic_year, term)
                                  DO UPDATE SET grade = excluded.grade""", (s["id"], ind["id"], year, term, grade))
                else:
                    db.execute("""DELETE FROM indicator_assessments WHERE student_id=? AND indicator_id=?
                                  AND academic_year=? AND term=?""", (s["id"], ind["id"], year, term))
        db.commit()
        flash("Indicator grades saved.", "success")
        return redirect(url_for("curriculum.assess_indicators", class_id=class_id, term=term))
    data = services.indicator_matrix(class_id, term) if class_id else None
    return render_template("curriculum/assess_indicators.html", classes=services.all_classes(), class_id=class_id,
                           term=term, data=data)
