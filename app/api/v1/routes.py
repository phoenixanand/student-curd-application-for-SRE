from flask import Blueprint, jsonify, request, current_app
from app.models import student as student_model

api_v1 = Blueprint("api_v1", __name__)

ALLOWED_UPDATE_FIELDS = {"name", "email", "age", "grade"}


def _validate_student_payload(data, require_all=True):
    required = {"name", "email", "age", "grade"}
    errors = []

    if require_all:
        missing = required - set(data.keys())
        if missing:
            return None, f"Missing required fields: {', '.join(sorted(missing))}"

    cleaned = {}

    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            errors.append("'name' must not be empty")
        else:
            cleaned["name"] = name

    if "email" in data:
        email = str(data["email"]).strip().lower()
        if "@" not in email or "." not in email:
            errors.append("'email' is not valid")
        else:
            cleaned["email"] = email

    if "age" in data:
        try:
            age = int(data["age"])
            if not (1 <= age <= 120):
                raise ValueError
            cleaned["age"] = age
        except (ValueError, TypeError):
            errors.append("'age' must be an integer between 1 and 120")

    if "grade" in data:
        grade = str(data["grade"]).strip()
        if not grade:
            errors.append("'grade' must not be empty")
        else:
            cleaned["grade"] = grade

    if errors:
        return None, "; ".join(errors)

    return cleaned, None


@api_v1.route("/healthcheck", methods=["GET"])
def healthcheck():
    current_app.logger.debug("Healthcheck requested")
    return jsonify({"status": "ok", "version": "v1"}), 200


@api_v1.route("/students", methods=["GET"])
def get_students():
    current_app.logger.info("GET /students — fetching all students")
    students = student_model.get_all_students()
    current_app.logger.info("Returned %d student(s)", len(students))
    return jsonify({"count": len(students), "students": students}), 200


@api_v1.route("/students", methods=["POST"])
def create_student():
    data = request.get_json(silent=True)
    if not data:
        current_app.logger.warning("POST /students — no JSON body received")
        return jsonify({"error": "Request body must be valid JSON"}), 400

    current_app.logger.info("POST /students — payload received: %s", data)

    cleaned, err = _validate_student_payload(data, require_all=True)
    if err:
        current_app.logger.warning("POST /students — validation failed: %s", err)
        return jsonify({"error": err}), 422

    if student_model.get_student_by_email(cleaned["email"]):
        current_app.logger.warning("POST /students — duplicate email: %s", cleaned["email"])
        return jsonify({"error": "A student with that email already exists"}), 409

    student = student_model.create_student(**cleaned)
    current_app.logger.info("Created student id=%s", student["id"])
    return jsonify({"message": "Student created", "student": student}), 201


@api_v1.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    current_app.logger.info("GET /students/%s", student_id)
    student = student_model.get_student_by_id(student_id)
    if not student:
        current_app.logger.warning("GET /students/%s — not found", student_id)
        return jsonify({"error": f"Student {student_id} not found"}), 404
    return jsonify({"student": student}), 200


@api_v1.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    current_app.logger.info("PUT /students/%s", student_id)

    if not student_model.get_student_by_id(student_id):
        current_app.logger.warning("PUT /students/%s — not found", student_id)
        return jsonify({"error": f"Student {student_id} not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    filtered = {k: v for k, v in data.items() if k in ALLOWED_UPDATE_FIELDS}
    if not filtered:
        return jsonify({"error": "No valid fields provided for update"}), 422

    cleaned, err = _validate_student_payload(filtered, require_all=False)
    if err:
        current_app.logger.warning("PUT /students/%s — validation failed: %s", student_id, err)
        return jsonify({"error": err}), 422

    if "email" in cleaned:
        existing = student_model.get_student_by_email(cleaned["email"])
        if existing and existing["id"] != student_id:
            return jsonify({"error": "Email already in use by another student"}), 409

    student = student_model.update_student(student_id, cleaned)
    current_app.logger.info("Updated student id=%s", student_id)
    return jsonify({"message": "Student updated", "student": student}), 200


@api_v1.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    current_app.logger.info("DELETE /students/%s", student_id)

    if not student_model.get_student_by_id(student_id):
        current_app.logger.warning("DELETE /students/%s — not found", student_id)
        return jsonify({"error": f"Student {student_id} not found"}), 404

    student_model.delete_student(student_id)
    current_app.logger.info("Deleted student id=%s", student_id)
    return jsonify({"message": f"Student {student_id} deleted"}), 200


@api_v1.app_errorhandler(404)
def not_found(e):
    current_app.logger.error("404 — %s", e)
    return jsonify({"error": "Resource not found"}), 404


@api_v1.app_errorhandler(405)
def method_not_allowed(e):
    current_app.logger.error("405 — %s", e)
    return jsonify({"error": "Method not allowed"}), 405


@api_v1.app_errorhandler(500)
def internal_error(e):
    current_app.logger.critical("500 — %s", e, exc_info=True)
    return jsonify({"error": "Internal server error"}), 500
