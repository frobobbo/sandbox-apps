import warnings

from wp_fleetops.fleet import FleetSite, calculate_health_score, generate_alerts, generate_maintenance_report
from wp_fleetops.storage import FleetOpsStore


def test_calculate_health_score_rewards_clean_site():
    site = FleetSite(name="Church", url="https://church.example", uptime_ok=True, ssl_days=80, wp_updates=0, backup_age_hours=10, response_ms=240, security_header_count=4)

    score = calculate_health_score(site)

    assert score >= 95


def test_generate_alerts_catches_operational_risks():
    site = FleetSite(name="Client", url="https://client.example", uptime_ok=False, ssl_days=5, wp_updates=6, backup_age_hours=100, response_ms=2600, security_header_count=0)

    alerts = generate_alerts(site)

    assert any(alert.severity == "critical" and "down" in alert.message.lower() for alert in alerts)
    assert any("SSL" in alert.message for alert in alerts)
    assert any("backup" in alert.message.lower() for alert in alerts)


def test_generate_maintenance_report_groups_fleet_status():
    sites = [
        FleetSite("A", "https://a.example", True, 80, 0, 12, 200, 4),
        FleetSite("B", "https://b.example", True, 6, 3, 80, 1900, 1),
    ]

    report = generate_maintenance_report(sites)

    assert "WP FleetOps Maintenance Report" in report
    assert "A" in report and "B" in report
    assert "Recommended actions" in report


def test_generate_maintenance_report_includes_average_fleet_score():
    sites = [
        FleetSite("Healthy", "https://healthy.example", True, 80, 0, 12, 200, 4),
        FleetSite("Risky", "https://risky.example", True, 6, 3, 80, 1900, 1),
    ]

    report = generate_maintenance_report(sites)

    assert "Average fleet score: 65/100" in report


def test_store_persists_fleet_snapshots(tmp_path):
    store = FleetOpsStore(tmp_path / "fleet.sqlite3")
    site = FleetSite("Church", "https://church.example", True, 80, 0, 12, 200, 4)
    site_id = store.upsert_site(site)
    snap_id = store.save_snapshot(site_id, site, calculate_health_score(site), generate_alerts(site))

    assert site_id > 0
    assert snap_id > 0
    assert store.latest_dashboard()[0]["name"] == "Church"


def make_test_client():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Using `httpx` with `starlette.testclient` is deprecated.*",
        )
        from fastapi.testclient import TestClient

    from wp_fleetops.main import app

    return TestClient(app)


def valid_snapshot_payload(**overrides):
    payload = {
        "name": "Test Site",
        "url": "https://test-site.example",
        "uptime_ok": "true",
        "ssl_days": "60",
        "wp_updates": "0",
        "backup_age_hours": "24",
        "response_ms": "250",
        "security_header_count": "3",
    }
    payload.update(overrides)
    return payload


def test_snapshot_rejects_negative_operational_metrics():
    client = make_test_client()

    response = client.post(
        "/snapshot",
        data=valid_snapshot_payload(name="Bad Metrics", url="https://bad-metrics.example", ssl_days="-1"),
        follow_redirects=False,
    )

    assert response.status_code == 422


def test_snapshot_rejects_non_http_urls():
    client = make_test_client()

    response = client.post(
        "/snapshot",
        data=valid_snapshot_payload(url="javascript:alert(1)"),
        follow_redirects=False,
    )

    assert response.status_code == 422


def test_readiness_reports_database_and_template_dependencies():
    client = make_test_client()

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "app": "wp-fleetops",
        "checks": {
            "database": "ok",
            "templates": "ok",
        },
    }
