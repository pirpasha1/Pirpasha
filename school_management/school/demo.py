"""Sample data so staff can explore every screen before entering real records.

The Class 6 chapter lists follow the NCERT textbooks introduced in 2024
(Ganita Prakash, Curiosity, Exploring Society: India and Beyond). Schools should
check them against the books they actually use and edit as needed.
"""
import random
from datetime import date, timedelta

from .db import get_db, get_settings

CHAPTERS = {
    "Mathematics": ("Ganita Prakash", [
        ("Patterns in Mathematics", "Identifies, describes and extends number and shape patterns"),
        ("Lines and Angles", "Identifies lines, line segments, rays and angles; measures angles with a protractor"),
        ("Number Play", "Uses properties of numbers to play with and reason about numbers"),
        ("Data Handling and Presentation", "Collects, organises and represents data using pictographs and bar graphs"),
        ("Prime Time", "Finds factors and multiples; identifies prime and composite numbers"),
        ("Perimeter and Area", "Finds the perimeter and area of rectangles and squares in daily-life situations"),
        ("Fractions", "Represents, compares and adds fractions"),
        ("Playing with Constructions", "Constructs circles, squares and rectangles using compass and ruler"),
        ("Symmetry", "Identifies lines of symmetry and rotational symmetry in figures"),
        ("The Other Side of Zero", "Understands negative numbers and represents integers on a number line"),
    ]),
    "Science": ("Curiosity", [
        ("The Wonderful World of Science", "Explains how science helps us understand the world around us"),
        ("Diversity in the Living World", "Groups plants and animals based on observable features"),
        ("Mindful Eating: A Path to a Healthy Body", "Identifies components of food and the need for a balanced diet"),
        ("Exploring Magnets", "Describes properties of magnets and their uses"),
        ("Measurement of Length and Motion", "Measures length using standard units and describes types of motion"),
        ("Materials Around Us", "Classifies materials based on their properties"),
        ("Temperature and its Measurement", "Measures temperature using a thermometer correctly"),
        ("A Journey through States of Water", "Explains changes of state of water: evaporation, condensation"),
        ("Methods of Separation in Everyday Life", "Selects suitable methods to separate mixtures"),
        ("Living Creatures: Exploring their Characteristics", "Distinguishes living and non-living things"),
        ("Nature's Treasures", "Explains the importance of conserving natural resources"),
        ("Beyond Earth", "Describes stars, constellations and the solar system"),
    ]),
    "Social Science": ("Exploring Society: India and Beyond", [
        ("Locating Places on the Earth", "Uses maps, globes and directions to locate places"),
        ("Oceans and Continents", "Locates the oceans and continents on a world map"),
        ("Landforms and Life", "Relates major landforms to the way people live"),
        ("Timeline and Sources of History", "Arranges events on a timeline and identifies sources of history"),
        ("India, That Is Bharat", "Explains the different names of India and their origins"),
        ("The Beginnings of Indian Civilisation", "Describes features of the Harappan civilisation"),
        ("India's Cultural Roots", "Describes early Indian schools of thought and their ideas"),
        ("Unity in Diversity, or 'Many in the One'", "Appreciates India's cultural diversity and unity"),
        ("Family and Community", "Explains the roles of family and community in our lives"),
        ("Grassroots Democracy - Part 1: Governance", "Explains the meaning of governance and democracy"),
        ("Grassroots Democracy - Part 2: Local Government in Rural Areas", "Describes the working of Panchayati Raj"),
        ("Grassroots Democracy - Part 3: Local Government in Urban Areas", "Describes the work of urban local bodies"),
        ("The Value of Work", "Recognises the value of different kinds of work"),
        ("Economic Activities Around Us", "Classifies economic activities into primary, secondary and tertiary"),
    ]),
}

TEACHERS = [
    ("T001", "Sunita Sharma", "Female", "M.Sc., B.Ed.", "PGT Mathematics"),
    ("T002", "Rajesh Kumar", "Male", "M.Sc., B.Ed.", "TGT Science"),
    ("T003", "Anita Verma", "Female", "M.A., B.Ed.", "TGT English"),
    ("T004", "Mohan Lal Yadav", "Male", "M.A., B.Ed.", "TGT Hindi"),
    ("T005", "Farida Khan", "Female", "M.A., B.Ed.", "TGT Social Science"),
    ("T006", "Prakash Joshi", "Male", "Shastri, B.Ed.", "TGT Sanskrit"),
    ("T007", "Kavita Nair", "Female", "MCA, B.Ed.", "Computer Teacher"),
]
SUBJECT_TEACHER = {"Mathematics": 0, "Science": 1, "English": 2, "Hindi": 3, "Social Science": 4,
                   "Sanskrit": 5, "Computer Science": 6}

BOYS = ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Kabir", "Ishaan", "Rahul", "Aman", "Harsh", "Yash",
        "Mohit", "Imran", "Gurpreet", "Sahil", "Nikhil"]
GIRLS = ["Ananya", "Diya", "Priya", "Sneha", "Kavya", "Isha", "Meera", "Pooja", "Riya", "Simran", "Neha",
         "Ayesha", "Aditi", "Sakshi", "Tanvi", "Lakshmi"]
SURNAMES = ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Patel", "Kumar", "Mishra", "Reddy", "Das", "Khan",
            "Joshi", "Nair", "Chauhan", "Pandey", "Mehta"]
FATHERS = ["Ramesh", "Suresh", "Mahesh", "Dinesh", "Rakesh", "Anil", "Sunil", "Vijay", "Ajay", "Manoj", "Sanjay",
           "Ashok", "Salim", "Harjeet", "Pradeep", "Deepak"]
MOTHERS = ["Geeta", "Sita", "Rekha", "Seema", "Neelam", "Asha", "Usha", "Kiran", "Meena", "Shabana", "Poonam",
           "Rita", "Sarita", "Manju", "Lata", "Kamla"]


def load_demo():
    rnd = random.Random(42)
    db = get_db()
    settings = get_settings()
    year = settings["academic_year"]
    subjects = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM subjects")}

    teacher_ids = []
    for code, name, gender, qual, desig in TEACHERS:
        teacher_ids.append(db.execute(
            """INSERT INTO teachers(emp_code, name, gender, qualification, designation, phone, joining_date, status)
               VALUES (?,?,?,?,?,?,?, 'Active')""",
            (code, name, gender, qual, desig, f"98{rnd.randint(10000000, 99999999)}",
             f"20{rnd.randint(10, 22)}-07-01")).lastrowid)

    class_ids = {}
    for i, (grade, section) in enumerate([("6", "A"), ("6", "B"), ("7", "A"), ("8", "A")]):
        cid = db.execute("INSERT INTO classes(grade, section, class_teacher_id, room) VALUES (?,?,?,?)",
                         (grade, section, teacher_ids[i], f"R-{10 + i}")).lastrowid
        class_ids[(grade, section)] = cid
        for sname, tidx in SUBJECT_TEACHER.items():
            if sname in subjects:
                db.execute("INSERT INTO class_subjects(class_id, subject_id, teacher_id) VALUES (?,?,?)",
                           (cid, subjects[sname], teacher_ids[tidx]))

    adm = 1001
    student_ids = {}
    for (grade, section), cid in class_ids.items():
        names = []
        for k in range(12):
            girl = k % 2 == 0
            first = rnd.choice(GIRLS if girl else BOYS)
            names.append((f"{first} {rnd.choice(SURNAMES)}", "Female" if girl else "Male"))
        names.sort()
        ids = []
        for roll, (name, gender) in enumerate(names, start=1):
            age = 11 + int(grade) - 6
            dob = date(date.today().year - age - 1, rnd.randint(1, 12), rnd.randint(1, 28))
            sid = db.execute(
                """INSERT INTO students(admission_no, admission_date, name, gender, dob, class_id, roll_no,
                   father_name, mother_name, guardian_phone, address, category, blood_group, mother_tongue, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'Active')""",
                (str(adm), f"{date.today().year - rnd.randint(0, 4)}-04-0{rnd.randint(1, 9)}", name, gender,
                 dob.isoformat(), cid, roll, f"{rnd.choice(FATHERS)} {name.split()[-1]}",
                 f"{rnd.choice(MOTHERS)} {name.split()[-1]}", f"9{rnd.randint(100000000, 999999999)}",
                 f"Ward {rnd.randint(1, 20)}, Main Road", rnd.choice(["General", "OBC", "SC", "ST", "OBC"]),
                 rnd.choice(["A+", "B+", "O+", "AB+", "B-", "O-"]), rnd.choice(["Hindi", "Hindi", "Urdu", "Punjabi"]))).lastrowid
            ids.append(sid)
            adm += 1
        student_ids[cid] = ids

    # Attendance for the last 25 school days (Mon-Sat)
    day = date.today()
    marked = 0
    while marked < 25:
        if day.weekday() != 6:
            for cid, ids in student_ids.items():
                for sid in ids:
                    status = rnd.choices(["P", "A", "L"], weights=[90, 7, 3])[0]
                    db.execute("INSERT INTO attendance(student_id, class_id, date, status) VALUES (?,?,?,?)",
                               (sid, cid, day.isoformat(), status))
            marked += 1
        day -= timedelta(days=1)

    # Exams and marks
    exam_defs = [("Periodic Test 1", "Term 1", 40, 1), ("Half Yearly Exam", "Term 1", 80, 2)]
    exam_ids = []
    for name, term, mx, order in exam_defs:
        exam_ids.append((db.execute(
            "INSERT INTO exams(name, term, academic_year, max_marks, display_order) VALUES (?,?,?,?,?)",
            (name, term, year, mx, order)).lastrowid, mx))
    db.execute("INSERT INTO exams(name, term, academic_year, max_marks, display_order) VALUES (?,?,?,?,?)",
               ("Periodic Test 2", "Term 2", year, 40, 3))
    db.execute("INSERT INTO exams(name, term, academic_year, max_marks, display_order) VALUES (?,?,?,?,?)",
               ("Annual Exam", "Term 2", year, 80, 4))
    for cid, ids in student_ids.items():
        for sid in ids:
            ability = rnd.uniform(0.35, 0.95)
            for eid, mx in exam_ids:
                for sname, subid in subjects.items():
                    if sname not in SUBJECT_TEACHER:
                        continue
                    if rnd.random() < 0.02:
                        db.execute("INSERT INTO marks(exam_id, student_id, subject_id, absent) VALUES (?,?,?,1)",
                                   (eid, sid, subid))
                        continue
                    score = max(0, min(mx, round(mx * rnd.gauss(ability, 0.1))))
                    db.execute("INSERT INTO marks(exam_id, student_id, subject_id, marks) VALUES (?,?,?,?)",
                               (eid, sid, subid, score))

    # NCERT chapters (Class 6), learning outcomes and progress
    for sname, (book, chapters) in CHAPTERS.items():
        subid = subjects[sname]
        prefix = {"Mathematics": "M", "Science": "S", "Social Science": "SS"}[sname]
        for no, (title, outcome) in enumerate(chapters, start=1):
            chid = db.execute("""INSERT INTO chapters(grade, subject_id, chapter_no, title, book, learning_outcomes,
                                 planned_periods) VALUES ('6',?,?,?,?,?,?)""",
                              (subid, no, title, book, outcome, rnd.choice([8, 10, 12, 14]))).lastrowid
            comp_id = db.execute("""INSERT INTO competencies(code, description, grade, subject_id, chapter_id, domain)
                                    VALUES (?,?, '6', ?, ?, ?)""",
                                 (f"{prefix}6.{no:02d}", outcome, subid, chid,
                                  "Conceptual Understanding")).lastrowid
            for section in ("A", "B"):
                cid = class_ids[("6", section)]
                if no <= 4 or (no == 5 and section == "A"):
                    status = "Completed" if no <= 4 else "In Progress"
                    start = date.today() - timedelta(days=150 - no * 25)
                    db.execute("""INSERT INTO chapter_progress(class_id, chapter_id, academic_year, status, teacher_id,
                                  start_date, end_date, periods_taken) VALUES (?,?,?,?,?,?,?,?)""",
                               (cid, chid, year, status, teacher_ids[SUBJECT_TEACHER[sname]], start.isoformat(),
                                (start + timedelta(days=20)).isoformat() if status == "Completed" else None,
                                rnd.randint(8, 14)))
                    for sid in student_ids[cid]:
                        db.execute("""INSERT INTO competency_assessments(student_id, competency_id, academic_year,
                                      term, level) VALUES (?,?,?, 'Term 1', ?)""",
                                   (sid, comp_id, year, rnd.choices([1, 2, 3, 4], weights=[10, 25, 45, 20])[0]))

    # Co-scholastic / life-skill indicators and remarks for Term 1
    indicators = [r["id"] for r in db.execute("SELECT id FROM indicators")]
    remarks = ["Excellent performance. Keep it up!", "Very good effort. Can do even better.",
               "Good progress. Needs more practice in Mathematics.", "Regular and well-behaved student.",
               "Participates actively in class activities."]
    for cid, ids in student_ids.items():
        for sid in ids:
            for iid in indicators:
                db.execute("""INSERT INTO indicator_assessments(student_id, indicator_id, academic_year, term, grade)
                              VALUES (?,?,?, 'Term 1', ?)""",
                           (sid, iid, year, rnd.choices("ABC", weights=[40, 45, 15])[0]))
            db.execute("""INSERT INTO report_remarks(student_id, academic_year, term, remarks)
                          VALUES (?,?, 'Term 1', ?)""", (sid, year, rnd.choice(remarks)))

    if not settings.get("school_address"):
        for key, value in [("school_name", "Govt. Model Senior Secondary School (Sample)"),
                           ("school_address", "Civil Lines, Sample City"), ("principal_name", "Dr. R. K. Mehta")]:
            db.execute("INSERT INTO settings(key, value) VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    db.commit()
