import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_login_invalid():
    response = client.post("/api/auth/login", json={"password": "wrong"})
    assert response.status_code == 401

def test_login_valid():
    response = client.post("/api/auth/login", json={"password": "1234"})
    assert response.status_code == 200
    assert "token" in response.json()
    assert "user_id" in response.json()

def test_dashboard_requires_auth():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 422  # No Authorization header

def test_dashboard_with_auth():
    login_res = client.post("/api/auth/login", json={"password": "1234"})
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/dashboard/stats", headers=headers)
    assert response.status_code == 200
    assert "total_workouts" in response.json()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
