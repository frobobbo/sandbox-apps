from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError("Enter a valid URL")
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a valid URL")
    path = parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


class PatchPilotStore:
    def __init__(self, path: str | Path = "data/patchpilot.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.execute("""create table if not exists sites(
                id integer primary key autoincrement,
                name text not null,
                base_url text not null unique,
                client_name text not null default '',
                created_at text not null default current_timestamp
            )""")
            con.execute("""create table if not exists site_pages(
                id integer primary key autoincrement,
                site_id integer not null references sites(id),
                label text not null,
                url text not null,
                baseline_title text,
                created_at text not null default current_timestamp,
                unique(site_id, url)
            )""")
            con.execute("""create table if not exists maintenance_runs(
                id integer primary key autoincrement,
                site_id integer not null references sites(id),
                notes text not null default '',
                status text not null default 'complete',
                created_at text not null default current_timestamp
            )""")
            con.execute("""create table if not exists page_checks(
                id integer primary key autoincrement,
                run_id integer not null references maintenance_runs(id),
                page_id integer not null references site_pages(id),
                url text not null,
                http_status integer,
                title text,
                baseline_title text,
                status text not null,
                warnings_json text not null,
                elapsed_ms integer not null default 0,
                evidence_text text not null default '',
                screenshot_path text,
                created_at text not null default current_timestamp
            )""")
            con.execute("""create table if not exists reports(
                id integer primary key autoincrement,
                run_id integer not null unique references maintenance_runs(id),
                report_text text not null,
                created_at text not null default current_timestamp
            )""")

    def add_site(self, name: str, base_url: str, client_name: str = "") -> int:
        if not name.strip():
            raise ValueError("Enter a site name")
        normalized = normalize_url(base_url)
        with self._connect() as con:
            cur = con.execute("insert or ignore into sites(name, base_url, client_name) values(?,?,?)", (name.strip(), normalized, client_name.strip()))
            if cur.lastrowid:
                return int(cur.lastrowid)
            con.execute("update sites set name=?, client_name=? where base_url=?", (name.strip(), client_name.strip(), normalized))
            return int(con.execute("select id from sites where base_url=?", (normalized,)).fetchone()["id"])

    def list_sites(self) -> list[dict]:
        with self._connect() as con:
            return [dict(r) for r in con.execute("select * from sites order by name")]

    def get_site(self, site_id: int) -> dict:
        with self._connect() as con:
            row = con.execute("select * from sites where id=?", (site_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown site {site_id}")
            return dict(row)

    def add_page(self, site_id: int, label: str, url: str, baseline_title: str | None = None) -> int:
        if not label.strip():
            raise ValueError("Enter a page label")
        normalized = normalize_url(url)
        with self._connect() as con:
            cur = con.execute("insert or ignore into site_pages(site_id,label,url,baseline_title) values(?,?,?,?)", (site_id, label.strip(), normalized, baseline_title or None))
            if cur.lastrowid:
                return int(cur.lastrowid)
            con.execute("update site_pages set label=?, baseline_title=? where site_id=? and url=?", (label.strip(), baseline_title or None, site_id, normalized))
            return int(con.execute("select id from site_pages where site_id=? and url=?", (site_id, normalized)).fetchone()["id"])

    def list_pages(self, site_id: int) -> list[dict]:
        with self._connect() as con:
            return [dict(r) for r in con.execute("select * from site_pages where site_id=? order by id", (site_id,))]

    def start_run(self, site_id: int, notes: str = "") -> int:
        with self._connect() as con:
            cur = con.execute("insert into maintenance_runs(site_id, notes) values(?,?)", (site_id, notes.strip()))
            return int(cur.lastrowid)

    def list_runs(self, site_id: int | None = None) -> list[dict]:
        sql = "select r.*, s.name site_name, s.base_url site_url, s.client_name from maintenance_runs r join sites s on s.id=r.site_id"
        params: tuple = ()
        if site_id is not None:
            sql += " where r.site_id=?"
            params = (site_id,)
        sql += " order by r.id desc"
        with self._connect() as con:
            return [dict(r) for r in con.execute(sql, params)]

    def get_run(self, run_id: int) -> dict:
        with self._connect() as con:
            row = con.execute("""select r.*, s.name site_name, s.base_url site_url, s.client_name
                from maintenance_runs r join sites s on s.id=r.site_id where r.id=?""", (run_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown run {run_id}")
            return dict(row)

    def save_page_check(self, run_id: int, page_id: int, url: str, http_status: int | None, title: str | None, baseline_title: str | None, status: str, warnings: list[str], elapsed_ms: int, evidence_text: str, screenshot_path: str | None = None) -> int:
        with self._connect() as con:
            cur = con.execute("""insert into page_checks(run_id,page_id,url,http_status,title,baseline_title,status,warnings_json,elapsed_ms,evidence_text,screenshot_path)
                values(?,?,?,?,?,?,?,?,?,?,?)""", (run_id, page_id, url, http_status, title, baseline_title, status, json.dumps(warnings), elapsed_ms, evidence_text, screenshot_path))
            return int(cur.lastrowid)

    def list_run_checks(self, run_id: int) -> list[dict]:
        with self._connect() as con:
            rows = []
            for r in con.execute("""select pc.*, sp.label from page_checks pc join site_pages sp on sp.id=pc.page_id
                where pc.run_id=? order by pc.id""", (run_id,)):
                item = dict(r)
                item["warnings"] = json.loads(item.pop("warnings_json"))
                rows.append(item)
            return rows

    def save_report(self, run_id: int, report_text: str) -> int:
        with self._connect() as con:
            con.execute("insert into reports(run_id, report_text) values(?,?) on conflict(run_id) do update set report_text=excluded.report_text, created_at=current_timestamp", (run_id, report_text))
            return int(con.execute("select id from reports where run_id=?", (run_id,)).fetchone()["id"])

    def get_report(self, run_id: int) -> dict | None:
        with self._connect() as con:
            row = con.execute("select * from reports where run_id=?", (run_id,)).fetchone()
            return dict(row) if row else None
