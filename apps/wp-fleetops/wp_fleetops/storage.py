from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .fleet import FleetSite, Alert, normalize_site
class FleetOpsStore:
    def __init__(self, path: str | Path = 'data/fleetops.sqlite3'):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self._init()
    def _connect(self):
        con=sqlite3.connect(self.path); con.row_factory=sqlite3.Row; return con
    def _init(self):
        with self._connect() as con:
            con.execute('create table if not exists sites(id integer primary key autoincrement, name text not null, url text not null unique, created_at text not null default current_timestamp)')
            con.execute('create table if not exists snapshots(id integer primary key autoincrement, site_id integer not null references sites(id), captured_at text not null default current_timestamp, score integer not null, uptime_ok integer not null, ssl_days integer not null, wp_updates integer not null, backup_age_hours integer not null, response_ms integer not null, security_header_count integer not null, alerts_json text not null, raw_json text not null)')
    def upsert_site(self, site: FleetSite) -> int:
        site = normalize_site(site)
        with self._connect() as con:
            cur=con.execute('insert or ignore into sites(name,url) values(?,?)',(site.name,site.url))
            if cur.lastrowid: return int(cur.lastrowid)
            con.execute('update sites set name=? where url=?',(site.name,site.url))
            return int(con.execute('select id from sites where url=?',(site.url,)).fetchone()['id'])
    def save_snapshot(self, site_id: int, site: FleetSite, score: int, alerts: list[Alert]) -> int:
        with self._connect() as con:
            cur=con.execute('insert into snapshots(site_id,score,uptime_ok,ssl_days,wp_updates,backup_age_hours,response_ms,security_header_count,alerts_json,raw_json) values(?,?,?,?,?,?,?,?,?,?)',(site_id,score,int(site.uptime_ok),site.ssl_days,site.wp_updates,site.backup_age_hours,site.response_ms,site.security_header_count,json.dumps([a.__dict__ for a in alerts]),json.dumps(site.to_dict())))
            return int(cur.lastrowid)
    def latest_dashboard(self) -> list[dict]:
        sql='select s.name,s.url, sn.* from snapshots sn join sites s on s.id=sn.site_id where sn.id in (select max(id) from snapshots group by site_id) order by sn.score asc, s.name'
        with self._connect() as con:
            rows=[]
            for r in con.execute(sql):
                d=dict(r); d['alerts']=json.loads(d.pop('alerts_json')); rows.append(d)
            return rows
