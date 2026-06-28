from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .proof import RestoreEvidence, bool_from_form, evaluate_restore, normalize_url, render_restore_report
from .storage import RestoreProofStore

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title="RestoreProof")
templates = Jinja2Templates(directory=str(BASE / "templates"))
store = RestoreProofStore(os.environ.get("RESTOREPROOF_DB", BASE / "data" / "restoreproof.sqlite3"))


@app.get("/health")
def health():
    return {"status": "ok", "app": "restoreproof"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "sites": store.list_sites(),
            "backups": store.list_backups(),
            "runs": store.latest_runs(),
        },
    )


@app.post("/sites")
def add_site(name: str = Form(...), url: str = Form(...), client: str = Form("")):
    try:
        store.add_site(name, url, client)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/", status_code=303)


@app.post("/restore-runs")
def add_restore_run(
    site_id: int = Form(...),
    backup_label: str = Form(...),
    backup_created_at: str = Form(...),
    backup_size_mb: int = Form(...),
    storage_location: str = Form(...),
    restore_target_url: str = Form(...),
    homepage_status: int = Form(200),
    admin_status: int = Form(200),
    database_imported: str = Form("on"),
    media_present: str = Form("on"),
    key_urls_passed: int = Form(3),
    key_urls_total: int = Form(3),
    backup_age_hours: int = Form(24),
    notes: str = Form(""),
):
    try:
        site = store.get_site(site_id)
        backup_id = store.add_backup(site_id, backup_label, backup_created_at, backup_size_mb, storage_location, notes)
        evidence = RestoreEvidence(
            name=site["name"],
            restore_target_url=normalize_url(restore_target_url),
            homepage_status=homepage_status,
            admin_status=admin_status,
            database_imported=bool_from_form(database_imported),
            media_present=bool_from_form(media_present),
            key_urls_passed=key_urls_passed,
            key_urls_total=key_urls_total,
            backup_age_hours=backup_age_hours,
            backup_size_mb=backup_size_mb,
            notes=notes.strip(),
        )
        assessment = evaluate_restore(evidence)
        run_id = store.save_restore_run(site_id, backup_id, assessment)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(f"/report/{run_id}", status_code=303)


@app.get("/report/{run_id}", response_class=PlainTextResponse)
def report(run_id: int):
    try:
        site, backup, run, assessment = store.get_run_bundle(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return render_restore_report(site, backup, run, assessment)
