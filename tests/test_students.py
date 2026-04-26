import os
import tempfile
import pytest
from app import create_app


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path})

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


VALID_STUDENT = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "age": 20,
    "grade": "A",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_student(client, data=None):
    return client.post(
        "/api/v1/students",
        json=data or VALID_STUDENT,
        content_type="application/json",
    )


# ── healthcheck ───────────────────────────────────────────────────────────────

class TestHealthcheck:
    def test_returns_200(self, client):
        r = client.get("/api/v1/healthcheck")
        assert r.status_code == 200

    def test_response_body(self, client):
        data = client.get("/api/v1/healthcheck").get_json()
        assert data["status"] == "ok"
        assert data["version"] == "v1"


# ── POST /students ────────────────────────────────────────────────────────────

class TestCreateStudent:
    def test_creates_student_successfully(self, client):
        r = _create_student(client)
        assert r.status_code == 201
        body = r.get_json()
        assert body["student"]["name"] == VALID_STUDENT["name"]
        assert body["student"]["email"] == VALID_STUDENT["email"]
        assert "id" in body["student"]

    def test_missing_fields_returns_422(self, client):
        r = _create_student(client, {"name": "Bob"})
        assert r.status_code == 422
        assert "error" in r.get_json()

    def test_invalid_email_returns_422(self, client):
        r = _create_student(client, {**VALID_STUDENT, "email": "not-an-email"})
        assert r.status_code == 422

    def test_invalid_age_returns_422(self, client):
        r = _create_student(client, {**VALID_STUDENT, "age": -5})
        assert r.status_code == 422

    def test_duplicate_email_returns_409(self, client):
        _create_student(client)
        r = _create_student(client)
        assert r.status_code == 409

    def test_no_body_returns_400(self, client):
        r = client.post("/api/v1/students", content_type="application/json")
        assert r.status_code == 400


# ── GET /students ─────────────────────────────────────────────────────────────

class TestGetAllStudents:
    def test_empty_list(self, client):
        r = client.get("/api/v1/students")
        assert r.status_code == 200
        body = r.get_json()
        assert body["students"] == []
        assert body["count"] == 0

    def test_returns_created_students(self, client):
        _create_student(client)
        _create_student(client, {**VALID_STUDENT, "email": "bob@example.com", "name": "Bob"})
        r = client.get("/api/v1/students")
        assert r.status_code == 200
        assert r.get_json()["count"] == 2


# ── GET /students/<id> ────────────────────────────────────────────────────────

class TestGetStudent:
    def test_get_existing_student(self, client):
        student_id = _create_student(client).get_json()["student"]["id"]
        r = client.get(f"/api/v1/students/{student_id}")
        assert r.status_code == 200
        assert r.get_json()["student"]["id"] == student_id

    def test_get_nonexistent_returns_404(self, client):
        r = client.get("/api/v1/students/9999")
        assert r.status_code == 404


# ── PUT /students/<id> ────────────────────────────────────────────────────────

class TestUpdateStudent:
    def test_update_name(self, client):
        student_id = _create_student(client).get_json()["student"]["id"]
        r = client.put(
            f"/api/v1/students/{student_id}",
            json={"name": "Alice Updated"},
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.get_json()["student"]["name"] == "Alice Updated"

    def test_update_nonexistent_returns_404(self, client):
        r = client.put(
            "/api/v1/students/9999",
            json={"name": "Ghost"},
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_update_with_duplicate_email_returns_409(self, client):
        _create_student(client)
        student2_id = _create_student(
            client, {**VALID_STUDENT, "email": "bob@example.com", "name": "Bob"}
        ).get_json()["student"]["id"]

        r = client.put(
            f"/api/v1/students/{student2_id}",
            json={"email": VALID_STUDENT["email"]},
            content_type="application/json",
        )
        assert r.status_code == 409

    def test_update_no_valid_fields_returns_422(self, client):
        student_id = _create_student(client).get_json()["student"]["id"]
        r = client.put(
            f"/api/v1/students/{student_id}",
            json={"unknown_field": "value"},
            content_type="application/json",
        )
        assert r.status_code == 422

    def test_update_invalid_age_returns_422(self, client):
        student_id = _create_student(client).get_json()["student"]["id"]
        r = client.put(
            f"/api/v1/students/{student_id}",
            json={"age": 999},
            content_type="application/json",
        )
        assert r.status_code == 422


# ── DELETE /students/<id> ─────────────────────────────────────────────────────

class TestDeleteStudent:
    def test_delete_existing_student(self, client):
        student_id = _create_student(client).get_json()["student"]["id"]
        r = client.delete(f"/api/v1/students/{student_id}")
        assert r.status_code == 200
        assert str(student_id) in r.get_json()["message"]

    def test_deleted_student_no_longer_found(self, client):
        student_id = _create_student(client).get_json()["student"]["id"]
        client.delete(f"/api/v1/students/{student_id}")
        r = client.get(f"/api/v1/students/{student_id}")
        assert r.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        r = client.delete("/api/v1/students/9999")
        assert r.status_code == 404
