from flask import Flask, request, redirect, url_for, session, g, send_from_directory, render_template, render_template_string
import sqlite3
import os
import secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "school.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

ALLOWED_FILES = {
    "pdf", "png", "jpg", "jpeg",
    "doc", "docx", "ppt", "pptx"
}


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            grade INTEGER NOT NULL,
            phone TEXT,
            transcript TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            grade INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS teacher_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            UNIQUE(teacher_id, class_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            file_name TEXT,
            material_type TEXT NOT NULL,
            grade INTEGER NOT NULL,
            teacher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS live_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            grade INTEGER NOT NULL,
            meeting_link TEXT,
            start_time TEXT,
            teacher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            file_name TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================
# HELPERS
# =========================

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_FILES
    )


def generate_student_id():
    conn = get_db()

    while True:
        student_id = "SSS-" + str(secrets.randbelow(900000) + 100000)

        existing = conn.execute(
            "SELECT id FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

        if not existing:
            conn.close()
            return student_id


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)

    return wrapper


def student_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("student_id"):
            return redirect(url_for("student_login"))
        return func(*args, **kwargs)

    return wrapper


def teacher_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("teacher_id"):
            return redirect(url_for("teacher_login"))
        return func(*args, **kwargs)

    return wrapper


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shinshicho Sinary Secondary School</title>
<link rel="stylesheet" href="/static/theme.css">
<script src="/static/theme.js"></script>
<style>
body {
    margin:0;
    font-family:Arial,sans-serif;
    background:#07111f;
    color:white;
}
.container {
    max-width:900px;
    margin:auto;
    padding:40px 20px;
    text-align:center;
}
.logo {
    width:90px;
    height:90px;
    border-radius:20px;
    background:#0878ff;
    display:flex;
    align-items:center;
    justify-content:center;
    margin:30px auto;
    font-size:32px;
    font-weight:bold;
}
h1 {
    color:#55aaff;
}
p {
    color:#b8c7d9;
}
.buttons {
    display:grid;
    gap:15px;
    max-width:400px;
    margin:30px auto;
}
a {
    display:block;
    padding:15px;
    border-radius:12px;
    background:#0878ff;
    color:white;
    text-decoration:none;
    font-weight:bold;
}
a.secondary {
    background:#13243a;
}
</style>
</head>
<body>
<div class="container">

<div class="logo">SSS</div>

<h1>Shinshicho Sinary Secondary School</h1>

<p>Student Learning & School Management System</p>
<button class="theme-button" onclick="toggleDarkMode()">🌙 Dark Mode</button>
<div class="buttons">
<a href="/register">Student Registration</a>
<a href="/student/login">Student Login</a>
<a href="/announcements">📢 Announcements</a>
<a href="/teacher/login">Teacher Login</a>
<a class="secondary" href="/admin/login">Admin Login</a>
</div>

<p>Grades 9 • 10 • 11 • 12</p>

</div>
</body>
</html>
""")


# =========================
# STUDENT REGISTRATION
# =========================
@app.route("/announcements")
def announcements():

    conn = get_db()

    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
python -m py_compile app.py
<title>School Announcements</title>
<link rel="stylesheet" href="/static/theme.css">
<script src="/static/theme.js"></script>
<style>
body {
    margin:0;
    font-family:Arial,sans-serif;
    background:#07111f;
    color:white;
}

.container {
    max-width:800px;
    margin:auto;
    padding:30px 20px;
}

h1 {
    color:#55aaff;
}

.announcement {
    background:#102238;
    padding:18px;
    margin:15px 0;
    border-radius:12px;
}

.date {body.light {
    background:#f4f7fb;
    color:#172033;
}

body.light h1 {
    color:#0878ff;
}

body.light .announcement {
    background:white;
    color:#172033;
}

body.light .date {
    color:#667085;
}
    color:#8fa8c2;
    font-size:13px;
}

a {
    color:#55aaff;
}body.light {
    background:#f4f7fb;
    color:#172033;
}

body.light h1 {
    color:#0878ff;
}

body.light .announcement {
    background:white;
    color:#172033;
}

body.light .date {
    color:#667085;
}
</style>
</head>

<body>

<div class="container">

<h1>📢 School Announcements</h1>
<button class="theme-button" onclick="toggleDarkMode()">🌙 Dark Mode</button>

{% for announcement in announcements %}

<div class="announcement">

<h2>{{ announcement["title"] }}</h2>

<p>{{ announcement["content"] }}</p>

<p class="date">
{{ announcement["created_at"] }}
</p>

</div>

{% else %}

<p>No announcements yet.</p>

{% endfor %}

<p>
<a href="/">← Back to Home</a>
</p>

</div>
<script>
function toggleDarkMode() {
    document.body.classList.toggle("light");
}
</script>
</body>
</html>
""", announcements=announcements)
@app.route("/register", methods=["GET", "POST"])
def register():

    message = ""

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        grade = request.form.get("grade", "")
        phone = request.form.get("phone", "").strip()

        transcript = request.files.get("transcript")

        if not full_name or not username or not password or not grade:
            message = "Please complete all required fields."

        elif grade not in ["9", "10", "11", "12"]:
            message = "Please select Grade 9, 10, 11 or 12."

        elif not transcript or transcript.filename == "":
            message = "Please upload your transcript."

        elif not allowed_file(transcript.filename):
            message = "Unsupported transcript file."

        else:
            filename = secure_filename(transcript.filename)

            unique_name = (
                "transcript_"
                + secrets.token_hex(8)
                + "_"
                + filename
            )

            transcript.save(
                os.path.join(UPLOAD_DIR, unique_name)
            )

            conn = get_db()

            try:
                conn.execute("""
                    INSERT INTO students
                    (full_name, username, password, grade, phone, transcript)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    full_name,
                    username,
                    generate_password_hash(password),
                    int(grade),
                    phone,
                    unique_name
                ))

                conn.commit()
                message = (
                    "Registration submitted successfully. "
                    "Please wait for admin approval."
                )

            except sqlite3.IntegrityError:
                message = "That username is already registered."

            finally:
                conn.close()

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Registration</title>
<style>
body {.theme-button {
    position: fixed;
    top: 15px;
    left: 15px;
    z-index: 1000;
}
    background:#07111f;
    color:white;
    font-family:Arial;
}
.box {
    max-width:500px;
    margin:30px auto;
    padding:25px;
}
input,select {
    width:100%;
    box-sizing:border-box;
    padding:13px;
    margin:8px 0 15px;
    border-radius:9px;
    border:1px solid #29415f;
    background:#101f32;
    color:white;
}
button {
    width:100%;
    padding:14px;
    background:#0878ff;
    color:white;
    border:0;
    border-radius:9px;
    font-weight:bold;
}
.message {
    padding:12px;
    background:#13243a;
    border-radius:8px;
    margin-bottom:15px;
}
a {color:#55aaff;}
</style>
</head>
<body>
<div class="box">

<h1>Student Registration</h1>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<form method="POST" enctype="multipart/form-data">

<label>Full Name</label>
<input name="full_name" required>

<label>Username</label>
<input name="username" required>

<label>Password</label>
<input type="password" name="password" required>

<label>Grade</label>
<select name="grade" required>
<option value="">Select Grade</option>
<option value="9">Grade 9</option>
<option value="10">Grade 10</option>
<option value="11">Grade 11</option>
<option value="12">Grade 12</option>
</select>

<label>Phone</label>
<input name="phone">

<label>Transcript</label>
<input type="file" name="transcript" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" required>

<button type="submit">Submit Registration</button>

</form>

<p><a href="/">Back to home</a></p>

</div>
</body>
</html>
""", message=message)


# =========================
# STUDENT LOGIN
# =========================

@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    message = ""

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        conn = get_db()

        student = conn.execute(
            "SELECT * FROM students WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if student and check_password_hash(
            student["password"], password
        ):

            if student["status"] != "approved":
                message = (
                    "Your account is still waiting for admin approval."
                )
            else:
                session.clear()
                session["student_id"] = student["id"]
                return redirect(url_for("student_dashboard"))

        else:
            message = "Invalid username or password."

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Login</title>
<style>
body {
    background:#07111f;
    color:white;
    font-family:Arial;
}
.box {
    max-width:400px;
    margin:60px auto;
    padding:25px;
}
input {
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin:8px 0 15px;
    background:#101f32;
    color:white;
    border:1px solid #29415f;
    border-radius:9px;
}
button {
    width:100%;
    padding:14px;
    background:#0878ff;
    color:white;
    border:0;
    border-radius:9px;
}
.message {
    background:#13243a;
    padding:12px;
    border-radius:8px;
}
a {color:#55aaff;}
</style>
</head>
<body>
<div class="box">
<h1>Student Login</h1>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<form method="POST">
<input name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button>Login</button>
</form>

<p><a href="/register">Register</a></p>
<p><a href="/">Home</a></p>

</div>
</body>
</html>
""", message=message)


# =========================
# STUDENT DASHBOARD
# =========================

@app.route("/student")
@student_required
def student_dashboard():

    conn = get_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (session["student_id"],)
    ).fetchone()

    materials = conn.execute("""
        SELECT * FROM materials
        WHERE grade = ?
        ORDER BY created_at DESC
    """, (student["grade"],)).fetchall()

    live_classes = conn.execute("""
        SELECT * FROM live_classes
        WHERE grade = ?
        ORDER BY start_time
    """, (student["grade"],)).fetchall()

    conn.close()

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Dashboard</title>
<style>
body {
    margin:0;
    background:#07111f;
    color:white;
    font-family:Arial;
}
header {
    padding:20px;
    background:#0b1b30;
}
.container {
    max-width:900px;
    margin:auto;
    padding:20px;
}
.card {
    background:#10233a;
    padding:18px;
    border-radius:12px;
    margin:12px 0;
}
.badge {
    color:#55aaff;
}
a {
    color:#55aaff;
}
.logout {
    float:right;
}
</style>
</head>
<body>

<header>
<strong>Shinshicho Sinary Secondary School</strong>
<a class="logout" href="/logout">Logout</a>
</header>

<div class="container">

<h1>Welcome, {{ student["full_name"] }}</h1>

<div class="card">
<strong>Student ID:</strong>
{{ student["student_id"] or "Waiting for admin approval" }}
<br>
<strong>Grade:</strong> {{ student["grade"] }}
</div>

<h2>Learning Materials</h2>

{% for material in materials %}
<div class="card">
<h3>{{ material["title"] }}</h3>
<p>{{ material["description"] or "" }}</p>
<p class="badge">{{ material["material_type"] }}</p>

{% if material["file_name"] %}
<p>
<a href="/uploads/{{ material['file_name'] }}">
Open / Download
</a>
</p>
{% endif %}
</div>
{% else %}
<p>No materials available yet.</p>
{% endfor %}

<h2>Live Classes</h2>

{% for live in live_classes %}
<div class="card">
<h3>{{ live["title"] }}</h3>
<p>{{ live["description"] or "" }}</p>
<p>{{ live["start_time"] or "" }}</p>

{% if live["meeting_link"] %}
<a href="{{ live['meeting_link'] }}" target="_blank">
Join Live Class
</a>
{% endif %}
</div>
{% else %}
<p>No live classes scheduled.</p>
{% endfor %}

</div>
</body>
</html>
""", student=student, materials=materials, live_classes=live_classes)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =========================
# UPLOADS
# =========================

@app.route("/uploads/<filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)
# =========================
# ADMIN AUTHENTICATION
# =========================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    message = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if admin and check_password_hash(
            admin["password"],
            password
        ):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]

            return redirect(url_for("admin_dashboard"))

        message = "Invalid admin username or password."

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Login</title>

<style>
body {
    margin:0;
    background:#050d18;
    color:white;
    font-family:Arial,sans-serif;
}

.box {
    max-width:420px;
    margin:70px auto;
    padding:30px;
}

.logo {
    width:75px;
    height:75px;
    margin:auto auto 25px;
    border-radius:18px;
    background:#0878ff;
    display:flex;
    justify-content:center;
    align-items:center;
    font-weight:bold;
    font-size:24px;
}

h1 {
    text-align:center;
}

.subtitle {
    text-align:center;
    color:#9db0c7;
    margin-bottom:30px;
}

input {
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin:8px 0 18px;
    background:#101e30;
    color:white;
    border:1px solid #29425f;
    border-radius:10px;
}

button {
    width:100%;
    padding:14px;
    background:#0878ff;
    color:white;
    border:0;
    border-radius:10px;
    font-weight:bold;
    font-size:16px;
}

.message {
    background:#3a1720;
    color:#ffb8c3;
    padding:12px;
    border-radius:9px;
    margin-bottom:15px;
}

a {
    color:#55aaff;
}
</style>
</head>

<body>

<div class="box">

<div class="logo">SSS</div>

<h1>Admin Login</h1>

<div class="subtitle">
Shinshicho Sinary Secondary School
</div>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<form method="POST">

<label>Admin Username</label>
<input
    name="username"
    autocomplete="username"
    required
>

<label>Password</label>
<input
    type="password"
    name="password"
    autocomplete="current-password"
    required
>

<button type="submit">
Sign in securely
</button>

</form>

<p>
<a href="/">← Back to school home</a>
</p>

</div>
</body>
""", message=message)


@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id", None)
    session.pop("admin_username", None)

    return redirect(url_for("admin_login"))


# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin/announcements", methods=["GET", "POST"])
@admin_required
def admin_announcements():
    conn = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if title and content:
            conn.execute(
                "INSERT INTO announcements (title, content) VALUES (?, ?)",
                (title, content)
            )
            conn.commit()

    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template_string("""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Announcements</title>
<style>
body {
    font-family:Arial,sans-serif;
    background:#07111f;
    color:white;
    padding:20px;
}
.container {
    max-width:800px;
    margin:auto;
}
input, textarea {
    width:100%;
    padding:12px;
    margin:8px 0;
    box-sizing:border-box;
    border-radius:8px;
    border:1px solid #29425f;
    background:#102238;
    color:white;
}
button {
    padding:12px 18px;
    border:0;
    border-radius:8px;
    background:#0878ff;
    color:white;
    font-weight:bold;
}
.announcement {
    background:#102238;
    padding:18px;
    margin-top:15px;
    border-radius:10px;
}
a {
    color:#55aaff;
}
</style>
</head>

<body>
<div class="container">

<h1>School Announcements</h1>

<form method="POST">
    <input name="title" placeholder="Announcement title" required>

    <textarea name="content"
              rows="5"
              placeholder="Write your announcement..."
              required></textarea>

    <button type="submit">Publish Announcement</button>
</form>

<hr>

{% for announcement in announcements %}
<div class="announcement">
    <h2>{{ announcement["title"] }}</h2>
    <p>{{ announcement["content"] }}</p>
    <small>{{ announcement["created_at"] }}</small>
</div>
{% else %}
<p>No announcements yet.</p>
{% endfor %}

<p><a href="/admin">← Back to Admin Dashboard</a></p>

</div>
</body>
</html>
""", announcements=announcements)
@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = get_db()

    total_students = conn.execute(
        "SELECT COUNT(*) AS count FROM students"
    ).fetchone()["count"]

    pending_students = conn.execute(
        "SELECT COUNT(*) AS count FROM students WHERE status = 'pending'"
    ).fetchone()["count"]

    approved_students = conn.execute(
        "SELECT COUNT(*) AS count FROM students WHERE status = 'approved'"
    ).fetchone()["count"]

    rejected_students = conn.execute(
        "SELECT COUNT(*) AS count FROM students WHERE status = 'rejected'"
    ).fetchone()["count"]

    total_teachers = conn.execute(
        "SELECT COUNT(*) AS count FROM teachers"
    ).fetchone()["count"]

    conn.close()

    return render_template_string("""
<!doctype html>
<html>

<head>

<meta name="viewport" content="width=device-width,initial-scale=1">

<title>Admin Dashboard</title>

<style>

* {
    box-sizing:border-box;
}

body {
    margin:0;
    background:#050d18;
    color:white;
    font-family:Arial,sans-serif;
}

header {
    background:#0b1c31;
    padding:18px 20px;
    border-bottom:1px solid #1c3654;
}

.header-inner {
    max-width:1100px;
    margin:auto;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.brand {
    color:#55aaff;
    font-weight:bold;
}

.logout {
    color:#ff9aa9;
    text-decoration:none;
}

.container {
    max-width:1100px;
    margin:auto;
    padding:25px 18px;
}

h1 {
    margin-bottom:5px;
}

.subtitle {
    color:#91a5bc;
}

.stats {
    display:grid;
    grid-template-columns:
        repeat(auto-fit,minmax(180px,1fr));
    gap:15px;
    margin:25px 0;
}

.stat {
    background:#10233a;
    border:1px solid #1d3958;
    padding:20px;
    border-radius:14px;
}

.stat-number {
    font-size:30px;
    font-weight:bold;
    color:#55aaff;
}

.stat-title {
    color:#a7b8ca;
    margin-top:6px;
}

.actions {
    display:grid;
    grid-template-columns:
        repeat(auto-fit,minmax(200px,1fr));
    gap:14px;
}

.action {
    background:#10233a;
    border:1px solid #1d3958;
    border-radius:14px;
    padding:20px;
}

.action h3 {
    margin-top:0;
}

.action p {
    color:#9db0c7;
}

.button {
    display:inline-block;
    padding:11px 15px;
    background:#0878ff;
    color:white;
    border-radius:9px;
    text-decoration:none;
    font-weight:bold;
}

.warning {
    border-color:#725d20;
}

</style>

</head>

<body>

<header>

<div class="header-inner">

<div class="brand">
SHINSHICHO SINARY SCHOOL
</div>

<a class="logout" href="/admin/logout">
Logout
</a>

</div>

</header>

<div class="container">

<h1>Admin Dashboard</h1>

<p class="subtitle">
Welcome, {{ session["admin_username"] }}
</p>

<div class="stats">

<div class="stat">
<div class="stat-number">
{{ total_students }}
</div>
<div class="stat-title">
Total Students
</div>
</div>

<div class="stat warning">
<div class="stat-number">
{{ pending_students }}
</div>
<div class="stat-title">
Pending Approval
</div>
</div>

<div class="stat">
<div class="stat-number">
{{ approved_students }}
</div>
<div class="stat-title">
Approved Students
</div>
</div>

<div class="stat">
<div class="stat-number">
{{ rejected_students }}
</div>
<div class="stat-title">
Rejected Students
</div>
</div>

<div class="stat">
<div class="stat-number">
{{ total_teachers }}
</div>
<div class="stat-title">
Teachers
</div>
</div>

</div>


<h2>Administration</h2>

<div class="actions">

<div class="action">

<h3>Student Registrations</h3>

<p>
Review new registrations and uploaded transcripts.
</p>

<a class="button" href="/admin/students">
Manage Students
</a>

</div>
<div class="action">

<h3>Announcements</h3>

<p>
Create and publish school announcements.
</p>

<a class="button" href="/admin/announcements">
📢 Announcements
</a>

</div>

<div class="action">

<h3>Teachers</h3>

<p>
Approve teachers and assign their classes.
</p>

<a class="button" href="/admin/teachers">
Manage Teachers
</a>

</div>


<div class="action">

<h3>Learning Materials</h3>

<p>
Manage notes, exams, assignments and worksheets.
</p>

<a class="button" href="/admin/materials">
Manage Materials
</a>

</div>


<div class="action">

<h3>Live Classes</h3>

<p>
Create and manage Grade 9–12 live classes.
</p>

<a class="button" href="/admin/live-classes">
Manage Live Classes
</a>

</div>

</div>

</div>

</body>
</html>
""",
        total_students=total_students,
        pending_students=pending_students,
        approved_students=approved_students,
        rejected_students=rejected_students,
        total_teachers=total_teachers
    )


# =========================
# ADMIN STUDENT MANAGEMENT
# =========================

@app.route("/admin/students")
@admin_required
def admin_students():

    conn = get_db()

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY
            CASE status
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                ELSE 3
            END,
            created_at DESC
    """).fetchall()

    conn.close()

    return render_template_string("""
<!doctype html>

<html>

<head>

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>Student Registrations</title>

<style>

body {
    margin:0;
    background:#050d18;
    color:white;
    font-family:Arial,sans-serif;
}

header {
    padding:18px;
    background:#0b1c31;
}

.container {
    max-width:1100px;
    margin:auto;
    padding:20px;
}

.card {
    background:#10233a;
    border:1px solid #1d3958;
    padding:20px;
    border-radius:14px;
    margin-bottom:16px;
}

.pending {
    border-left:5px solid #ffbd3d;
}

.approved {
    border-left:5px solid #38d996;
}

.rejected {
    border-left:5px solid #ff647c;
}

.info {
    color:#aabbd0;
}

.status {
    display:inline-block;
    padding:6px 10px;
    border-radius:20px;
    background:#18314d;
}

button {
    border:0;
    border-radius:8px;
    padding:11px 15px;
    color:white;
    font-weight:bold;
    margin:4px;
}

.approve {
    background:#0878ff;
}

.reject {
    background:#8d2639;
}

a {
    color:#55aaff;
}

.back {
    display:inline-block;
    margin-bottom:20px;
}

</style>

</head>

<body>

<header>
<strong>Student Registration Management</strong>
</header>

<div class="container">

<a class="back" href="/admin">
← Admin Dashboard
</a>

<h1>Students</h1>

{% for student in students %}

<div class="card {{ student['status'] }}">

<h2>
{{ student["full_name"] }}
</h2>

<p class="info">
Username: {{ student["username"] }}
</p>

<p class="info">
Grade: {{ student["grade"] }}
</p>

<p class="info">
Phone: {{ student["phone"] or "Not provided" }}
</p>

<p>
Status:
<span class="status">
{{ student["status"] }}
</span>
</p>

{% if student["student_id"] %}
<p>
<strong>Student ID:</strong>
{{ student["student_id"] }}
</p>
{% endif %}

{% if student["transcript"] %}

<p>
<a
href="/uploads/{{ student['transcript'] }}"
target="_blank"
>
📄 View Transcript
</a>
</p>

{% endif %}


{% if student["status"] == "pending" %}

<form
method="POST"
action="/admin/students/{{ student['id'] }}/approve"
style="display:inline"
>

<button class="approve">
✓ Approve
</button>

</form>


<form
method="POST"
action="/admin/students/{{ student['id'] }}/reject"
style="display:inline"
>

<button
class="reject"
onclick="return confirm('Reject this student registration?')"
>
✕ Reject
</button>

</form>

{% endif %}

</div>

{% else %}

<p>No student registrations yet.</p>

{% endfor %}

</div>

</body>

</html>
""", students=students)


# =========================
# APPROVE STUDENT
# =========================

@app.route(
    "/admin/students/<int:student_id>/approve",
    methods=["POST"]
)
@admin_required
def approve_student(student_id):

    conn = get_db()

    student = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        return "Student not found", 404

    student_id_number = student["student_id"]

    if not student_id_number:
        student_id_number = generate_student_id()

    conn.execute("""
        UPDATE students
        SET status = 'approved',
            student_id = ?
        WHERE id = ?
    """, (
        student_id_number,
        student_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_students"))


# =========================
# REJECT STUDENT
# =========================

@app.route(
    "/admin/students/<int:student_id>/reject",
    methods=["POST"]
)
@admin_required
def reject_student(student_id):

    conn = get_db()

    conn.execute("""
        UPDATE students
        SET status = 'rejected'
        WHERE id = ?
    """, (student_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_students"))


# =========================
# ADMIN SETUP PAGE
# =========================

@app.route("/setup-admin", methods=["GET", "POST"])
def setup_admin():

    conn = get_db()

    existing = conn.execute(
        "SELECT COUNT(*) AS count FROM admins"
    ).fetchone()["count"]

    conn.close()

    if existing > 0:
        return """
        <h2>Admin setup is already completed.</h2>
        <p><a href="/admin/login">Go to Admin Login</a></p>
        """

    message = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 4:
            message = "Username must be at least 4 characters."

        elif len(password) < 8:
            message = "Password must be at least 8 characters."

        else:

            conn = get_db()

            conn.execute("""
                INSERT INTO admins
                (username, password)
                VALUES (?, ?)
            """, (
                username,
                generate_password_hash(password)
            ))

            conn.commit()
            conn.close()

            return redirect(url_for("admin_login"))

    return render_template_string("""
<!doctype html>

<html>

<head>

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>Create Admin</title>

<style>

body {
    background:#050d18;
    color:white;
    font-family:Arial;
}

.box {
    max-width:420px;
    margin:60px auto;
    padding:25px;
}

input {
    width:100%;
    box-sizing:border-box;
    padding:14px;
    margin:8px 0 18px;
    background:#102033;
    color:white;
    border:1px solid #29415f;
    border-radius:9px;
}

button {
    width:100%;
    padding:14px;
    background:#0878ff;
    color:white;
    border:0;
    border-radius:9px;
    font-weight:bold;
}

.message {
    background:#3a1720;
    padding:12px;
    border-radius:8px;
}

</style>

</head>

<body>

<div class="box">

<h1>Create School Admin</h1>

<p>
Create the first administrator account.
</p>

{% if message %}
<div class="message">
{{ message }}
</div>
{% endif %}

<form method="POST">

<input
name="username"
placeholder="Admin username"
required
>

<input
type="password"
name="password"
placeholder="Password (8+ characters)"
required
>

<button>
Create Admin
</button>

</form>

</div>

</body>

</html>
""", message=message)
# =========================
# TEACHER MANAGEMENT
# =========================

@app.route("/teacher/register", methods=["GET", "POST"])
def teacher_register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()

        if not full_name or not username or not password or not subject:
            return render_template(
                "teacher_register.html",
                error="Please fill in all required fields."
            )

        if len(password) < 8:
            return render_template(
                "teacher_register.html",
                error="Password must be at least 8 characters."
            )

        db = get_db()

        existing = db.execute(
            "SELECT id FROM teachers WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            return render_template(
                "teacher_register.html",
                error="That username is already registered."
            )

        password_hash = generate_password_hash(password)

        db.execute(
            """
            INSERT INTO teachers
            (full_name, username, password, password_hash, phone, subject, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                full_name,
                username,
                password_hash,
                password_hash,
                phone,
                subject
            )
        )

        db.commit()

        return render_template(
            "teacher_register.html",
            success="Registration submitted. An administrator must approve your account."
        )

    return render_template("teacher_register.html")


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()

        teacher = db.execute(
            "SELECT * FROM teachers WHERE username = ?",
            (username,)
        ).fetchone()

        if teacher and check_password_hash(
            teacher["password_hash"],
            password
        ):
            if teacher["status"] != "approved":
                return render_template(
                    "teacher_login.html",
                    error="Your teacher account has not been approved yet."
                )

            session.clear()
            session["teacher_id"] = teacher["id"]
            session["teacher_username"] = teacher["username"]

            return redirect(url_for("teacher_dashboard"))

        return render_template(
            "teacher_login.html",
            error="Invalid teacher username or password."
        )

    return render_template("teacher_login.html")


@app.route("/teacher")
@teacher_required
def teacher_dashboard():
    db = get_db()

    teacher = db.execute(
        "SELECT * FROM teachers WHERE id = ?",
        (session["teacher_id"],)
    ).fetchone()

    classes = db.execute(
        """
        SELECT classes.*
        FROM classes
        JOIN teacher_classes
        ON classes.id = teacher_classes.class_id
        WHERE teacher_classes.teacher_id = ?
        ORDER BY classes.grade, classes.name
        """,
        (teacher["id"],)
    ).fetchall()

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        classes=classes
    )


@app.route("/admin/teachers")
@admin_required
def admin_teachers():
    db = get_db()

    teachers = db.execute(
        """
        SELECT *
        FROM teachers
        ORDER BY
            CASE status
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                ELSE 3
            END,
            id DESC
        """
    ).fetchall()

    return render_template(
        "admin_teachers.html",
        teachers=teachers
    )


@app.route("/admin/teachers/<int:teacher_id>/approve", methods=["POST"])
@admin_required
def approve_teacher(teacher_id):
    db = get_db()

    teacher = db.execute(
        "SELECT * FROM teachers WHERE id = ?",
        (teacher_id,)
    ).fetchone()

    if teacher:
        db.execute(
            "UPDATE teachers SET status = 'approved' WHERE id = ?",
            (teacher_id,)
        )
        db.commit()

    return redirect(url_for("admin_teachers"))


@app.route("/admin/teachers/<int:teacher_id>/reject", methods=["POST"])
@admin_required
def reject_teacher(teacher_id):
    db = get_db()

    teacher = db.execute(
        "SELECT * FROM teachers WHERE id = ?",
        (teacher_id,)
    ).fetchone()

    if teacher:
        db.execute(
            "UPDATE teachers SET status = 'rejected' WHERE id = ?",
            (teacher_id,)
        )
        db.commit()

    return redirect(url_for("admin_teachers"))


@app.route("/teacher/logout")
def teacher_logout():
    session.pop("teacher_username", None)
    return redirect(url_for("home"))
# =========================
# CLASS MANAGEMENT
# =========================

@app.route("/admin/classes")
@admin_required
def admin_classes():
    db = get_db()

    classes = db.execute(
        """
        SELECT *
        FROM classes
        ORDER BY grade, name
        """
    ).fetchall()

    teachers = db.execute(
        """
        SELECT *
        FROM teachers
        WHERE status = 'approved'
        ORDER BY full_name
        """
    ).fetchall()

    assignments = db.execute(
        """
        SELECT
            teacher_classes.id,
            teacher_classes.teacher_id,
            teacher_classes.class_id,
            teachers.full_name AS teacher_name,
            classes.name AS class_name,
            classes.grade AS grade
        FROM teacher_classes
        JOIN teachers
            ON teachers.id = teacher_classes.teacher_id
        JOIN classes
            ON classes.id = teacher_classes.class_id
        ORDER BY classes.grade, classes.name, teachers.full_name
        """
    ).fetchall()

    return render_template(
        "admin_classes.html",
        classes=classes,
        teachers=teachers,
        assignments=assignments
    )


@app.route("/admin/classes/add", methods=["POST"])
@admin_required
def add_class():
    name = request.form.get("name", "").strip()
    grade = request.form.get("grade", "").strip()

    if name and grade in {"9", "10", "11", "12"}:
        db = get_db()

        existing = db.execute(
            "SELECT id FROM classes WHERE name = ? AND grade = ?",
            (name, int(grade))
        ).fetchone()

        if not existing:
            db.execute(
                "INSERT INTO classes (name, grade) VALUES (?, ?)",
                (name, int(grade))
            )
            db.commit()

    return redirect(url_for("admin_classes"))


@app.route("/admin/classes/<int:class_id>/delete", methods=["POST"])
@admin_required
def delete_class(class_id):
    db = get_db()

    db.execute(
        "DELETE FROM teacher_classes WHERE class_id = ?",
        (class_id,)
    )

    db.execute(
        "DELETE FROM classes WHERE id = ?",
        (class_id,)
    )

    db.commit()

    return redirect(url_for("admin_classes"))


@app.route("/admin/classes/assign", methods=["POST"])
@admin_required
def assign_teacher():
    teacher_id = request.form.get("teacher_id")
    class_id = request.form.get("class_id")

    if teacher_id and class_id:
        db = get_db()

        existing = db.execute(
            """
            SELECT id
            FROM teacher_classes
            WHERE teacher_id = ? AND class_id = ?
            """,
            (teacher_id, class_id)
        ).fetchone()

        if not existing:
            db.execute(
                """
                INSERT INTO teacher_classes
                (teacher_id, class_id)
                VALUES (?, ?)
                """,
                (teacher_id, class_id)
            )
            db.commit()

    return redirect(url_for("admin_classes"))


@app.route(
    "/admin/classes/assignment/<int:assignment_id>/delete",
    methods=["POST"]
)
@admin_required
def remove_teacher_assignment(assignment_id):
    db = get_db()

    db.execute(
        "DELETE FROM teacher_classes WHERE id = ?",
        (assignment_id,)
    )

    db.commit()

@app.route("/admin/materials", methods=["GET", "POST"])
@admin_required
def admin_materials():
    db = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        material_type = request.form.get("material_type", "").strip()
        grade = request.form.get("grade", "").strip()
        file = request.files.get("file")

        if not title or not material_type or not grade:
            return "Title, material type and grade are required.", 400

        file_name = None

        if file and file.filename:
            if not allowed_file(file.filename):
                return "File type not allowed.", 400

            file_name = file.filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], file_name))

        db.execute(
            """
            INSERT INTO materials
            (title, description, file_name, material_type, grade, teacher_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                file_name,
                material_type,
                int(grade),
                None
            )
        )

        db.commit()
        return redirect(url_for("admin_materials"))

    materials = db.execute(
        """
        SELECT materials.*, teachers.full_name AS teacher_name
        FROM materials
        LEFT JOIN teachers ON materials.teacher_id = teachers.id
        ORDER BY materials.created_at DESC
        """
    ).fetchall()

    return render_template(
        "admin_materials.html",
        materials=materials
    )


@app.route("/admin/materials/<int:material_id>/delete", methods=["POST"])
@admin_required
def admin_delete_material(material_id):
    db = get_db()

    material = db.execute(
        "SELECT * FROM materials WHERE id = ?",
        (material_id,)
    ).fetchone()

    if material:
        if material["file_name"]:
            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                material["file_name"]
            )

            if os.path.exists(file_path):
                os.remove(file_path)

        db.execute(
            "DELETE FROM materials WHERE id = ?",
            (material_id,)
        )
        db.commit()

    return redirect(url_for("admin_materials"))
# =========================
# INITIALIZE
# =========================

init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
