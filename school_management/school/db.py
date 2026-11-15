"""Database layer: a single SQLite file, no server needed.

All tables are created automatically the first time the app starts.
"""
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS teachers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_code      TEXT UNIQUE,
    name          TEXT NOT NULL,
    gender        TEXT,
    dob           TEXT,
    phone         TEXT,
    email         TEXT,
    qualification TEXT,
    designation   TEXT,
    joining_date  TEXT,
    address       TEXT,
    status        TEXT NOT NULL DEFAULT 'Active',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    role          TEXT NOT NULL DEFAULT 'teacher',
    teacher_id    INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS classes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    grade            TEXT NOT NULL,
    section          TEXT NOT NULL DEFAULT 'A',
    class_teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    room             TEXT,
    UNIQUE (grade, section)
);

CREATE TABLE IF NOT EXISTS subjects (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    code TEXT
);

CREATE TABLE IF NOT EXISTS class_subjects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    UNIQUE (class_id, subject_id)
);

CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_no    TEXT UNIQUE NOT NULL,
    admission_date  TEXT,
    name            TEXT NOT NULL,
    gender          TEXT,
    dob             TEXT,
    class_id        INTEGER REFERENCES classes(id) ON DELETE SET NULL,
    roll_no         INTEGER,
    father_name     TEXT,
    mother_name     TEXT,
    guardian_phone  TEXT,
    email           TEXT,
    address         TEXT,
    category        TEXT,
    religion        TEXT,
    blood_group     TEXT,
    mother_tongue   TEXT,
    apaar_id        TEXT,
    previous_school TEXT,
    status          TEXT NOT NULL DEFAULT 'Active',
    leaving_date    TEXT,
    remarks         TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    class_id   INTEGER REFERENCES classes(id) ON DELETE SET NULL,
    date       TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('P', 'A', 'L')),
    UNIQUE (student_id, date)
);
CREATE INDEX IF NOT EXISTS idx_attendance_class_date ON attendance(class_id, date);

CREATE TABLE IF NOT EXISTS exams (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    term          TEXT,
    academic_year TEXT NOT NULL,
    max_marks     REAL NOT NULL DEFAULT 100,
    exam_date     TEXT,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS marks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id    INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    marks      REAL,
    absent     INTEGER NOT NULL DEFAULT 0,
    UNIQUE (exam_id, student_id, subject_id)
);

CREATE TABLE IF NOT EXISTS chapters (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    grade             TEXT NOT NULL,
    subject_id        INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    chapter_no        INTEGER NOT NULL,
    title             TEXT NOT NULL,
    book              TEXT,
    learning_outcomes TEXT,
    planned_periods   INTEGER,
    UNIQUE (grade, subject_id, chapter_no)
);

CREATE TABLE IF NOT EXISTS chapter_progress (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id      INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    chapter_id    INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'Not Started',
    teacher_id    INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    start_date    TEXT,
    end_date      TEXT,
    periods_taken INTEGER,
    remarks       TEXT,
    UNIQUE (class_id, chapter_id, academic_year)
);

CREATE TABLE IF NOT EXISTS competencies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT,
    description TEXT NOT NULL,
    grade       TEXT NOT NULL,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    chapter_id  INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    domain      TEXT
);

CREATE TABLE IF NOT EXISTS competency_assessments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    competency_id INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    term          TEXT NOT NULL,
    level         INTEGER CHECK (level BETWEEN 1 AND 4),
    UNIQUE (student_id, competency_id, academic_year, term)
);

CREATE TABLE IF NOT EXISTS indicators (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    area          TEXT NOT NULL,
    description   TEXT,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS indicator_assessments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    indicator_id  INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    term          TEXT NOT NULL,
    grade         TEXT,
    UNIQUE (student_id, indicator_id, academic_year, term)
);

CREATE TABLE IF NOT EXISTS report_remarks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    academic_year TEXT NOT NULL,
    term          TEXT NOT NULL,
    remarks       TEXT,
    UNIQUE (student_id, academic_year, term)
);
"""

DEFAULT_SETTINGS = {
    "school_name": "My School",
    "school_address": "",
    "school_phone": "",
    "school_email": "",
    "affiliation_no": "",
    "udise_code": "",
    "principal_name": "",
    "academic_year": "2026-27",
    "session_start": "2026-04-01",
    "session_end": "2027-03-31",
    "pass_percentage": "33",
}

# Co-scholastic and holistic (HPC-style) indicators created on first run.
DEFAULT_INDICATORS = [
    ("Work Education", "Co-Scholastic", "Skill-based and practical work activities"),
    ("Art Education", "Co-Scholastic", "Visual and performing arts"),
    ("Health & Physical Education", "Co-Scholastic", "Sports, yoga, fitness and health awareness"),
    ("Discipline", "Co-Scholastic", "Regularity, punctuality, behaviour and values"),
    ("Communication", "Life Skills", "Expresses ideas clearly in speech and writing"),
    ("Collaboration", "Life Skills", "Works well with others in groups"),
    ("Critical Thinking", "Life Skills", "Reasons, questions and solves problems"),
    ("Creativity", "Life Skills", "Shows original ideas and imagination"),
    ("Curiosity", "Life Skills", "Asks questions and shows interest in learning"),
    ("Responsibility", "Life Skills", "Takes care of tasks, materials and surroundings"),
]

DEFAULT_SUBJECTS = [
    ("English", "ENG"),
    ("Hindi", "HIN"),
    ("Mathematics", "MAT"),
    ("Science", "SCI"),
    ("Social Science", "SST"),
    ("Sanskrit", "SKT"),
    ("Computer Science", "CS"),
]


def connect(path):
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def scalar(sql, args=()):
    row = query(sql, args, one=True)
    return row[0] if row else None


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def init_db(path):
    """Create tables and first-run data (admin user, settings, defaults)."""
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, value))
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users(username, password_hash, full_name, role) VALUES (?, ?, ?, 'admin')",
                ("admin", generate_password_hash("admin123"), "Administrator"),
            )
        if conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0] == 0:
            for i, (name, area, desc) in enumerate(DEFAULT_INDICATORS):
                conn.execute(
                    "INSERT INTO indicators(name, area, description, display_order) VALUES (?, ?, ?, ?)",
                    (name, area, desc, i),
                )
        if conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 0:
            conn.executemany("INSERT INTO subjects(name, code) VALUES (?, ?)", DEFAULT_SUBJECTS)
        conn.commit()
    finally:
        conn.close()


def get_settings():
    if "settings" not in g:
        g.settings = {r["key"]: r["value"] for r in query("SELECT key, value FROM settings")}
        for key, value in DEFAULT_SETTINGS.items():
            g.settings.setdefault(key, value)
    return g.settings


def save_setting(key, value):
    execute("INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    g.pop("settings", None)
