from wp_carepulse.checks import evaluate_site, summarize_report
from wp_carepulse.storage import CarePulseStore


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
