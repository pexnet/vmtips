import importlib
import os

from fastapi.testclient import TestClient


def test_health_reports_app_version(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "test-version")

    import main

    main = importlib.reload(main)
    client = TestClient(main.app)

    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "test-version"}
