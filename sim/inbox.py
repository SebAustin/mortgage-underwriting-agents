"""The local Action Inbox — a SQLite store that mirrors UiPath Action Center.

Holds case records and the human tasks raised at gates. ``run`` writes a pending task
when a case suspends; ``approve`` resolves it and resumes the case (possibly in another
process). The persona's mock directory is stored alongside the case so a fresh process
can rebuild the platform port to resume.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class CaseRecord:
    case_id: str
    persona: str
    status: str  # running | suspended | closed
    terminal_decision: str | None
    directory_json: str


@dataclass
class TaskRecord:
    task_id: str
    case_id: str
    gate: str
    title: str
    summary: str
    options: list[str]
    context: dict
    status: str  # pending | resolved
    choice: str | None
    note: str | None


def _now() -> str:
    return datetime.now(UTC).isoformat()


class InboxStore:
    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                persona TEXT,
                status TEXT,
                terminal_decision TEXT,
                directory_json TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                case_id TEXT,
                gate TEXT,
                title TEXT,
                summary TEXT,
                options_json TEXT,
                context_json TEXT,
                status TEXT,
                choice TEXT,
                note TEXT,
                created_at TEXT,
                resolved_at TEXT
            );
            """
        )
        self.conn.commit()

    # — cases —
    def upsert_case(
        self,
        case_id: str,
        persona: str,
        status: str,
        directory_json: str,
        terminal_decision: str | None = None,
    ) -> None:
        now = _now()
        self.conn.execute(
            """
            INSERT INTO cases (case_id, persona, status, terminal_decision, directory_json,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                persona=excluded.persona,
                status=excluded.status,
                terminal_decision=excluded.terminal_decision,
                directory_json=excluded.directory_json,
                updated_at=excluded.updated_at
            """,
            (case_id, persona, status, terminal_decision, directory_json, now, now),
        )
        self.conn.commit()

    def get_case(self, case_id: str) -> CaseRecord | None:
        row = self.conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
        if row is None:
            return None
        return CaseRecord(
            case_id=row["case_id"],
            persona=row["persona"],
            status=row["status"],
            terminal_decision=row["terminal_decision"],
            directory_json=row["directory_json"],
        )

    def list_cases(self) -> list[CaseRecord]:
        rows = self.conn.execute("SELECT * FROM cases ORDER BY created_at").fetchall()
        return [
            CaseRecord(r["case_id"], r["persona"], r["status"], r["terminal_decision"],
                       r["directory_json"])
            for r in rows
        ]

    # — tasks —
    def add_task(
        self,
        task_id: str,
        case_id: str,
        gate: str,
        title: str,
        summary: str,
        options: list[str],
        context: dict,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO tasks (task_id, case_id, gate, title, summary, options_json,
                               context_json, status, choice, note, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', NULL, NULL, ?, NULL)
            """,
            (task_id, case_id, gate, title, summary, json.dumps(options),
             json.dumps(context), _now()),
        )
        self.conn.commit()

    def resolve_task(self, task_id: str, choice: str, note: str) -> None:
        self.conn.execute(
            "UPDATE tasks SET status='resolved', choice=?, note=?, resolved_at=? WHERE task_id=?",
            (choice, note, _now(), task_id),
        )
        self.conn.commit()

    def get_task(self, task_id: str) -> TaskRecord | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_pending(self) -> list[TaskRecord]:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE status='pending' ORDER BY created_at"
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            case_id=row["case_id"],
            gate=row["gate"],
            title=row["title"],
            summary=row["summary"],
            options=json.loads(row["options_json"]),
            context=json.loads(row["context_json"]),
            status=row["status"],
            choice=row["choice"],
            note=row["note"],
        )

    def close(self) -> None:
        self.conn.close()
