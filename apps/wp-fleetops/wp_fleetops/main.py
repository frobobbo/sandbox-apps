from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from .fleet import FleetSite, calculate_health_score, generate_alerts, generate_maintenance_report
from .storage import FleetOpsStore
BASE=Path(__file__).resolve().parent.parent
app=FastAPI(title='WP FleetOps')
templates=Jinja2Templates(directory=str(BASE/'templates'))
store=FleetOpsStore(BASE/'data'/'fleetops.sqlite3')
@app.get('/health')
def health(): return {'status':'ok','app':'wp-fleetops'}
@app.get('/', response_class=HTMLResponse)
def index(request: Request): return templates.TemplateResponse(request,'index.html',{'rows':store.latest_dashboard()})
@app.post('/snapshot')
def snapshot(name: str=Form(...), url: str=Form(...), uptime_ok: bool=Form(True), ssl_days: int=Form(60), wp_updates: int=Form(0), backup_age_hours: int=Form(24), response_ms: int=Form(250), security_header_count: int=Form(3)):
    site=FleetSite(name,url,uptime_ok,ssl_days,wp_updates,backup_age_hours,response_ms,security_header_count); sid=store.upsert_site(site); store.save_snapshot(sid, site, calculate_health_score(site), generate_alerts(site)); return RedirectResponse('/', status_code=303)
@app.get('/report', response_class=PlainTextResponse)
def report():
    sites=[FleetSite(r['name'],r['url'],bool(r['uptime_ok']),r['ssl_days'],r['wp_updates'],r['backup_age_hours'],r['response_ms'],r['security_header_count']) for r in store.latest_dashboard()]
    return generate_maintenance_report(sites)
