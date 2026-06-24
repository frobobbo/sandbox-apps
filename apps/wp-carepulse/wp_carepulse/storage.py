from __future__ import annotations
import json, sqlite3
from pathlib import Path
from urllib.parse import urlparse
from .checks import SiteCheck

def normalize_site_url(url: str) -> str:
    candidate = url.strip()
    if '://' not in candidate:
        candidate = f'https://{candidate}'
    parsed = urlparse(candidate)
    if parsed.path == '/' and not parsed.query and not parsed.fragment:
        candidate = candidate.rstrip('/')
    return candidate

class CarePulseStore:
    def __init__(self, path: str | Path = 'data/carepulse.sqlite3'):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self._init()
    def _connect(self):
        con = sqlite3.connect(self.path); con.row_factory = sqlite3.Row; return con
    def _init(self):
        with self._connect() as con:
            con.execute('create table if not exists sites (id integer primary key autoincrement, name text not null, url text not null unique, client text not null default "", created_at text not null default current_timestamp)')
            con.execute('create table if not exists checks (id integer primary key autoincrement, site_id integer not null references sites(id), checked_at text not null, status text not null, score integer not null, http_status integer not null, latency_ms integer not null, ssl_days_remaining integer not null, wordpress_version text not null, update_count integer not null, backup_age_hours integer not null, summary text not null, actions_json text not null, raw_json text not null)')
    def add_site(self, name: str, url: str, client: str = '') -> int:
        url = normalize_site_url(url)
        with self._connect() as con:
            cur = con.execute('insert or ignore into sites(name,url,client) values(?,?,?)', (name, url, client))
            if cur.lastrowid: return int(cur.lastrowid)
            return int(con.execute('select id from sites where url=?', (url,)).fetchone()['id'])
    def list_sites(self) -> list[dict]:
        with self._connect() as con: return [dict(r) for r in con.execute('select * from sites order by name')]
    def save_check(self, site_id: int, check: SiteCheck) -> int:
        with self._connect() as con:
            cur = con.execute('insert into checks(site_id,checked_at,status,score,http_status,latency_ms,ssl_days_remaining,wordpress_version,update_count,backup_age_hours,summary,actions_json,raw_json) values(?,?,?,?,?,?,?,?,?,?,?,?,?)', (site_id, check.checked_at, check.status, check.score, check.http_status, check.latency_ms, check.ssl_days_remaining, check.wordpress_version, check.update_count, check.backup_age_hours, check.summary, json.dumps(check.actions), json.dumps(check.to_dict())))
            return int(cur.lastrowid)
    def latest_checks(self) -> list[dict]:
        sql = 'select s.name, s.url, s.client, c.* from checks c join sites s on s.id=c.site_id where c.id in (select max(id) from checks group by site_id) order by s.name'
        with self._connect() as con:
            rows=[]
            for r in con.execute(sql):
                d=dict(r); d['actions']=json.loads(d.pop('actions_json')); rows.append(d)
            return rows
