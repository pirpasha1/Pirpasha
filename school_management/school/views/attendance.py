from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import services
from ..db import get_db, query

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@bp.route("/", methods=["GET", "POST"])
def mark():
    class_id = request.values.get("class_id", type=int)
    day = request.values.get("date") or date.today().isoformat()
    try:
        day_obj = date.fromisoformat(day)
    except ValueError:
        flash("Please pick a valid date.", "error")
        return redirect(url_for("attendance.mark"))
    if request.method == "POST" and class_id:
        if day_obj > date.today():
            flash("Attendance cannot be marked for a future date.", "error")
            return redirect(url_for("attendance.mark", class_id=class_id, date=day))
        db = get_db()
        saved = 0
        for s in services.class_students(class_id):
            status = request.form.get(f"s_{s['id']}")
            if status in ("P", "A", "L"):
                db.execute("""INSERT INTO attendance(student_id, class_id, date, status) VALUES (?,?,?,?)
                              ON CONFLICT(student_id, date) DO UPDATE SET status = excluded.status,
                              class_id = excluded.class_id""", (s["id"], class_id, day, status))
                saved += 1
        db.commit()
        absent = [s["name"] for s in services.class_students(class_id) if request.form.get(f"s_{s['id']}") == "A"]
        msg = f"Attendance saved for {saved} students on {day_obj.strftime('%d-%m-%Y')}."
        if absent:
            msg += f" Absent: {', '.join(absent)}."
        flash(msg, "success")
        return redirect(url_for("attendance.mark", class_id=class_id, date=day))

    students, existing = [], {}
    if class_id:
        students = services.class_students(class_id)
        existing = {r["student_id"]: r["status"] for r in query(
            """SELECT a.student_id, a.status FROM attendance a JOIN students s ON s.id = a.student_id
               WHERE s.class_id = ? AND a.date = ?""", (class_id, day))}
    return render_template("attendance/mark.html", classes=services.all_classes(), class_id=class_id,
                           day=day, day_obj=day_obj, students=students, existing=existing,
                           already=bool(existing))


@bp.route("/register")
def register():
    class_id = request.args.get("class_id", type=int)
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    data = None
    try:
        y, m = (int(x) for x in month.split("-"))
    except ValueError:
        y, m = date.today().year, date.today().month
        month = f"{y}-{m:02d}"
    if class_id:
        data = services.attendance_register(class_id, y, m)
    return render_template("attendance/register.html", classes=services.all_classes(), class_id=class_id,
                           month=month, data=data, klass=services.get_class(class_id) if class_id else None)
