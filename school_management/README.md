# School Management System

A complete, offline school management system for Indian schools (CBSE / State boards). It runs in any web browser on
the school's own computer: no internet and no database server are needed, and all data stays in one file at the school.

## What it does

| Area | Features |
|---|---|
| **Admin dashboard** | Student, teacher and class counts, today's attendance, last 7 days' attendance chart, class-wise strength, list of classes whose attendance is not yet marked, NCERT syllabus completion %, quick-action buttons |
| **Student admissions** | Full admission record (admission no., DOB, parents, phone, category, blood group, APAAR ID, previous school…), automatic admission numbers, Excel bulk import with template, promote / transfer, mark as Left / TC issued / Passed Out |
| **Class & subject records** | Classes with sections, class teacher, room; subjects per class with subject teacher; class-wise strength (boys/girls) |
| **Teachers** | Staff records, qualification, designation, teaching load, links to their login |
| **Attendance** | One-click daily marking (everyone Present by default; tap A / L), corrections, monthly register, session-wide percentage, list of students below e.g. 75% |
| **Examinations** | Any number of exams (PT-1, Half Yearly…) with their own maximum marks; fast marks entry (Enter → next student, `AB` = absent, invalid marks flagged); class mark sheet with total, %, CBSE grade (A1–E), rank, pass / needs improvement; subject averages; school-wide result analysis |
| **Report cards** | Part A scholastic (all exams, totals, grades), Part B co-scholastic & life skills, Part C learning outcomes, attendance, rank, teacher remarks, signatures. Print from the browser, or download a PDF for one student or the whole class |
| **Learning outcomes & competencies** | Competencies per class and subject, linked to NCERT chapters; 4-level assessment (Beginning / Developing / Proficient / Advanced) per term; class report with % reaching Proficient or above |
| **NCERT chapter records** | Chapter list per class and subject (book, learning outcomes, planned periods), Excel import, class-wise progress (Not Started / In Progress / Completed, dates, periods taken, teacher, remarks) with completion % |
| **Assessment indicators** | Co-scholastic (Work Education, Art, Health & PE, Discipline) and holistic life-skill indicators (Communication, Collaboration, Critical Thinking…), editable, graded A–D per term |
| **PDF & Excel reports** | Student list / admission register, teacher list, class strength, attendance register, attendance summary, mark sheet, result analysis, NCERT progress, chapter list, competency report, indicators, report cards. Every list also has a **Print** button |
| **Search** | One search box finds students (name, admission no., father/mother, phone, APAAR), teachers, chapters and learning outcomes |
| **Safety** | Separate logins for admin and teachers, password hashing, CSRF protection, one-click backup and restore |

## Installing and starting

1. Install **Python 3.10 or newer** from <https://www.python.org/downloads/>. On Windows, tick **"Add Python to PATH"**.
2. Copy the `school_management` folder to the computer.
3. Start it:
   - **Windows:** double-click `start_windows.bat`
   - **Linux / Mac:** run `./start_linux_mac.sh`

   The first start takes a minute while it installs its parts. After that it starts in seconds.
4. The browser opens at <http://localhost:5000>. Log in with **admin / admin123** and **change the password**
   straight away (the dashboard reminds you until you do).

To try the system with sample classes, students, marks and NCERT chapters, click **Load sample data** on the
dashboard (only shown while the system is empty) or start with `start_windows.bat --demo`.

To use it from **several computers in the school**, start it with `--network` on one computer. Other computers then open
`http://<that-computer's-IP-address>:5000`.

Manual start without the scripts:

```bash
pip install -r requirements.txt
python run.py            # add --demo, --network, --port 8080 as needed
```

## Daily use (short guide for staff)

A fuller guide is built in: the **Help** page in the menu.

1. **Setup (admin, once):** School Settings → Subjects → Teachers → Classes (open each class to pick subject teachers) → User Logins.
2. **Admissions:** New Admission, or Import from Excel (download the template first).
3. **Attendance:** Mark Attendance → choose class → click A / L for absentees → Save.
4. **Exams:** create the exam once → Enter Marks (exam → class → subject) → Mark Sheet / Result Analysis.
5. **Curriculum:** NCERT Chapters → Chapter Progress → Learning Outcomes → Assess Competencies → Grade Indicators.
6. **Report cards:** Teacher Remarks → Report Cards → print, or download all as one PDF.
7. **Backup:** School Settings → Download Backup, every week, onto a pen drive.

## Notes

- All data is stored in `instance/school.db`. That file is the whole database, so back it up.
- Grades use the CBSE 8-point scale (A1 91–100 … D 33–40, E below 33). The pass percentage can be changed in Settings.
- Exams, attendance, assessments and remarks are kept per academic year. At year end: promote students (highest class
  first), then change the academic year and session dates in Settings.
- The sample NCERT chapter lists (Class 6 *Ganita Prakash*, *Curiosity*, *Exploring Society: India and Beyond*) are a
  starting point. Check them against the books your school uses.

## For developers

- Flask + SQLite (standard library `sqlite3`), reportlab for PDF, openpyxl for Excel. There are no JavaScript or CSS
  frameworks and no CDN, so it works fully offline.
- `school/services.py` holds all calculations, shared by the screens and the PDF/Excel exports. `school/exports.py`
  builds the files and `school/views/` holds one module per area.
- Tests: `pip install pytest && python -m pytest tests`
