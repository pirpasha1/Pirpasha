"""End-to-end tests: run with  python -m pytest tests  (from the school_management folder)."""
import io
import os
import sys
from datetime import date

import pytest
from openpyxl import Workbook, load_workbook

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from school import create_app  # noqa: E402
from school.services import grade_for  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    return create_app({"DATABASE": str(tmp_path / "test.db"), "SECRET_KEY": "test", "TESTING": True,
                       "CSRF_DISABLED": True})


@pytest.fixture()
def client(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 302
    return c


@pytest.fixture()
def demo(client):
    assert client.post("/demo-data").status_code == 302
    return client


def ids(app):
    with app.app_context():
        from school.db import query
        return {
            "class": query("SELECT id FROM classes ORDER BY id LIMIT 1", one=True)[0],
            "student": query("SELECT id FROM students ORDER BY id LIMIT 1", one=True)[0],
            "exam": query("SELECT id FROM exams ORDER BY id LIMIT 1", one=True)[0],
            "subject": query("SELECT id FROM subjects WHERE name = 'Mathematics'", one=True)[0],
            "teacher": query("SELECT id FROM teachers ORDER BY id LIMIT 1", one=True)[0],
        }


def test_login_required_and_wrong_password(app):
    c = app.test_client()
    assert c.get("/").status_code == 302
    r = c.post("/login", data={"username": "admin", "password": "nope"})
    assert b"Wrong username or password" in r.data


def test_csrf_enforced(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "c.db"), "SECRET_KEY": "x", "TESTING": True})
    c = app.test_client()
    assert c.post("/login", data={"username": "admin", "password": "admin123"}).status_code == 400


def test_grade_scale():
    assert grade_for(95) == "A1"
    assert grade_for(90) == "A2"
    assert grade_for(91) == "A1"
    assert grade_for(81) == "A2"
    assert grade_for(33) == "D"
    assert grade_for(32.9) == "E"
    assert grade_for(None) == ""


def test_empty_system_pages(client):
    for url in ["/", "/students/", "/classes", "/subjects", "/teachers", "/attendance/", "/attendance/register",
                "/exams", "/marks", "/marksheet", "/result-analysis", "/remarks", "/report-cards", "/chapters",
                "/chapters/progress", "/competencies", "/competencies/assess", "/competencies/report",
                "/indicators", "/indicators/assess", "/reports/", "/settings", "/users", "/help", "/search?q=x",
                "/students/new", "/students/import", "/students/promote", "/teachers/new", "/account/password"]:
        r = client.get(url)
        assert r.status_code == 200, url


def test_all_pages_with_demo_data(app, demo):
    i = ids(app)
    urls = [
        "/", "/students/", f"/students/?class_id={i['class']}&q=a", f"/students/{i['student']}",
        f"/students/{i['student']}/edit", "/classes", f"/classes/{i['class']}", "/teachers",
        f"/teachers/{i['teacher']}", f"/teachers/{i['teacher']}/edit",
        f"/attendance/?class_id={i['class']}", f"/attendance/register?class_id={i['class']}",
        f"/marks?exam_id={i['exam']}&class_id={i['class']}&subject_id={i['subject']}",
        f"/marksheet?exam_id={i['exam']}&class_id={i['class']}", f"/result-analysis?exam_id={i['exam']}",
        f"/remarks?class_id={i['class']}", f"/report-cards?class_id={i['class']}", f"/report-cards/{i['student']}",
        "/chapters?grade=6", f"/chapters/progress?class_id={i['class']}",
        "/competencies?grade=6", f"/competencies/assess?class_id={i['class']}&subject_id={i['subject']}",
        f"/competencies/report?class_id={i['class']}&subject_id={i['subject']}",
        f"/indicators/assess?class_id={i['class']}", "/search?q=sharma", "/search?q=fractions",
        f"/students/promote?from_class={i['class']}",
    ]
    for url in urls:
        r = demo.get(url)
        assert r.status_code == 200, url
    page = demo.get(f"/report-cards/{i['student']}").data
    assert b"PROGRESS REPORT" in page and b"Part B" in page and b"Part C" in page


def test_all_downloads(app, demo):
    i = ids(app)
    month = date.today().strftime("%Y-%m")
    reports = [
        "/reports/students?", f"/reports/students?class_id={i['class']}&", "/reports/teachers?", "/reports/classes?",
        f"/reports/attendance?class_id={i['class']}&month={month}&", f"/reports/attendance-summary?below=95&",
        f"/reports/marks?exam_id={i['exam']}&class_id={i['class']}&", f"/reports/result-analysis?exam_id={i['exam']}&",
        f"/reports/chapters?class_id={i['class']}&", "/reports/chapter-list?grade=6&",
        f"/reports/competencies?class_id={i['class']}&subject_id={i['subject']}&term=Term+1&",
        f"/reports/indicators?class_id={i['class']}&term=Term+1&",
    ]
    for url in reports:
        pdf = demo.get(url + "fmt=pdf")
        assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF", url
        xl = demo.get(url + "fmt=xlsx")
        assert xl.status_code == 200, url
        load_workbook(io.BytesIO(xl.data))  # must be a valid workbook
    for url in [f"/report-cards/{i['student']}/pdf", f"/report-cards/class/{i['class']}/pdf"]:
        r = demo.get(url)
        assert r.status_code == 200 and r.data[:4] == b"%PDF", url
    assert demo.get("/students/import/template").status_code == 200
    assert demo.get("/chapters/template").status_code == 200
    assert demo.get("/backup").data[:15] == b"SQLite format 3"


def test_full_workflow(app, client):
    # class, teacher, student
    client.post("/classes", data={"grade": "9", "section": "A, B", "all_subjects": "1"})
    with app.app_context():
        from school.db import query
        cid = query("SELECT id FROM classes WHERE grade='9' AND section='A'", one=True)[0]
        assert query("SELECT COUNT(*) FROM classes WHERE grade='9'", one=True)[0] == 2
        math = query("SELECT id FROM subjects WHERE name='Mathematics'", one=True)[0]
    client.post("/teachers/new", data={"name": "Test Teacher", "emp_code": "X1", "status": "Active"})
    r = client.post("/students/new", data={"admission_no": "5001", "name": "Ravi Kumar", "class_id": cid,
                                           "roll_no": "1", "gender": "Male", "status": "Active"})
    assert r.status_code == 302
    dup = client.post("/students/new", data={"admission_no": "5001", "name": "Someone", "status": "Active"})
    assert b"already used" in dup.data
    with app.app_context():
        from school.db import query
        sid = query("SELECT id FROM students WHERE admission_no='5001'", one=True)[0]

    # attendance
    today = date.today().isoformat()
    client.post("/attendance/", data={"class_id": cid, "date": today, f"s_{sid}": "A"})
    with app.app_context():
        from school.db import query
        assert query("SELECT status FROM attendance WHERE student_id=?", (sid,), one=True)[0] == "A"
    fut = client.post("/attendance/", data={"class_id": cid, "date": "2999-01-01", f"s_{sid}": "P"},
                      follow_redirects=True)
    assert b"future" in fut.data

    # exam + marks (including validation)
    client.post("/exams", data={"name": "Unit Test", "term": "Term 1", "max_marks": "50"})
    with app.app_context():
        from school.db import query
        eid = query("SELECT id FROM exams WHERE name='Unit Test'", one=True)[0]
    bad = client.post("/marks", data={"exam_id": eid, "class_id": cid, "subject_id": math, f"m_{sid}": "75"},
                      follow_redirects=True)
    assert b"NOT saved" in bad.data
    client.post("/marks", data={"exam_id": eid, "class_id": cid, "subject_id": math, f"m_{sid}": "45"})
    page = client.get(f"/marksheet?exam_id={eid}&class_id={cid}").data
    assert b"90" in page and b"A2" in page

    # chapters, progress, competencies, indicators, remarks
    client.post("/chapters", data={"grade": "9", "subject_id": math, "chapter_no": "1", "title": "Number Systems"})
    with app.app_context():
        from school.db import query
        chid = query("SELECT id FROM chapters WHERE title='Number Systems'", one=True)[0]
    client.post("/chapters/progress", data={"class_id": cid, f"status_{chid}": "Completed",
                                            f"start_{chid}": "01-07-2026", f"end_{chid}": "2026-07-20"})
    client.post("/competencies", data={"grade": "9", "subject_id": math, "code": "M9.1", "chapter_id": chid,
                                       "description": "Represents real numbers on the number line"})
    with app.app_context():
        from school.db import query
        assert query("SELECT status, start_date FROM chapter_progress", one=True)[:] == ("Completed", "2026-07-01")
        comp = query("SELECT id FROM competencies WHERE code='M9.1'", one=True)[0]
        ind = query("SELECT id FROM indicators LIMIT 1", one=True)[0]
    client.post("/competencies/assess", data={"class_id": cid, "subject_id": math, "term": "Term 1",
                                              f"l_{sid}_{comp}": "3"})
    client.post("/indicators/assess", data={"class_id": cid, "term": "Term 1", f"g_{sid}_{ind}": "A"})
    client.post("/remarks", data={"class_id": cid, "term": "Term 1", f"r_{sid}": "Good work"})

    card = client.get(f"/report-cards/{sid}").data
    for text in (b"Ravi Kumar", b"Proficient", b"Good work", b"Represents real numbers", b"PASS"):
        assert text in card, text

    # promote then mark as left
    with app.app_context():
        from school.db import query
        cid_b = query("SELECT id FROM classes WHERE grade='9' AND section='B'", one=True)[0]
    client.post("/students/promote", data={"from_class": cid, "to_class": cid_b, "student_ids": sid,
                                           "action": "promote"})
    client.post("/students/promote", data={"from_class": cid_b, "student_ids": sid, "action": "left"})
    with app.app_context():
        from school.db import query
        row = query("SELECT class_id, status FROM students WHERE id=?", (sid,), one=True)
        assert row["class_id"] == cid_b and row["status"] == "Left"


def test_student_excel_import(app, client):
    client.post("/classes", data={"grade": "6", "section": "A"})
    wb = Workbook()
    ws = wb.active
    ws.append(["Admission No", "Student Name", "Class", "Section", "Roll No", "Gender",
               "Date of Birth (DD-MM-YYYY)", "Father's Name"])
    ws.append([7001, "Asha Rani", 6, "A", 1, "Female", "15-06-2014", "Ram Lal"])
    ws.append([7002, "Bad Class", 12, "Z", 2, "Male", "", ""])
    ws.append([7003, "Bad Date", 6, "a", 3, "Male", "31-31-2014", ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    r = client.post("/students/import", data={"file": (buf, "students.xlsx")}, content_type="multipart/form-data")
    assert b"1 added" in r.data and b"Row 3" in r.data and b"Row 4" in r.data
    with app.app_context():
        from school.db import query
        s = query("SELECT * FROM students WHERE admission_no='7001'", one=True)
        assert s["dob"] == "2014-06-15" and s["roll_no"] == 1


def test_chapter_excel_import(app, client):
    wb = Workbook()
    ws = wb.active
    ws.append(["Class", "Subject", "Chapter No", "Chapter Title", "Book Name", "Learning Outcomes", "Planned Periods"])
    ws.append([7, "Mathematics", 1, "Large Numbers Around Us", "Ganita Prakash", "Reads large numbers", 10])
    ws.append([7, "Environmental Studies", 1, "New Subject Chapter", "", "", ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    client.post("/chapters/import", data={"file": (buf, "ch.xlsx")}, content_type="multipart/form-data")
    with app.app_context():
        from school.db import query
        assert query("SELECT COUNT(*) FROM chapters WHERE grade='7'", one=True)[0] == 2
        assert query("SELECT 1 FROM subjects WHERE name='Environmental Studies'", one=True)


def test_teacher_role_restrictions(app, client):
    client.post("/users", data={"username": "teach", "password": "secret1", "role": "teacher"})
    t = app.test_client()
    assert t.post("/login", data={"username": "teach", "password": "secret1"}).status_code == 302
    assert t.get("/settings").status_code == 403
    assert t.get("/users").status_code == 403
    assert t.get("/backup").status_code == 403
    assert t.get("/attendance/").status_code == 200


def test_backup_restore_roundtrip(app, client, tmp_path):
    client.post("/students/new", data={"admission_no": "1", "name": "Before Backup", "status": "Active"})
    backup = client.get("/backup").data
    client.post("/students/new", data={"admission_no": "2", "name": "After Backup", "status": "Active"})
    r = client.post("/restore", data={"backup": (io.BytesIO(backup), "b.db")}, content_type="multipart/form-data")
    assert r.status_code == 302
    client.post("/login", data={"username": "admin", "password": "admin123"})
    page = client.get("/students/").data
    assert b"Before Backup" in page and b"After Backup" not in page
