from __future__ import annotations
import csv
import io
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from .fleet import FleetSite, calculate_health_score, generate_alerts, generate_maintenance_report, normalize_site
from .storage import FleetOpsStore
BASE=Path(__file__).resolve().parent.parent
app=FastAPI(title='WP FleetOps')
templates=Jinja2Templates(directory=str(BASE/'templates'))
store=FleetOpsStore(BASE/'data'/'fleetops.sqlite3')
@app.get('/health')
def health(): return {'status':'ok','app':'wp-fleetops'}
@app.get('/ready')
def ready(response: Response):
    try:
        store.latest_dashboard()
        database_status='ok'
    except sqlite3.Error:
        database_status='unavailable'
    template_status='ok' if (BASE/'templates'/'index.html').is_file() else 'missing'
    is_ready=database_status == 'ok' and template_status == 'ok'
    if not is_ready: response.status_code=503
    return {'status':'ready' if is_ready else 'not-ready','app':'wp-fleetops','checks':{'database':database_status,'templates':template_status}}
@app.get('/', response_class=HTMLResponse)
def index(request: Request): return templates.TemplateResponse(request,'index.html',{'rows':store.latest_dashboard()})
@app.post('/snapshot')
def snapshot(name: str=Form(..., min_length=1), url: str=Form(..., min_length=1, pattern=r'^https?://'), uptime_ok: bool=Form(False), ssl_days: int=Form(60, ge=0), wp_updates: int=Form(0, ge=0), backup_age_hours: int=Form(24, ge=0), response_ms: int=Form(250, ge=0), security_header_count: int=Form(3, ge=0)):
    site=normalize_site(FleetSite(name,url,uptime_ok,ssl_days,wp_updates,backup_age_hours,response_ms,security_header_count))
    if not site.name:
        raise HTTPException(status_code=422, detail='Site name must not be blank')
    if not urlsplit(site.url).hostname:
        raise HTTPException(status_code=422, detail='URL must include a hostname')
    sid=store.upsert_site(site); store.save_snapshot(sid, site, calculate_health_score(site), generate_alerts(site)); return RedirectResponse('/', status_code=303)
@app.get('/report', response_class=PlainTextResponse)
def report():
    sites=[FleetSite(r['name'],r['url'],bool(r['uptime_ok']),r['ssl_days'],r['wp_updates'],r['backup_age_hours'],r['response_ms'],r['security_header_count']) for r in store.latest_dashboard()]
    return generate_maintenance_report(sites)

@app.get('/export.json')
def export_json():
    rows=store.latest_dashboard()
    scores=[r['score'] for r in rows]
    return {
        'summary': {
            'sites': len(rows),
            'critical_sites': sum(1 for r in rows if any(a['severity'] == 'critical' for a in r['alerts'])),
            'average_score': round(sum(scores)/len(scores)) if scores else 0,
        },
        'sites': rows,
    }

def _spreadsheet_safe(value: str) -> str:
    return f"'{value}" if value.startswith(('=', '+', '-', '@')) else value

@app.get('/export.csv')
def export_csv():
    fieldnames = [
        'name', 'url', 'score', 'status', 'ssl_days', 'wp_updates',
        'backup_age_hours', 'response_ms', 'security_header_count',
        'critical_alerts', 'warning_alerts', 'info_alerts', 'captured_at',
    ]
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in store.latest_dashboard():
        writer.writerow({
            'name': _spreadsheet_safe(row['name']),
            'url': row['url'],
            'score': row['score'],
            'status': 'up' if row['uptime_ok'] else 'down',
            'ssl_days': row['ssl_days'],
            'wp_updates': row['wp_updates'],
            'backup_age_hours': row['backup_age_hours'],
            'response_ms': row['response_ms'],
            'security_header_count': row['security_header_count'],
            'critical_alerts': sum(a['severity'] == 'critical' for a in row['alerts']),
            'warning_alerts': sum(a['severity'] == 'warning' for a in row['alerts']),
            'info_alerts': sum(a['severity'] == 'info' for a in row['alerts']),
            'captured_at': row['captured_at'],
        })
    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="wp-fleetops.csv"'},
    )
