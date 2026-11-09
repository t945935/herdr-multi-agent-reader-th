import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "tasks.db"


def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(connect()) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
          description TEXT NOT NULL DEFAULT '', completed INTEGER NOT NULL DEFAULT 0)""")


def task(row):
    return {**dict(row), "completed": bool(row["completed"])} if row else None


def get_tasks():
    with closing(connect()) as conn:
        return [task(row) for row in conn.execute("SELECT * FROM tasks ORDER BY id")]


def get_task(task_id):
    with closing(connect()) as conn:
        return task(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())


def create_task(title, description=""):
    with closing(connect()) as conn, conn:
        cursor = conn.execute("INSERT INTO tasks(title,description) VALUES(?,?)", (title, description))
        return task(conn.execute("SELECT * FROM tasks WHERE id=?", (cursor.lastrowid,)).fetchone())


def update_task(task_id, **fields):
    if not set(fields) <= {"title", "description", "completed"}:
        raise ValueError("ไม่รู้จักฟิลด์ที่ต้องการอัปเดต")
    if not fields:
        return get_task(task_id)
    columns = ",".join(f"{key}=?" for key in fields)
    with closing(connect()) as conn, conn:
        cursor = conn.execute(f"UPDATE tasks SET {columns} WHERE id=?", (*fields.values(), task_id))
        return task(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()) if cursor.rowcount else None


def delete_task(task_id):
    with closing(connect()) as conn, conn:
        return conn.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount == 1
