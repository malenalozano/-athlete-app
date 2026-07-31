"""Smoke tests de los endpoints reales de la app (antes este archivo probaba
una API ficticia con /api/auth/login + tokens Bearer que nunca existió aquí)."""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_invalid():
    response = client.post("/auth/login", json={"nombre": "usuario_que_no_existe"})
    assert response.status_code == 401


def test_login_valid():
    response = client.post("/auth/login", json={"nombre": "malena"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["nombre"] == "Malena"


def test_login_case_insensitive():
    response = client.post("/auth/login", json={"nombre": "MALENA"})
    assert response.status_code == 200
    assert response.json()["id"] == 1
