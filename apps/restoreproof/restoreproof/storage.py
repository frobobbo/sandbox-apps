from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .proof import RestoreAssessment, normalize_url


class RestoreProofStore:
    def __init__(self, path: str | Path = "data/restoreproof.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                create table if not exists sites (
                    id integer primary key autoincrement,
                    name text not null,
                    url text not null unique,
                    client text not null default '',
                    created_at text not null default current_timestamp
                )
                """
            )
            con.execute(
                """
                create table if not exists backups (
                    id integer primary key autoincrement,
                    site_id integer not null references sites(id),
                    label text not null,
                    created_at text not null,
                    size_mb integer not null,
                    storage_location text not null,
                    notes text not null default ''
                )
                """
            )
            con.execute(
                """
                create table if not exists restore_runs (
                    id integer primary key autoincrement,
                    site_id integer not null references sites(id),
                    backup_id integer not null references backups(id),
                    started_at text not null default current_timestamp,
                    restore_target_url text not null,
                    status text not null,
                    score integer not null,
                    summary text not null,
                    actions_json text not null,
                    assessment_json text not null
                )
                """
            )

    def add_site(self, name: str, url: str, client: str = "") -> int:
        name = name.strip()
        if not name:
            raise ValueError("Please enter a site name.")
        normalized = normalize_url(url)
        with self._connect() as con:
            cur = con.execute(
                "insert or ignore into sites(name, url, client) values(?,?,?)",
                (name, normalized, client.strip()),
            )
            if cur.lastrowid:
                return int(cur.lastrowid)
            return int(con.execute("select id from sites where url=?", (normalized,)).fetchone()["id"])

    def list_sites(self) -> list[dict]:
        with self._connect() as con:
            return [dict(r) for r in con.execute("select * from sites order by name")]

    def get_site(self, site_id: int) -> dict:
        with self._connect() as con:
            row = con.execute("select * from sites where id=?", (site_id,)).fetchone()
        if not row:
            raise KeyError(f"Site {site_id} not found")
        return dict(row)

    def add_backup(self, site_id: int, label: str, created_at: str, size_mb: int, storage_location: str, notes: str = "") -> int:
        label = label.strip()
        storage_location = storage_location.strip()
        if not label:
            raise ValueError("Please enter a backup label.")
        if size_mb < 0:
            raise ValueError("Backup size cannot be negative.")
        if not storage_location:
            raise ValueError("Please enter a backup storage location.")
        self.get_site(site_id)
        with self._connect() as con:
            cur = con.execute(
                "insert into backups(site_id,label,created_at,size_mb,storage_location,notes) values(?,?,?,?,?,?)",
                (site_id, label, created_at.strip(), size_mb, storage_location, notes.strip()),
            )
            if cur.lastrowid is None:
                raise RuntimeError("Backup insert did not return an id.")
            return int(cur.lastrowid)

    def get_backup(self, backup_id: int) -> dict:
        with self._connect() as con:
            row = con.execute("select * from backups where id=?", (backup_id,)).fetchone()
        if not row:
            raise KeyError(f"Backup {backup_id} not found")
        return dict(row)

    def list_backups(self, site_id: int | None = None) -> list[dict]:
        sql = "select b.*, s.name as site_name from backups b join sites s on s.id=b.site_id"
        params: tuple = ()
        if site_id is not None:
            sql += " where b.site_id=?"
            params = (site_id,)
        sql += " order by b.id desc"
        with self._connect() as con:
            return [dict(r) for r in con.execute(sql, params)]

    def save_restore_run(self, site_id: int, backup_id: int, assessment: RestoreAssessment) -> int:
        self.get_site(site_id)
        backup = self.get_backup(backup_id)
        if backup["site_id"] != site_id:
            raise ValueError("Backup does not belong to the selected site.")
        with self._connect() as con:
            cur = con.execute(
                """
                insert into restore_runs(site_id,backup_id,restore_target_url,status,score,summary,actions_json,assessment_json)
                values(?,?,?,?,?,?,?,?)
                """,
                (
                    site_id,
                    backup_id,
                    assessment.evidence.restore_target_url,
                    assessment.status,
                    assessment.score,
                    assessment.summary,
                    json.dumps(assessment.actions),
                    json.dumps(assessment.to_dict()),
                ),
            )
            if cur.lastrowid is None:
                raise RuntimeError("Restore run insert did not return an id.")
            return int(cur.lastrowid)

    def latest_runs(self) -> list[dict]:
        sql = """
        select r.*, s.name as site_name, s.client, s.url as site_url, b.label as backup_label, b.size_mb, b.storage_location
        from restore_runs r
        join sites s on s.id=r.site_id
        join backups b on b.id=r.backup_id
        where r.id in (select max(id) from restore_runs group by site_id)
        order by s.name
        """
        with self._connect() as con:
            rows = []
            for row in con.execute(sql):
                item = dict(row)
                item["actions"] = json.loads(item.pop("actions_json"))
                rows.append(item)
            return rows

    def get_run_bundle(self, run_id: int):
        from .proof import RestoreAssessment, RestoreEvidence

        with self._connect() as con:
            row = con.execute("select * from restore_runs where id=?", (run_id,)).fetchone()
        if not row:
            raise KeyError(f"Restore run {run_id} not found")
        run = dict(row)
        assessment_data = json.loads(run["assessment_json"])
        evidence = RestoreEvidence(**assessment_data["evidence"])
        assessment = RestoreAssessment(
            assessed_at=assessment_data["assessed_at"],
            status=assessment_data["status"],
            score=assessment_data["score"],
            summary=assessment_data["summary"],
            actions=assessment_data["actions"],
            evidence=evidence,
        )
        return self.get_site(run["site_id"]), self.get_backup(run["backup_id"]), run, assessment
