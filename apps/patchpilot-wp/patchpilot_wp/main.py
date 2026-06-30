from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .checks import check_page, evaluate_page_result, generate_run_report, PageFetchResult
from .storage import PatchPilotStore

BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title="PatchPilot WP")
templates = Jinja2Templates(directory=str(BASE / "templates"))
store = PatchPilotStore(BASE / "data" / "patchpilot.sqlite3")


@app.get("/health")
def health():
    return {"status": "ok", "app": "patchpilot-wp"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    sites = store.list_sites()
    runs = store.list_runs()
    latest_checks = {run["id"]: store.list_run_checks(run["id"]) for run in runs[:5]}
    return templates.TemplateResponse(request, "index.html", {"sites": sites, "runs": runs, "latest_checks": latest_checks})


@app.post("/sites")
def add_site(name: str = Form(...), base_url: str = Form(...), client_name: str = Form("")):
    store.add_site(name, base_url, client_name)
    return RedirectResponse("/", status_code=303)


@app.post("/sites/{site_id}/pages")
def add_page(site_id: int, label: str = Form(...), url: str = Form(...), baseline_title: str = Form("")):
    store.add_page(site_id, label, url, baseline_title or None)
    return RedirectResponse("/", status_code=303)


@app.post("/sites/{site_id}/runs")
def start_run(site_id: int, notes: str = Form(""), mode: str = Form("live")):
    run_id = store.start_run(site_id, notes)
    pages = store.list_pages(site_id)
    for page in pages:
        if mode == "baseline":
            fetch = PageFetchResult(page["url"], 200, page.get("baseline_title"), "", 0, None)
            result = evaluate_page_result(fetch, page.get("baseline_title"))
        else:
            result = check_page(page["url"], page.get("baseline_title"))
        store.save_page_check(
            run_id,
            page["id"],
            result.url,
            result.http_status,
            result.title,
            page.get("baseline_title"),
            result.status,
            result.warnings,
            result.elapsed_ms,
            result.evidence_text,
            result.screenshot_path,
        )
    report = generate_run_report(store.get_run(run_id), store.list_run_checks(run_id))
    store.save_report(run_id, report)
    return RedirectResponse(f"/runs/{run_id}/report", status_code=303)


@app.get("/runs/{run_id}/report", response_class=PlainTextResponse)
def report(run_id: int):
    existing = store.get_report(run_id)
    if existing:
        return existing["report_text"]
    report_text = generate_run_report(store.get_run(run_id), store.list_run_checks(run_id))
    store.save_report(run_id, report_text)
    return report_text


@app.get("/export.json")
def export_json():
    runs = store.list_runs()
    return {"runs": [{**run, "checks": store.list_run_checks(run["id"])} for run in runs]}
