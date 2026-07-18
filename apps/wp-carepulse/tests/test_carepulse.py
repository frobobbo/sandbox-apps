import pytest
from fastapi.testclient import TestClient

from wp_carepulse.checks import evaluate_site, summarize_report
from wp_carepulse.main import app
from wp_carepulse.storage import CarePulseStore, normalize_site_url


def test_evaluate_site_marks_healthy_wordpress_site():
    result = evaluate_site(
        name="Church",
        url="https://church.example",
        http_status=200,
        latency_ms=240,
        ssl_days_remaining=72,
        wordpress_version="6.6.1",
        update_count=0,
        backup_age_hours=12,
        security_headers={"strict-transport-security": "max-age=31536000", "x-frame-options": "SAMEORIGIN"},
    )

    assert result.status == "green"
    assert result.score >= 90
    assert "healthy" in result.summary.lower()


def test_evaluate_site_flags_ssl_updates_and_stale_backup():
    result = evaluate_site(
        name="Client",
        url="https://client.example",
        http_status=200,
        latency_ms=1450,
        ssl_days_remaining=8,
        wordpress_version="6.4.0",
        update_count=7,
        backup_age_hours=96,
        security_headers={},
    )

    assert result.status == "red"
    assert any("SSL" in item for item in result.actions)
    assert any("updates" in item for item in result.actions)
    assert any("backup" in item.lower() for item in result.actions)


def test_store_saves_sites_checks_and_report(tmp_path):
    store = CarePulseStore(tmp_path / "care.sqlite3")
    site_id = store.add_site("Church", "https://church.example", "Church Client")
    check = evaluate_site("Church", "https://church.example", 200, 180, 90, "6.6.1", 1, 20, {})
    check_id = store.save_check(site_id, check)

    assert check_id > 0
    assert store.list_sites()[0]["name"] == "Church"
    assert store.latest_checks()[0]["status"] == check.status


def test_store_normalizes_bare_domain_urls_for_deduplication(tmp_path):
    store = CarePulseStore(tmp_path / "care.sqlite3")

    first_id = store.add_site("Church", "church.example", "Church Client")
    second_id = store.add_site("Church", "https://church.example", "Church Client")

    assert second_id == first_id
    assert store.list_sites()[0]["url"] == "https://church.example"


def test_store_normalizes_url_host_case_for_deduplication(tmp_path):
    store = CarePulseStore(tmp_path / "care.sqlite3")

    first_id = store.add_site("Church", "HTTPS://Church.Example/", "Church Client")
    second_id = store.add_site("Church", "https://church.example", "Church Client")

    assert second_id == first_id
    assert store.list_sites()[0]["url"] == "https://church.example"


def test_normalize_site_url_rejects_blank_or_hostless_urls():
    for invalid_url in ("", "   ", "https://", "mailto:care@example.com"):
        with pytest.raises(ValueError, match="valid site URL"):
            normalize_site_url(invalid_url)


def test_store_rejects_invalid_site_urls(tmp_path):
    store = CarePulseStore(tmp_path / "care.sqlite3")

    with pytest.raises(ValueError, match="valid site URL"):
        store.add_site("Broken", "https://")

    assert store.list_sites() == []


def test_store_rejects_blank_site_names(tmp_path):
    store = CarePulseStore(tmp_path / "care.sqlite3")

    with pytest.raises(ValueError, match="site name"):
        store.add_site("   ", "https://church.example")

    assert store.list_sites() == []


def test_add_site_form_returns_400_for_invalid_url():
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/sites",
        data={"name": "Broken", "url": "https://", "client": "Church Client"},
    )

    assert response.status_code == 400
    assert "valid site URL" in response.text


def test_green_site_with_minor_recommendations_stays_client_friendly():
    result = evaluate_site(
        name="Church",
        url="https://church.example",
        http_status=200,
        latency_ms=240,
        ssl_days_remaining=72,
        wordpress_version="6.6.1",
        update_count=1,
        backup_age_hours=12,
        security_headers={},
    )

    assert result.status == "green"
    assert "needs attention" not in result.summary.lower()


def test_summarize_report_is_client_friendly():
    checks = [
        evaluate_site("A", "https://a.example", 200, 100, 90, "6.6", 0, 10, {}),
        evaluate_site("B", "https://b.example", 500, 2000, 3, "6.2", 5, 120, {}),
    ]
    report = summarize_report(checks)

    assert "Monthly WordPress Care Report" in report
    assert "Needs attention" in report
    assert "B" in report


def test_summarize_report_prioritizes_sites_needing_attention():
    checks = [
        evaluate_site("Healthy", "https://healthy.example", 200, 100, 90, "6.6", 0, 10, {}),
        evaluate_site("Urgent", "https://urgent.example", 500, 2000, 3, "6.2", 5, 120, {}),
        evaluate_site("Maintenance", "https://maintenance.example", 200, 1300, 40, "6.5", 3, 48, {}),
    ]

    report = summarize_report(checks)

    assert report.index("## Urgent") < report.index("## Maintenance") < report.index("## Healthy")


def test_manual_check_uses_normalized_url_in_saved_report(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)
    client = TestClient(app)

    response = client.post(
        "/manual-check",
        data={"name": "Church", "url": "Church.Example/", "client": "Church Client"},
        follow_redirects=False,
    )
    report = client.get("/report")

    assert response.status_code == 303
    assert "URL: https://church.example" in report.text


def test_manual_check_rejects_http_status_below_valid_range(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)

    response = TestClient(app).post(
        "/manual-check",
        data={"name": "Church", "url": "church.example", "http_status": "99"},
    )

    assert response.status_code == 422
    assert test_store.list_sites() == []


def test_manual_check_rejects_http_status_above_valid_range(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)

    response = TestClient(app).post(
        "/manual-check",
        data={"name": "Church", "url": "church.example", "http_status": "600"},
    )

    assert response.status_code == 422
    assert test_store.list_sites() == []


def test_report_uses_saved_check_results_without_recalculating(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)
    site_id = test_store.add_site("Healthy", "https://healthy.example", "Church Client")
    check = evaluate_site(
        "Healthy",
        "https://healthy.example",
        200,
        100,
        90,
        "6.6",
        0,
        10,
        {
            "strict-transport-security": "max-age=31536000",
            "x-frame-options": "SAMEORIGIN",
        },
    )
    test_store.save_check(site_id, check)

    response = TestClient(app).get("/report")

    assert response.status_code == 200
    assert "Score: 100/100" in response.text
    assert "Recommended actions:" not in response.text


def test_dashboard_limits_manual_http_status_to_valid_range(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'name="http_status" type="number" min="100" max="599"' in response.text


def test_dashboard_shows_recommended_actions_for_latest_checks(tmp_path, monkeypatch):
    test_store = CarePulseStore(tmp_path / "care.sqlite3")
    monkeypatch.setattr("wp_carepulse.main.store", test_store)
    site_id = test_store.add_site("Client", "https://client.example", "Church Client")
    check = evaluate_site("Client", "https://client.example", 200, 1450, 8, "6.4.0", 7, 96, {})
    test_store.save_check(site_id, check)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Recommended actions" in response.text
    assert "Renew SSL certificate" in response.text
    assert "Apply WordPress/plugin/theme updates" in response.text
