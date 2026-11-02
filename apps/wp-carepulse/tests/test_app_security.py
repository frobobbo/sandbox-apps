from fastapi.testclient import TestClient

from wp_carepulse.main import app
from wp_carepulse.storage import CarePulseStore


def test_dashboard_response_prevents_mime_sniffing(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
