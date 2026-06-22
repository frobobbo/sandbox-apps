from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class RunbookRecord:
    id: int
    title: str
    system: str
    runbook_type: str
    tags: str
    raw_notes: str
    markdown: str
    bookstack_page_id: str | None
    created_at: str
    updated_at: str


class RunbookStore:
    def __init__(self, db_path: str | Path = "data/runbooks.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    system TEXT NOT NULL,
                    runbook_type TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '',
                    raw_notes TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    bookstack_page_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_runbook(
        self,
        *,
        title: str,
        system: str,
        runbook_type: str,
        tags: str,
        raw_notes: str,
        markdown: str,
    ) -> RunbookRecord:
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO runbooks (title, system, runbook_type, tags, raw_notes, markdown, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, system, runbook_type, tags, raw_notes, markdown, now, now),
            )
            connection.commit()
            record_id = int(cursor.lastrowid)
        record = self.get_runbook(record_id)
        if record is None:
            raise RuntimeError("Failed to load newly created runbook")
        return record

    def update_markdown(self, record_id: int, markdown: str) -> RunbookRecord | None:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                "UPDATE runbooks SET markdown = ?, updated_at = ? WHERE id = ?",
                (markdown, now, record_id),
            )
            connection.commit()
        return self.get_runbook(record_id)

    def mark_published(self, record_id: int, bookstack_page_id: str) -> RunbookRecord | None:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                "UPDATE runbooks SET bookstack_page_id = ?, updated_at = ? WHERE id = ?",
                (bookstack_page_id, now, record_id),
            )
            connection.commit()
        return self.get_runbook(record_id)

    def get_runbook(self, record_id: int) -> RunbookRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runbooks WHERE id = ?", (record_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_runbooks(self) -> list[RunbookRecord]:
        with self._connect() as connection:
            rows: Iterable[sqlite3.Row] = connection.execute(
                "SELECT * FROM runbooks ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row: sqlite3.Row) -> RunbookRecord:
    return RunbookRecord(
        id=int(row["id"]),
        title=str(row["title"]),
        system=str(row["system"]),
        runbook_type=str(row["runbook_type"]),
        tags=str(row["tags"]),
        raw_notes=str(row["raw_notes"]),
        markdown=str(row["markdown"]),
        bookstack_page_id=row["bookstack_page_id"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
