"""Exams, marks entry, mark sheets, teacher remarks and report cards."""
from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for

from .. import TERMS, admin_required, services
from ..db import execute, get_db, get_settings, query
from ..exports import report_cards_pdf

bp = Blueprint("exams", __name__)


@bp.route("/exams", methods=["GET", "POST"])
def exams():
    if request.method == "POST":
        admin_required()
        action = request.form.get("action", "add")
        eid = request.form.get("exam_id", type=int)
        if action == "delete" and eid:
            execute("DELETE FROM exams WHERE id = ?", (eid,))
            flash("Exam and all its marks deleted.", "success")
            return redirect(url_for("exams.exams"))
        name = request.form.get("name", "").strip()
        try:
            max_marks = float(request.form.get("max_marks") or 100)
            if max_marks <= 0:
                raise ValueError
        except ValueError:
            flash("Maximum marks must be a number greater than 0.", "error")
            return redirect(url_for("exams.exams"))
        if not name:
            flash("Please enter the exam name.", "error")
            return redirect(url_for("exams.exams"))
        values = (name, request.form.get("term") or None, request.form.get("academic_year") or services.academic_year(),
                  max_marks, request.form.get("exam_date") or None, request.form.get("display_order", type=int) or 0)
        if action == "update" and eid:
            execute("""UPDATE exams SET name=?, term=?, academic_year=?, max_marks=?, exam_date=?, display_order=?
                       WHERE id = ?""", values + (eid,))
            flash("Exam updated.", "success")
        else:
            execute("""INSERT INTO exams(name, term, academic_year, max_marks, exam_date, display_order)
                       VALUES (?,?,?,?,?,?)""", values)
            flash(f"Exam '{name}' created. You can now enter marks.", "success")
        return redirect(url_for("exams.exams"))
    rows = query("""SELECT e.*, (SELECT COUNT(*) FROM marks m WHERE m.exam_id = e.id) AS entries
                    FROM exams e ORDER BY e.academic_year DESC, e.display_order, e.exam_date, e.id""")
    return render_template("exams/exams.html", exams=rows)


@bp.route("/marks", methods=["GET", "POST"])
def enter_marks():
    exam_id = request.values.get("exam_id", type=int)
    class_id = request.values.get("class_id", type=int)
    subject_id = request.values.get("subject_id", type=int)
    exam = query("SELECT * FROM exams WHERE id = ?", (exam_id,), one=True) if exam_id else None
    subjects = services.class_subjects(class_id) if class_id else []
    if subject_id and subject_id not in {s["id"] for s in subjects}:
        subject_id = None
    students = services.class_students(class_id) if class_id else []

    if request.method == "POST" and exam and class_id and subject_id:
        db = get_db()
        errors, saved = [], 0
        for s in students:
            raw = (request.form.get(f"m_{s['id']}") or "").strip()
            absent = 1 if request.form.get(f"ab_{s['id']}") or raw.upper() in ("AB", "A") else 0
            if absent:
                value = None
            elif raw == "":
                db.execute("DELETE FROM marks WHERE exam_id=? AND student_id=? AND subject_id=?",
                           (exam_id, s["id"], subject_id))
                continue
            else:
                try:
                    value = float(raw)
                except ValueError:
                    errors.append(f"{s['name']}: '{raw}' is not a number")
                    continue
                if value < 0 or value > exam["max_marks"]:
                    errors.append(f"{s['name']}: {raw} is outside 0 - {exam['max_marks']:g}")
                    continue
            db.execute("""INSERT INTO marks(exam_id, student_id, subject_id, marks, absent) VALUES (?,?,?,?,?)
                          ON CONFLICT(exam_id, student_id, subject_id)
                          DO UPDATE SET marks = excluded.marks, absent = excluded.absent""",
                       (exam_id, s["id"], subject_id, value, absent))
            saved += 1
        db.commit()
        if errors:
            flash("Some marks were NOT saved - please correct them: " + "; ".join(errors), "error")
        flash(f"Marks saved for {saved} students.", "success")
        nxt = request.form.get("next_subject", type=int)
        return redirect(url_for("exams.enter_marks", exam_id=exam_id, class_id=class_id,
                                subject_id=nxt or subject_id))

    existing = {}
    if exam and class_id and subject_id:
        existing = {r["student_id"]: r for r in query(
            "SELECT * FROM marks WHERE exam_id = ? AND subject_id = ?", (exam_id, subject_id))}
    next_subject = None
    if subject_id:
        ids = [s["id"] for s in subjects]
        i = ids.index(subject_id)
        next_subject = subjects[i + 1] if i + 1 < len(ids) else None
    return render_template("exams/marks.html", exams=services.exams_for_year(), classes=services.all_classes(),
                           exam=exam, exam_id=exam_id, class_id=class_id, subject_id=subject_id,
                           subjects=subjects, students=students, existing=existing, next_subject=next_subject)


@bp.route("/marksheet")
def marksheet():
    exam_id = request.args.get("exam_id", type=int)
    class_id = request.args.get("class_id", type=int)
    data = services.marksheet(exam_id, class_id) if exam_id and class_id else None
    return render_template("exams/marksheet.html", exams=services.exams_for_year(), classes=services.all_classes(),
                           exam_id=exam_id, class_id=class_id, data=data,
                           klass=services.get_class(class_id) if class_id else None)


@bp.route("/result-analysis")
def result_analysis():
    exam_id = request.args.get("exam_id", type=int)
    exam = query("SELECT * FROM exams WHERE id = ?", (exam_id,), one=True) if exam_id else None
    data = services.result_analysis(exam_id) if exam else None
    return render_template("exams/analysis.html", exams=services.exams_for_year(), exam=exam, exam_id=exam_id,
                           data=data, scale=services.GRADE_SCALE)


@bp.route("/remarks", methods=["GET", "POST"])
def remarks():
    class_id = request.values.get("class_id", type=int)
    term = request.values.get("term") or TERMS[0]
    year = services.academic_year()
    students = services.class_students(class_id) if class_id else []
    if request.method == "POST" and class_id:
        db = get_db()
        for s in students:
            text = (request.form.get(f"r_{s['id']}") or "").strip()
            db.execute("""INSERT INTO report_remarks(student_id, academic_year, term, remarks) VALUES (?,?,?,?)
                          ON CONFLICT(student_id, academic_year, term) DO UPDATE SET remarks = excluded.remarks""",
                       (s["id"], year, term, text))
        db.commit()
        flash("Remarks saved.", "success")
        return redirect(url_for("exams.remarks", class_id=class_id, term=term))
    existing = {r["student_id"]: r["remarks"] for r in query(
        "SELECT student_id, remarks FROM report_remarks WHERE academic_year = ? AND term = ?", (year, term))}
    suggestions = ["Excellent performance. Keep it up!", "Very good effort. Can do even better.",
                   "Good progress. Needs more practice in weak subjects.", "Regular and well-behaved student.",
                   "Needs to be more attentive in class.", "Should improve handwriting and neatness.",
                   "Needs regular revision at home.", "Participates actively in class activities."]
    return render_template("exams/remarks.html", classes=services.all_classes(), class_id=class_id, term=term,
                           students=students, existing=existing, suggestions=suggestions)


@bp.route("/report-cards")
def report_cards():
    class_id = request.args.get("class_id", type=int)
    students = services.class_students(class_id) if class_id else []
    return render_template("exams/report_cards.html", classes=services.all_classes(), class_id=class_id,
                           students=students, exams=services.exams_for_year())


@bp.route("/report-cards/<int:student_id>")
def report_card(student_id):
    card = services.report_card(student_id)
    if not card:
        abort(404)
    return render_template("exams/report_card.html", card=card, scale=services.GRADE_SCALE)


@bp.route("/report-cards/<int:student_id>/pdf")
def report_card_pdf(student_id):
    card = services.report_card(student_id)
    if not card:
        abort(404)
    buf = report_cards_pdf([card], get_settings())
    name = f"report-card-{card['student']['admission_no']}-{card['student']['name'].replace(' ', '_')}.pdf"
    return send_file(buf, as_attachment=True, download_name=name, mimetype="application/pdf")


@bp.route("/report-cards/class/<int:class_id>/pdf")
def class_report_cards_pdf(class_id):
    klass = services.get_class(class_id)
    if not klass:
        abort(404)
    cards = [services.report_card(s["id"]) for s in services.class_students(class_id)]
    buf = report_cards_pdf(cards, get_settings())
    return send_file(buf, as_attachment=True, mimetype="application/pdf",
                     download_name=f"report-cards-class-{klass['grade']}-{klass['section']}.pdf")
