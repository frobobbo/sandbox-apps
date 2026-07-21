import csv
import io
import warnings

import pytest

from wp_fleetops.fleet import FleetSite, calculate_health_score, generate_alerts, generate_maintenance_report, normalize_site
from wp_fleetops.storage import FleetOpsStore


def test_calculate_health_score_rewards_clean_site():
    site = FleetSite(name="Church", url="https://church.example", uptime_ok=True, ssl_days=80, wp_updates=0, backup_age_hours=10, response_ms=240, security_header_count=4)

    score = calculate_health_score(site)

    assert score >= 95


def test_normalize_site_canonicalizes_url_and_name_for_deduplication():
    site = FleetSite(name="  Church WP  ", url=" HTTPS://Church.Example/ ", uptime_ok=True, ssl_days=80, wp_updates=0, backup_age_hours=10, response_ms=240, security_header_count=4)

    normalized = normalize_site(site)

    assert normalized.name == "Church WP"
    assert normalized.url == "https://church.example"
    assert normalized.ssl_days == site.ssl_days
    assert normalized.response_ms == site.response_ms


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


def test_store_deduplicates_sites_by_canonical_url(tmp_path):
    store = FleetOpsStore(tmp_path / "fleet.sqlite3")
    first = FleetSite("Church", "https://church.example", True, 80, 0, 12, 200, 4)
    duplicate = FleetSite("Church Updated", "HTTPS://Church.Example/", True, 80, 0, 12, 200, 4)

    first_id = store.upsert_site(first)
    duplicate_id = store.upsert_site(duplicate)

    assert duplicate_id == first_id


def make_test_client(*, raise_server_exceptions=True):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Using `httpx` with `starlette.testclient` is deprecated.*",
        )
        from fastapi.testclient import TestClient

    from wp_fleetops.main import app

    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


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


def test_dashboard_links_to_csv_export():
    response = make_test_client().get("/")

    assert response.status_code == 200
    assert 'href="/export.csv"' in response.text


def test_snapshot_rejects_negative_operational_metrics():
    client = make_test_client()

    response = client.post(
        "/snapshot",
        data=valid_snapshot_payload(name="Bad Metrics", url="https://bad-metrics.example", ssl_days="-1"),
        follow_redirects=False,
    )

    assert response.status_code == 422


def test_snapshot_rejects_whitespace_only_site_names(tmp_path, monkeypatch):
    from wp_fleetops import main

    monkeypatch.setattr(main, "store", FleetOpsStore(tmp_path / "fleet.sqlite3"))

    response = make_test_client().post(
        "/snapshot",
        data=valid_snapshot_payload(name="   "),
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert main.store.latest_dashboard() == []


def test_snapshot_rejects_non_http_urls():
    client = make_test_client()

    response = client.post(
        "/snapshot",
        data=valid_snapshot_payload(url="javascript:alert(1)"),
        follow_redirects=False,
    )

    assert response.status_code == 422


def test_snapshot_rejects_urls_without_a_hostname(tmp_path, monkeypatch):
    from wp_fleetops import main

    monkeypatch.setattr(main, "store", FleetOpsStore(tmp_path / "fleet.sqlite3"))
    response = make_test_client().post(
        "/snapshot",
        data=valid_snapshot_payload(url="https://"),
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert main.store.latest_dashboard() == []


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


def test_readiness_returns_503_when_template_dependency_is_missing(tmp_path, monkeypatch):
    from wp_fleetops import main

    monkeypatch.setattr(main, "BASE", tmp_path)

    response = make_test_client().get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not-ready",
        "app": "wp-fleetops",
        "checks": {
            "database": "ok",
            "templates": "missing",
        },
    }


def test_readiness_returns_503_when_database_dependency_is_unavailable(tmp_path, monkeypatch):
    from wp_fleetops import main

    unavailable_store = FleetOpsStore(tmp_path / "available.sqlite3")
    unavailable_store.path = tmp_path / "missing" / "fleet.sqlite3"
    monkeypatch.setattr(main, "store", unavailable_store)

    response = make_test_client(raise_server_exceptions=False).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not-ready",
        "app": "wp-fleetops",
        "checks": {
            "database": "unavailable",
            "templates": "ok",
        },
    }


def test_export_returns_machine_readable_dashboard_with_summary(tmp_path):
    from wp_fleetops import main

    original_store = main.store
    main.store = FleetOpsStore(tmp_path / "fleet.sqlite3")
    try:
        client = make_test_client()
        response = client.post(
            "/snapshot",
            data=valid_snapshot_payload(
                name="Exported Site",
                url="https://exported.example",
                ssl_days="5",
                backup_age_hours="96",
            ),
            follow_redirects=False,
        )
        assert response.status_code == 303

        export_response = client.get("/export.json")
    finally:
        main.store = original_store

    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["summary"] == {"sites": 1, "critical_sites": 1, "average_score": 55}
    assert payload["sites"][0]["name"] == "Exported Site"
    assert payload["sites"][0]["url"] == "https://exported.example"
    assert any(alert["severity"] == "critical" for alert in payload["sites"][0]["alerts"])


def test_csv_export_downloads_spreadsheet_ready_fleet_rows(tmp_path, monkeypatch):
    from wp_fleetops import main

    monkeypatch.setattr(main, "store", FleetOpsStore(tmp_path / "fleet.sqlite3"))
    client = make_test_client()
    response = client.post(
        "/snapshot",
        data=valid_snapshot_payload(
            name="Church, Downtown",
            url="https://downtown.example",
            ssl_days="5",
            backup_age_hours="96",
        ),
        follow_redirects=False,
    )
    assert response.status_code == 303

    export_response = client.get("/export.csv")

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert export_response.headers["content-disposition"] == 'attachment; filename="wp-fleetops.csv"'
    rows = list(csv.DictReader(io.StringIO(export_response.text)))
    assert rows == [
        {
            "name": "Church, Downtown",
            "url": "https://downtown.example",
            "score": "55",
            "status": "up",
            "ssl_days": "5",
            "wp_updates": "0",
            "backup_age_hours": "96",
            "response_ms": "250",
            "security_header_count": "3",
            "critical_alerts": "2",
            "warning_alerts": "0",
            "info_alerts": "0",
            "captured_at": rows[0]["captured_at"],
        }
    ]


@pytest.mark.parametrize(
    "site_name",
    [
        '=HYPERLINK("https://malicious.example")',
        "+SUM(1,1)",
        "-1+1",
        "@SUM(1,1)",
    ],
)
def test_csv_export_prevents_spreadsheet_formula_injection(tmp_path, monkeypatch, site_name):
    from wp_fleetops import main

    monkeypatch.setattr(main, "store", FleetOpsStore(tmp_path / "fleet.sqlite3"))
    client = make_test_client()
    response = client.post(
        "/snapshot",
        data=valid_snapshot_payload(name=site_name),
        follow_redirects=False,
    )
    assert response.status_code == 303

    export_response = client.get("/export.csv")

    row = next(csv.DictReader(io.StringIO(export_response.text)))
    assert row["name"] == f"'{site_name}"
