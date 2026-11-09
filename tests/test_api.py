import pytest
from fastapi.testclient import TestClient

from examples.task_manager import db
from examples.task_manager.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    with TestClient(app) as test_client:
        yield test_client


def test_crud_persists_and_serves_frontend(client):
    assert client.get("/").status_code == 200
    for path in ["/static/app.js", "/static/style.css", "/openapi.json"]:
        assert client.get(path).status_code == 200
    assert client.get("/api/tasks").json() == []
    body = {"title": " ทำหนังสือให้เสร็จ <script> ", "description": "อัญประกาศ ' และภาษาไทย"}
    response = client.post("/api/tasks", json=body)
    assert response.status_code == 201
    item = response.json()
    assert item["title"] == body["title"].strip() and item["completed"] is False
    task_id = item["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={"completed": True, "description": ""})
    assert response.status_code == 200 and response.json()["completed"] is True
    assert response.json()["description"] == ""
    with TestClient(app) as reopened:
        assert reopened.get(f"/api/tasks/{task_id}").json()["completed"] is True
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    missing = client.get(f"/api/tasks/{task_id}")
    assert missing.status_code == 404 and missing.json()["detail"] == "ไม่พบงานที่ระบุ"


@pytest.mark.parametrize("body", [{}, {"title": " "}, {"title": None}, {"title": 3}, {"title": "ok", "unknown": 1}])
def test_create_rejects_invalid_payload(client, body):
    assert client.post("/api/tasks", json=body).status_code == 422


@pytest.mark.parametrize("body", [{"title": " "}, {"title": None}, {"completed": "true"}, {"completed": None}, {"description": None}, {"extra": 1}])
def test_patch_validation(client, body):
    task_id = client.post("/api/tasks", json={"title": "งานทดสอบ"}).json()["id"]
    assert client.patch(f"/api/tasks/{task_id}", json=body).status_code == 422


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_task(client, method):
    kwargs = {"json": {"title": "แก้ไขแล้ว"}} if method == "patch" else {}
    assert getattr(client, method)("/api/tasks/999", **kwargs).status_code == 404


def test_multiple_records_are_independent(client):
    for name in ["A", "B", "C"]:
        assert client.post("/api/tasks", json={"title": name}).status_code == 201
    assert [row["title"] for row in client.get("/api/tasks").json()] == ["A", "B", "C"]
