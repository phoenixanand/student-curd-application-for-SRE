from app.models.database import get_db, row_to_dict


def get_all_students():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM students ORDER BY created_at DESC"
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def get_student_by_id(student_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    return row_to_dict(row)


def get_student_by_email(email):
    db = get_db()
    row = db.execute(
        "SELECT * FROM students WHERE email = ?", (email,)
    ).fetchone()
    return row_to_dict(row)


def create_student(name, email, age, grade):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO students (name, email, age, grade) VALUES (?, ?, ?, ?)",
        (name, email, age, grade),
    )
    db.commit()
    return get_student_by_id(cursor.lastrowid)


def update_student(student_id, fields: dict):
    if not fields:
        return get_student_by_id(student_id)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    set_clause += ", updated_at = CURRENT_TIMESTAMP"
    values = list(fields.values()) + [student_id]

    db = get_db()
    db.execute(
        f"UPDATE students SET {set_clause} WHERE id = ?", values
    )
    db.commit()
    return get_student_by_id(student_id)


def delete_student(student_id):
    db = get_db()
    affected = db.execute(
        "DELETE FROM students WHERE id = ?", (student_id,)
    ).rowcount
    db.commit()
    return affected > 0
