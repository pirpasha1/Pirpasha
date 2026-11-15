"""Data assembly shared by the web pages and the PDF / Excel exports.

Keeping these calculations in one place guarantees that what staff see on
screen is exactly what gets printed or downloaded.
"""
import calendar
from collections import defaultdict
from datetime import date

from . import COMPETENCY_LEVELS, TERMS
from .db import get_settings, query

# CBSE 8-point grading scale: (range shown to parents, grade)
GRADE_SCALE = [("91-100", "A1"), ("81-90", "A2"), ("71-80", "B1"), ("61-70", "B2"),
               ("51-60", "C1"), ("41-50", "C2"), ("33-40", "D"), ("Below 33", "E")]

CLASS_ORDER = ("CASE WHEN c.grade GLOB '[0-9]*' THEN CAST(c.grade AS INTEGER) ELSE -1 END, "
               "c.grade, c.section")


def grade_for(pct):
    if pct is None:
        return ""
    for above, grade in ((90, "A1"), (80, "A2"), (70, "B1"), (60, "B2"), (50, "C1"), (40, "C2")):
        if pct > above:
            return grade
    return "D" if pct >= 33 else "E"


def pass_mark():
    try:
        return float(get_settings().get("pass_percentage") or 33)
    except ValueError:
        return 33.0


def academic_year():
    return get_settings()["academic_year"]


def class_label(row):
    if row is None:
        return "Not assigned"
    return f"{row['grade']}-{row['section']}"


# ---------------------------------------------------------------- lookups

def all_classes():
    return query(f"""
        SELECT c.*, t.name AS class_teacher,
               (SELECT COUNT(*) FROM students s WHERE s.class_id = c.id AND s.status = 'Active') AS strength
        FROM classes c LEFT JOIN teachers t ON t.id = c.class_teacher_id
        ORDER BY {CLASS_ORDER}""")


def get_class(class_id):
    return query("""SELECT c.*, t.name AS class_teacher FROM classes c
                    LEFT JOIN teachers t ON t.id = c.class_teacher_id WHERE c.id = ?""",
                 (class_id,), one=True)


def class_students(class_id, active_only=True):
    sql = "SELECT * FROM students WHERE class_id = ?"
    if active_only:
        sql += " AND status = 'Active'"
    return query(sql + " ORDER BY roll_no IS NULL, roll_no, name", (class_id,))


def class_subjects(class_id):
    """Subjects taught in a class. Falls back to every subject if none are assigned yet."""
    rows = query("""SELECT s.*, cs.teacher_id, t.name AS teacher FROM class_subjects cs
                    JOIN subjects s ON s.id = cs.subject_id
                    LEFT JOIN teachers t ON t.id = cs.teacher_id
                    WHERE cs.class_id = ? ORDER BY s.name""", (class_id,))
    if rows:
        return rows
    return query("SELECT s.*, NULL AS teacher_id, NULL AS teacher FROM subjects s ORDER BY s.name")


def all_subjects():
    return query("SELECT * FROM subjects ORDER BY name")


def all_teachers(active_only=False):
    sql = "SELECT * FROM teachers"
    if active_only:
        sql += " WHERE status = 'Active'"
    return query(sql + " ORDER BY name")


def exams_for_year(year=None):
    return query("SELECT * FROM exams WHERE academic_year = ? ORDER BY display_order, exam_date, id",
                 (year or academic_year(),))


def grades_list():
    rows = query(f"SELECT DISTINCT c.grade FROM classes c ORDER BY {CLASS_ORDER}")
    seen, out = set(), []
    for r in rows:
        if r["grade"] not in seen:
            seen.add(r["grade"])
            out.append(r["grade"])
    for r in query("SELECT DISTINCT grade FROM chapters ORDER BY grade"):
        if r["grade"] not in seen:
            seen.add(r["grade"])
            out.append(r["grade"])
    return out


# ------------------------------------------------------------- attendance

def month_dates(year, month):
    days = calendar.monthrange(year, month)[1]
    return [date(year, month, d) for d in range(1, days + 1)]


def attendance_register(class_id, year, month):
    dates = month_dates(year, month)
    start, end = dates[0].isoformat(), dates[-1].isoformat()
    students = class_students(class_id)
    records = query("""SELECT a.student_id, a.date, a.status FROM attendance a
                       JOIN students s ON s.id = a.student_id
                       WHERE s.class_id = ? AND a.date BETWEEN ? AND ?""", (class_id, start, end))
    by_key = {(r["student_id"], r["date"]): r["status"] for r in records}
    working = sorted({r["date"] for r in records})
    rows = []
    for s in students:
        cells = [by_key.get((s["id"], d.isoformat()), "") for d in dates]
        p, a, lv = cells.count("P"), cells.count("A"), cells.count("L")
        marked = p + a + lv
        rows.append({
            "student": s, "cells": cells, "P": p, "A": a, "L": lv,
            "pct": round(100 * p / marked, 1) if marked else None,
        })
    return {"dates": dates, "rows": rows, "working_days": len(working),
            "month_name": f"{calendar.month_name[month]} {year}"}


def attendance_summary(student_id, start=None, end=None):
    settings = get_settings()
    start = start or settings["session_start"]
    end = end or settings["session_end"]
    row = query("""SELECT SUM(status = 'P') AS p, SUM(status = 'A') AS a, SUM(status = 'L') AS l,
                          COUNT(*) AS total
                   FROM attendance WHERE student_id = ? AND date BETWEEN ? AND ?""",
                (student_id, start, end), one=True)
    total = row["total"] or 0
    present = row["p"] or 0
    return {"present": present, "absent": row["a"] or 0, "leave": row["l"] or 0, "total": total,
            "pct": round(100 * present / total, 1) if total else None}


def daily_attendance_stats(day):
    row = query("SELECT SUM(status = 'P') AS p, COUNT(*) AS total FROM attendance WHERE date = ?",
                (day,), one=True)
    total = row["total"] or 0
    return {"present": row["p"] or 0, "total": total,
            "pct": round(100 * (row["p"] or 0) / total, 1) if total else None}


# ------------------------------------------------------------------ marks

def _marks_lookup(exam_ids, student_ids):
    if not exam_ids or not student_ids:
        return {}
    q_e = ",".join("?" * len(exam_ids))
    q_s = ",".join("?" * len(student_ids))
    rows = query(f"SELECT * FROM marks WHERE exam_id IN ({q_e}) AND student_id IN ({q_s})",
                 (*exam_ids, *student_ids))
    return {(r["exam_id"], r["student_id"], r["subject_id"]): r for r in rows}


def _cell(mark_row):
    if mark_row is None:
        return None
    if mark_row["absent"]:
        return "AB"
    return mark_row["marks"]


def marksheet(exam_id, class_id):
    exam = query("SELECT * FROM exams WHERE id = ?", (exam_id,), one=True)
    students = class_students(class_id)
    subjects = class_subjects(class_id)
    lookup = _marks_lookup([exam_id], [s["id"] for s in students])
    max_m = exam["max_marks"]
    limit = pass_mark()
    rows = []
    for s in students:
        cells, obtained, possible, failed = [], 0.0, 0.0, []
        for sub in subjects:
            value = _cell(lookup.get((exam_id, s["id"], sub["id"])))
            cells.append(value)
            if value is None:
                continue
            possible += max_m
            got = 0.0 if value == "AB" else float(value)
            obtained += got
            if 100 * got / max_m < limit:
                failed.append(sub["name"])
        pct = round(100 * obtained / possible, 2) if possible else None
        rows.append({"student": s, "cells": cells, "total": obtained if possible else None,
                     "max_total": possible, "pct": pct, "grade": grade_for(pct),
                     "result": "" if pct is None else ("Pass" if not failed else "Needs Improvement"),
                     "failed": failed})
    _assign_ranks(rows)
    sub_stats = []
    for i, sub in enumerate(subjects):
        vals = [0.0 if r["cells"][i] == "AB" else float(r["cells"][i])
                for r in rows if r["cells"][i] is not None]
        sub_stats.append({
            "subject": sub,
            "avg": round(sum(vals) / len(vals), 1) if vals else None,
            "high": max(vals) if vals else None,
            "low": min(vals) if vals else None,
            "passed": sum(1 for v in vals if 100 * v / max_m >= limit),
            "appeared": len(vals),
        })
    return {"exam": exam, "subjects": subjects, "rows": rows, "subject_stats": sub_stats}


def _assign_ranks(rows):
    ranked = sorted((r for r in rows if r["pct"] is not None), key=lambda r: -r["pct"])
    rank, prev = 0, None
    for i, r in enumerate(ranked, start=1):
        if r["pct"] != prev:
            rank, prev = i, r["pct"]
        r["rank"] = rank
    for r in rows:
        r.setdefault("rank", None)


def result_analysis(exam_id):
    out = []
    for c in all_classes():
        if not c["strength"]:
            continue
        ms = marksheet(exam_id, c["id"])
        appeared = [r for r in ms["rows"] if r["pct"] is not None]
        passed = [r for r in appeared if r["result"] == "Pass"]
        out.append({
            "class": c, "strength": c["strength"], "appeared": len(appeared), "passed": len(passed),
            "pass_pct": round(100 * len(passed) / len(appeared), 1) if appeared else None,
            "avg_pct": round(sum(r["pct"] for r in appeared) / len(appeared), 1) if appeared else None,
            "top": max(appeared, key=lambda r: r["pct"]) if appeared else None,
            "grades": {g: sum(1 for r in appeared if r["grade"] == g) for _, g in GRADE_SCALE},
        })
    return out


# ------------------------------------------------------------ report card

def report_card(student_id):
    settings = get_settings()
    year = settings["academic_year"]
    student = query("SELECT * FROM students WHERE id = ?", (student_id,), one=True)
    if student is None:
        return None
    klass = get_class(student["class_id"]) if student["class_id"] else None
    exams = exams_for_year(year)
    subjects = class_subjects(student["class_id"]) if klass else []
    classmates = class_students(student["class_id"]) if klass else [student]
    lookup = _marks_lookup([e["id"] for e in exams], [s["id"] for s in classmates])
    limit = pass_mark()

    def overall(sid):
        got = possible = 0.0
        for e in exams:
            for sub in subjects:
                v = _cell(lookup.get((e["id"], sid, sub["id"])))
                if v is None:
                    continue
                possible += e["max_marks"]
                got += 0.0 if v == "AB" else float(v)
        return (got, possible)

    rows, failed = [], []
    for sub in subjects:
        cells, got, possible = [], 0.0, 0.0
        for e in exams:
            v = _cell(lookup.get((e["id"], student_id, sub["id"])))
            cells.append(v)
            if v is not None:
                possible += e["max_marks"]
                got += 0.0 if v == "AB" else float(v)
        pct = round(100 * got / possible, 1) if possible else None
        if pct is not None and pct < limit:
            failed.append(sub["name"])
        rows.append({"subject": sub, "cells": cells, "total": got if possible else None,
                     "max_total": possible, "pct": pct, "grade": grade_for(pct)})

    got, possible = overall(student_id)
    pct = round(100 * got / possible, 2) if possible else None

    rank = None
    if pct is not None:
        scores = []
        for mate in classmates:
            g_, p_ = overall(mate["id"])
            if p_:
                scores.append(round(100 * g_ / p_, 2))
        rank = 1 + sum(1 for s in scores if s > pct)

    indicators = query("SELECT * FROM indicators ORDER BY display_order, id")
    ind_rows = query("""SELECT indicator_id, term, grade FROM indicator_assessments
                        WHERE student_id = ? AND academic_year = ?""", (student_id, year))
    ind_map = {(r["indicator_id"], r["term"]): r["grade"] for r in ind_rows}
    indicator_rows = [{"indicator": i, "grades": [ind_map.get((i["id"], t), "") for t in TERMS]}
                      for i in indicators]

    comp_rows = query("""
        SELECT c.code, c.description, s.name AS subject, ca.term, ca.level
        FROM competency_assessments ca
        JOIN competencies c ON c.id = ca.competency_id
        JOIN subjects s ON s.id = c.subject_id
        WHERE ca.student_id = ? AND ca.academic_year = ?
        ORDER BY s.name, c.code, c.id""", (student_id, year))
    comp_map = {}
    for r in comp_rows:
        key = (r["subject"], r["code"], r["description"])
        comp_map.setdefault(key, {})[r["term"]] = r["level"]
    competencies = [{"subject": k[0], "code": k[1], "description": k[2],
                     "levels": [v.get(t) for t in TERMS]} for k, v in comp_map.items()]

    remarks = {r["term"]: r["remarks"] for r in query(
        "SELECT term, remarks FROM report_remarks WHERE student_id = ? AND academic_year = ?",
        (student_id, year))}

    return {
        "student": student, "klass": klass, "year": year, "exams": exams, "rows": rows,
        "total": got if possible else None, "max_total": possible, "pct": pct, "grade": grade_for(pct),
        "rank": rank, "class_size": len(classmates),
        "result": "" if pct is None else ("PASS" if not failed else "NEEDS IMPROVEMENT"),
        "failed": failed, "attendance": attendance_summary(student_id),
        "indicators": indicator_rows, "competencies": competencies,
        "remarks": [remarks.get(t, "") for t in TERMS],
        "level_names": COMPETENCY_LEVELS,
    }


# ------------------------------------------------- curriculum / chapters

def chapter_progress(class_id, subject_id=None):
    klass = get_class(class_id)
    year = academic_year()
    args = [class_id, year, klass["grade"]]
    sql = """SELECT ch.*, s.name AS subject, cp.status, cp.start_date, cp.end_date,
                    cp.periods_taken, cp.remarks, cp.teacher_id, t.name AS teacher
             FROM chapters ch
             JOIN subjects s ON s.id = ch.subject_id
             LEFT JOIN chapter_progress cp ON cp.chapter_id = ch.id AND cp.class_id = ? AND cp.academic_year = ?
             LEFT JOIN teachers t ON t.id = cp.teacher_id
             WHERE ch.grade = ?"""
    if subject_id:
        sql += " AND ch.subject_id = ?"
        args.append(subject_id)
    rows = query(sql + " ORDER BY s.name, ch.chapter_no", args)
    summary = defaultdict(lambda: {"total": 0, "Completed": 0, "In Progress": 0, "Not Started": 0})
    for r in rows:
        st = r["status"] or "Not Started"
        summary[r["subject"]]["total"] += 1
        summary[r["subject"]][st] += 1
    for v in summary.values():
        v["pct"] = round(100 * v["Completed"] / v["total"], 1) if v["total"] else 0
    return {"klass": klass, "rows": rows, "summary": dict(summary)}


def syllabus_completion_overall():
    """Percentage of (class, chapter) pairs completed this academic year."""
    total = query("""SELECT COUNT(*) FROM classes c JOIN chapters ch ON ch.grade = c.grade""", one=True)[0]
    done = query("""SELECT COUNT(*) FROM chapter_progress cp
                    JOIN classes c ON c.id = cp.class_id
                    JOIN chapters ch ON ch.id = cp.chapter_id AND ch.grade = c.grade
                    WHERE cp.status = 'Completed' AND cp.academic_year = ?""",
                 (academic_year(),), one=True)[0]
    return {"total": total, "done": done, "pct": round(100 * done / total, 1) if total else None}


def class_competencies(class_id, subject_id):
    klass = get_class(class_id)
    return query("""SELECT c.*, ch.chapter_no, ch.title AS chapter FROM competencies c
                    LEFT JOIN chapters ch ON ch.id = c.chapter_id
                    WHERE c.grade = ? AND c.subject_id = ?
                    ORDER BY ch.chapter_no IS NULL, ch.chapter_no, c.code, c.id""",
                 (klass["grade"], subject_id))


def competency_matrix(class_id, subject_id, term):
    year = academic_year()
    students = class_students(class_id)
    comps = class_competencies(class_id, subject_id)
    rows = query("""SELECT ca.student_id, ca.competency_id, ca.level FROM competency_assessments ca
                    JOIN students s ON s.id = ca.student_id
                    WHERE s.class_id = ? AND ca.term = ? AND ca.academic_year = ?""",
                 (class_id, term, year))
    levels = {(r["student_id"], r["competency_id"]): r["level"] for r in rows}
    summary = []
    for c in comps:
        counts = {lvl: 0 for lvl in COMPETENCY_LEVELS}
        for s in students:
            lvl = levels.get((s["id"], c["id"]))
            if lvl:
                counts[lvl] += 1
        assessed = sum(counts.values())
        summary.append({"competency": c, "counts": counts, "assessed": assessed,
                        "achieved_pct": round(100 * (counts[3] + counts[4]) / assessed, 1) if assessed else None})
    return {"students": students, "competencies": comps, "levels": levels, "summary": summary}


def indicator_matrix(class_id, term):
    year = academic_year()
    students = class_students(class_id)
    indicators = query("SELECT * FROM indicators ORDER BY display_order, id")
    rows = query("""SELECT ia.student_id, ia.indicator_id, ia.grade FROM indicator_assessments ia
                    JOIN students s ON s.id = ia.student_id
                    WHERE s.class_id = ? AND ia.term = ? AND ia.academic_year = ?""",
                 (class_id, term, year))
    grades = {(r["student_id"], r["indicator_id"]): r["grade"] for r in rows}
    return {"students": students, "indicators": indicators, "grades": grades}
