from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
@dataclass(frozen=True)
class FleetSite:
    name: str; url: str; uptime_ok: bool; ssl_days: int; wp_updates: int; backup_age_hours: int; response_ms: int; security_header_count: int
    def to_dict(self) -> dict: return asdict(self)
@dataclass(frozen=True)
class Alert:
    site: str; severity: str; message: str


def normalize_site(site: FleetSite) -> FleetSite:
    parsed = urlsplit(site.url.strip())
    url = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), parsed.query, parsed.fragment))
    return FleetSite(site.name.strip(), url, site.uptime_ok, site.ssl_days, site.wp_updates, site.backup_age_hours, site.response_ms, site.security_header_count)


def calculate_health_score(site: FleetSite) -> int:
    score=100
    if not site.uptime_ok: score-=45
    if site.ssl_days < 14: score-=25
    elif site.ssl_days < 30: score-=10
    if site.wp_updates: score-=min(20, site.wp_updates*3)
    if site.backup_age_hours > 72: score-=20
    elif site.backup_age_hours > 36: score-=8
    if site.response_ms > 1500: score-=10
    if site.security_header_count < 2: score-=6
    return max(0,min(100,score))

def generate_alerts(site: FleetSite) -> list[Alert]:
    alerts=[]
    if not site.uptime_ok: alerts.append(Alert(site.name,'critical',f'{site.name} appears down or unreachable.'))
    if site.ssl_days < 30: alerts.append(Alert(site.name,'critical' if site.ssl_days < 7 else 'warning',f'SSL expires in {site.ssl_days} day(s).'))
    if site.wp_updates: alerts.append(Alert(site.name,'warning',f'{site.wp_updates} WordPress updates pending.'))
    if site.backup_age_hours > 72: alerts.append(Alert(site.name,'critical',f'Latest backup is {site.backup_age_hours} hours old.'))
    if site.response_ms > 1500: alerts.append(Alert(site.name,'warning',f'Homepage response time is {site.response_ms} ms.'))
    if site.security_header_count < 2: alerts.append(Alert(site.name,'info','Security headers need review.'))
    return alerts

def generate_maintenance_report(sites: list[FleetSite]) -> str:
    lines=['# WP FleetOps Maintenance Report','',f'Generated: {datetime.now(timezone.utc).isoformat()}','']
    scored=[(s,calculate_health_score(s),generate_alerts(s)) for s in sites]
    average_score=round(sum(score for _,score,_ in scored)/len(scored)) if scored else 0
    lines += [f'Sites monitored: {len(sites)}', f'Average fleet score: {average_score}/100', f"Critical sites: {sum(1 for _,_,a in scored if any(x.severity=='critical' for x in a))}", '']
    for site,score,alerts in scored:
        state='Healthy' if score>=85 else ('Watch' if score>=65 else 'Needs attention')
        lines += [f'## {site.name} — {state}', '', f'Score: {score}/100', f'URL: {site.url}', '']
        lines += ['Recommended actions:']
        lines += [f'- [{a.severity}] {a.message}' for a in alerts] if alerts else ['- Continue normal maintenance cadence.']
        lines.append('')
    return '\n'.join(lines).strip()+'\n'
