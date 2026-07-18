from __future__ import annotations
import json
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from .checks import SiteCheck, evaluate_site, fetch_basic_site_check, summarize_report
from .storage import CarePulseStore, normalize_site_url
BASE = Path(__file__).resolve().parent.parent
app = FastAPI(title='WP CarePulse')
templates = Jinja2Templates(directory=str(BASE / 'templates'))
store = CarePulseStore(BASE / 'data' / 'carepulse.sqlite3')
@app.get('/health')
def health(): return {'status': 'ok', 'app': 'wp-carepulse'}
@app.get('/', response_class=HTMLResponse)
def index(request: Request): return templates.TemplateResponse(request, 'index.html', {'sites': store.list_sites(), 'checks': store.latest_checks()})
@app.post('/sites')
def add_site(name: str = Form(...), url: str = Form(...), client: str = Form('')):
    try:
        site_id = store.add_site(name, url, client)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    check = fetch_basic_site_check(name, url); store.save_check(site_id, check); return RedirectResponse('/', status_code=303)
@app.post('/manual-check')
def manual_check(name: str = Form(...), url: str = Form(...), client: str = Form(''), http_status: Annotated[int, Form(ge=100, le=599)] = 200, latency_ms: int = Form(250), ssl_days_remaining: int = Form(60), wordpress_version: str = Form('unknown'), update_count: int = Form(0), backup_age_hours: int = Form(24)):
    try:
        normalized_url = normalize_site_url(url)
        site_id = store.add_site(name, normalized_url, client)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    check = evaluate_site(
        name,
        normalized_url,
        http_status,
        latency_ms,
        ssl_days_remaining,
        wordpress_version,
        update_count,
        backup_age_hours,
        {},
    )
    store.save_check(site_id, check)
    return RedirectResponse('/', status_code=303)
@app.get('/report', response_class=PlainTextResponse)
def report():
    checks = [SiteCheck(**json.loads(row['raw_json'])) for row in store.latest_checks()]
    return summarize_report(checks)
