from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "task_manager_secret_key"


# Database connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create database tables
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():
    return redirect("/login")


# Register
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        password = generate_password_hash(password)

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )
            conn.commit()
            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already registered!"

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            conn.close()
            return redirect("/dashboard")

        conn.close()
        return "Invalid email or password!"

    return render_template("login.html")

# Add Task
@app.route("/add_task", methods=["POST"])
def add_task():

    if "user_id" not in session:
        return redirect("/login")

    title = request.form["title"]
    description = request.form["description"]
    due_date = request.form["due_date"]

    conn = get_db()

    conn.execute(
        """
        INSERT INTO tasks (user_id, title, description, due_date)
        VALUES (?, ?, ?, ?)
        """,
        (
            session["user_id"],
            title,
            description,
            due_date
        )
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# Edit Task
@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    task = conn.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, session["user_id"])
    ).fetchone()

    if not task:
        conn.close()
        return "Task not found!"

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        due_date = request.form["due_date"]

        conn.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, due_date = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                title,
                description,
                due_date,
                task_id,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    conn.close()

    return render_template("edit_task.html", task=task)


# Delete Task
@app.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# Complete Task
@app.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    conn.execute(
        """
        UPDATE tasks
        SET status = 'Completed'
        WHERE id = ? AND user_id = ?
        """,
        (task_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# Dashboard
# Dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    today = date.today().isoformat()

    total_tasks = len(tasks)
    completed_tasks = sum(
        1 for task in tasks
        if task["status"] == "Completed"
    )

    pending_tasks = sum(
        1 for task in tasks
        if task["status"] == "Pending"
        and (not task["due_date"] or task["due_date"] >= today)
    )

    overdue_tasks = sum(
        1 for task in tasks
        if task["status"] == "Pending"
        and task["due_date"]
        and task["due_date"] < today
    )

    return render_template(
        "dashboard.html",
        tasks=tasks,
        name=session["user_name"],
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        overdue_tasks=overdue_tasks,
        today=today
    )


# API - Get all tasks
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()

    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    task_list = []

    for task in tasks:
        task_list.append({
            "id": task["id"],
            "title": task["title"],
            "description": task["description"],
            "due_date": task["due_date"],
            "status": task["status"]
        })

    return jsonify(task_list)


# API - Add task
@app.route("/api/tasks", methods=["POST"])
def create_task_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    due_date = data.get("due_date")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO tasks (user_id, title, description, due_date)
        VALUES (?, ?, ?, ?)
        """,
        (
            session["user_id"],
            title,
            description,
            due_date
        )
    )

    conn.commit()

    task_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "message": "Task created successfully",
        "task_id": task_id
    }), 201


# API - Delete task
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task_api(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()

    cursor = conn.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, session["user_id"])
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "message": "Task deleted successfully"
    })


# API - Update task
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task_api(task_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    title = data.get("title")
    description = data.get("description")
    due_date = data.get("due_date")
    status = data.get("status")

    conn = get_db()

    cursor = conn.execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, due_date = ?, status = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            title,
            description,
            due_date,
            status,
            task_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({
        "message": "Task updated successfully"
    })

# Logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)