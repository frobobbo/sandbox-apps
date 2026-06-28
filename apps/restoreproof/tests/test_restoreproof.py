import pytest
from fastapi.testclient import TestClient

from restoreproof.main import app
from restoreproof.proof import RestoreEvidence, evaluate_restore, normalize_url, render_restore_report
from restoreproof.storage import RestoreProofStore


def test_evaluate_restore_marks_strong_evidence_verified():
    assessment = evaluate_restore(
        RestoreEvidence(
            name="Church Website",
            restore_target_url="https://restore.example",
            homepage_status=200,
            admin_status=200,
            database_imported=True,
            media_present=True,
            key_urls_passed=4,
            key_urls_total=4,
            backup_age_hours=12,
            backup_size_mb=1024,
        )
    )

    assert assessment.status == "verified"
    assert assessment.score >= 90
    assert "working recovery target" in assessment.summary
    assert assessment.actions == []


def test_evaluate_restore_flags_failed_database_and_urls():
    assessment = evaluate_restore(
        RestoreEvidence(
            name="Client Site",
            restore_target_url="https://restore.example",
            homepage_status=500,
            admin_status=404,
            database_imported=False,
            media_present=False,
            key_urls_passed=1,
            key_urls_total=5,
            backup_age_hours=120,
            backup_size_mb=0,
        )
    )

    assert assessment.status == "failed"
    assert assessment.score < 70
    assert any("database" in action.lower() for action in assessment.actions)
    assert any("homepage" in action.lower() for action in assessment.actions)
    assert any("key URL" in action for action in assessment.actions)


def test_evaluate_restore_rejects_impossible_key_url_counts():
    with pytest.raises(ValueError, match="Passed key URLs"):
        evaluate_restore(
            RestoreEvidence("Bad", "https://restore.example", 200, 200, True, True, 3, 2, 4, 100)
        )


def test_normalize_url_rejects_hostless_or_credential_urls():
    for url in ("", "https://", "https://user:pass@example.org"):
        with pytest.raises(ValueError, match="valid URL"):
            normalize_url(url)


def test_store_persists_site_backup_and_restore_run(tmp_path):
    store = RestoreProofStore(tmp_path / "restoreproof.sqlite3")
    site_id = store.add_site("Church", "church.example", "Church")
    backup_id = store.add_backup(site_id, "Nightly", "2026-06-28", 512, "NAS")
    assessment = evaluate_restore(
        RestoreEvidence("Church", "restore.church.example", 200, 200, True, True, 2, 2, 8, 512)
    )
    run_id = store.save_restore_run(site_id, backup_id, assessment)

    latest = store.latest_runs()[0]
    assert latest["site_name"] == "Church"
    assert latest["status"] == "verified"
    assert latest["restore_target_url"] == "https://restore.church.example"
    site, backup, run, loaded = store.get_run_bundle(run_id)
    assert site["url"] == "https://church.example"
    assert backup["label"] == "Nightly"
    assert loaded.score == assessment.score
    assert run["id"] == run_id


def test_store_rejects_backup_for_wrong_site(tmp_path):
    store = RestoreProofStore(tmp_path / "restoreproof.sqlite3")
    site_a = store.add_site("A", "a.example")
    site_b = store.add_site("B", "b.example")
    backup_id = store.add_backup(site_a, "Nightly", "latest", 10, "NAS")
    assessment = evaluate_restore(RestoreEvidence("B", "restore.example", 200, 200, True, True, 1, 1, 1, 10))

    with pytest.raises(ValueError, match="selected site"):
        store.save_restore_run(site_b, backup_id, assessment)


def test_report_contains_client_ready_evidence(tmp_path):
    store = RestoreProofStore(tmp_path / "restoreproof.sqlite3")
    site_id = store.add_site("Church", "https://church.example", "Church Client")
    backup_id = store.add_backup(site_id, "Nightly", "2026-06-28", 512, "NAS")
    assessment = evaluate_restore(
        RestoreEvidence("Church", "https://restore.example", 200, 200, True, True, 2, 2, 12, 512, "Spot checked contact page.")
    )
    run_id = store.save_restore_run(site_id, backup_id, assessment)
    site, backup, run, loaded = store.get_run_bundle(run_id)

    report = render_restore_report(site, backup, run, loaded)

    assert "RestoreProof Report: Church" in report
    assert "Result: VERIFIED" in report
    assert "Database imported: yes" in report
    assert "Spot checked contact page" in report


def test_dashboard_and_form_flow_use_isolated_store(tmp_path, monkeypatch):
    test_store = RestoreProofStore(tmp_path / "restoreproof.sqlite3")
    monkeypatch.setattr("restoreproof.main.store", test_store)
    client = TestClient(app)

    response = client.post("/sites", data={"name": "Church", "url": "church.example", "client": "Church"}, follow_redirects=False)
    assert response.status_code == 303

    site_id = test_store.list_sites()[0]["id"]
    response = client.post(
        "/restore-runs",
        data={
            "site_id": site_id,
            "backup_label": "Nightly",
            "backup_created_at": "2026-06-28",
            "backup_size_mb": 512,
            "storage_location": "NAS",
            "restore_target_url": "restore.church.example",
            "homepage_status": 200,
            "admin_status": 200,
            "database_imported": "on",
            "media_present": "on",
            "key_urls_passed": 3,
            "key_urls_total": 3,
            "backup_age_hours": 12,
            "notes": "All key pages loaded.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    report = client.get(response.headers["location"])
    assert report.status_code == 200
    assert "Result: VERIFIED" in report.text

    dashboard = client.get("/")
    assert "RestoreProof" in dashboard.text
    assert "Church" in dashboard.text
    assert "verified" in dashboard.text


def test_restore_run_form_returns_400_for_invalid_restore_url(tmp_path, monkeypatch):
    test_store = RestoreProofStore(tmp_path / "restoreproof.sqlite3")
    site_id = test_store.add_site("Church", "church.example")
    monkeypatch.setattr("restoreproof.main.store", test_store)

    response = TestClient(app, raise_server_exceptions=False).post(
        "/restore-runs",
        data={
            "site_id": site_id,
            "backup_label": "Nightly",
            "backup_created_at": "latest",
            "backup_size_mb": 512,
            "storage_location": "NAS",
            "restore_target_url": "https://",
        },
    )

    assert response.status_code == 400
    assert "valid URL" in response.text
