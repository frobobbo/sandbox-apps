from fastapi.testclient import TestClient

from patchpilot_wp.checks import PageFetchResult, evaluate_page_result, generate_run_report
from patchpilot_wp.main import app
from patchpilot_wp.storage import PatchPilotStore


def test_evaluate_page_result_passes_healthy_wordpress_page():
    result = evaluate_page_result(
        PageFetchResult(
            url="https://client.example/",
            http_status=200,
            title="Welcome | Client Site",
            body="<html><title>Welcome | Client Site</title><body>Fresh WordPress page</body></html>",
            elapsed_ms=180,
            error=None,
        ),
        baseline_title="Welcome | Client Site",
    )

    assert result.status == "pass"
    assert result.title == "Welcome | Client Site"
    assert result.warnings == []


def test_evaluate_page_result_flags_php_errors_and_title_changes():
    result = evaluate_page_result(
        PageFetchResult(
            url="https://client.example/about",
            http_status=200,
            title="Critical Error",
            body="Fatal error: Uncaught Error in wp-content/plugins/example.php",
            elapsed_ms=210,
            error=None,
        ),
        baseline_title="About Us | Client Site",
    )

    assert result.status == "fail"
    assert any("PHP/WordPress error text" in item for item in result.warnings)
    assert any("Title changed" in item for item in result.warnings)


def test_evaluate_page_result_handles_missing_or_broken_pages():
    missing = evaluate_page_result(
        PageFetchResult("https://client.example/missing", 404, "Not Found", "", 95, None),
        baseline_title="Services | Client Site",
    )
    broken = evaluate_page_result(
        PageFetchResult("https://client.example/broken", None, None, "", 0, "connection refused"),
        baseline_title=None,
    )

    assert missing.status == "fail"
    assert any("HTTP 404" in item for item in missing.warnings)
    assert broken.status == "fail"
    assert any("connection refused" in item for item in broken.warnings)


def test_store_records_sites_pages_runs_checks_and_reports(tmp_path):
    store = PatchPilotStore(tmp_path / "patchpilot.sqlite3")
    site_id = store.add_site("Client Site", "https://client.example", "Client LLC")
    page_id = store.add_page(site_id, "Home", "https://client.example/", baseline_title="Welcome | Client Site")
    run_id = store.start_run(site_id, notes="Plugin updates applied manually on staging")

    check_id = store.save_page_check(
        run_id,
        page_id,
        url="https://client.example/",
        http_status=200,
        title="Welcome | Client Site",
        baseline_title="Welcome | Client Site",
        status="pass",
        warnings=[],
        elapsed_ms=120,
        evidence_text="200 OK Welcome | Client Site",
    )
    report_text = generate_run_report(store.get_run(run_id), store.list_run_checks(run_id))
    report_id = store.save_report(run_id, report_text)

    assert site_id > 0 and page_id > 0 and run_id > 0 and check_id > 0 and report_id > 0
    assert store.list_sites()[0]["name"] == "Client Site"
    assert store.list_pages(site_id)[0]["baseline_title"] == "Welcome | Client Site"
    assert store.list_run_checks(run_id)[0]["status"] == "pass"
    assert "PatchPilot WP Maintenance Report" in store.get_report(run_id)["report_text"]


def test_generate_run_report_summarizes_pass_warn_fail_pages():
    run = {
        "site_name": "Client Site",
        "site_url": "https://client.example",
        "client_name": "Client LLC",
        "created_at": "2026-06-30 19:00:00",
        "notes": "Theme and plugins updated on staging.",
    }
    checks = [
        {"label": "Home", "url": "https://client.example/", "status": "pass", "http_status": 200, "title": "Home", "warnings": []},
        {"label": "Contact", "url": "https://client.example/contact", "status": "warn", "http_status": 200, "title": "Contact", "warnings": ["Title changed from Contact Us to Contact"]},
        {"label": "Shop", "url": "https://client.example/shop", "status": "fail", "http_status": 500, "title": "Server Error", "warnings": ["HTTP 500 returned"]},
    ]

    report = generate_run_report(run, checks)

    assert "Client Site" in report
    assert "3 pages tested" in report
    assert "1 passed, 1 warning, 1 failed" in report
    assert "Shop" in report
    assert "Recommended follow-up" in report


def test_dashboard_flow_adds_site_page_run_and_report(tmp_path, monkeypatch):
    test_store = PatchPilotStore(tmp_path / "patchpilot.sqlite3")
    monkeypatch.setattr("patchpilot_wp.main.store", test_store)
    client = TestClient(app)

    site_response = client.post("/sites", data={"name": "Client Site", "base_url": "https://client.example", "client_name": "Client LLC"}, follow_redirects=False)
    assert site_response.status_code == 303
    site_id = test_store.list_sites()[0]["id"]

    page_response = client.post(f"/sites/{site_id}/pages", data={"label": "Home", "url": "https://client.example/", "baseline_title": "Home"}, follow_redirects=False)
    assert page_response.status_code == 303

    run_response = client.post(f"/sites/{site_id}/runs", data={"notes": "Manual update completed", "mode": "baseline"}, follow_redirects=False)
    assert run_response.status_code == 303
    run_id = test_store.list_runs(site_id)[0]["id"]

    report_response = client.get(f"/runs/{run_id}/report")
    assert report_response.status_code == 200
    assert "PatchPilot WP Maintenance Report" in report_response.text
    assert "Client Site" in report_response.text


def test_health_endpoint_reports_app_name(tmp_path, monkeypatch):
    monkeypatch.setattr("patchpilot_wp.main.store", PatchPilotStore(tmp_path / "patchpilot.sqlite3"))
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "patchpilot-wp"}
