"""Universal Engineering Augmentation Event Log - SQLite-backed engineering event tracking."""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("AUGMENTATION_DB", str(_ROOT / "data" / "sqlite" / "augmentation.db")))
SCHEMA_PATH = Path(os.environ.get("AUGMENTATION_SCHEMA", str(_ROOT / "data" / "sqlite" / "schema.sql")))


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.close()


@contextmanager
def log_event(event_type, project=None, session_id=None, **kwargs):
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO events (event_type, project, session_id, stage, tool, detail,
               duration_ms, tokens_in, tokens_out, cost_usd, candidate_id,
               verification_result, skill_name, success, error, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_type, project, session_id,
             kwargs.get("stage"), kwargs.get("tool"), kwargs.get("detail"),
             kwargs.get("duration_ms"), kwargs.get("tokens_in"), kwargs.get("tokens_out"),
             kwargs.get("cost_usd"), kwargs.get("candidate_id"),
             kwargs.get("verification_result"), kwargs.get("skill_name"),
             kwargs.get("success", 1), kwargs.get("error"),
             json.dumps(kwargs.get("metadata")) if kwargs.get("metadata") else None)
        )
        conn.commit()
        yield cursor.lastrowid
    finally:
        conn.close()


def log_task(task_type, project, description, session_id=None, verification_level=None):
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO tasks (session_id, project, task_type, description, verification_level)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, project, task_type, description, verification_level)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def complete_task(task_id, result=None, files_changed=None, risk_level=None):
    conn = get_db()
    try:
        conn.execute(
            """UPDATE tasks SET completed_at=CURRENT_TIMESTAMP, result=?,
               files_changed=?, risk_level=? WHERE id=?""",
            (result, files_changed, risk_level, task_id)
        )
        conn.commit()
    finally:
        conn.close()


def log_verification(task_id, project, level, checks, passed=0, failed=0, skipped=0, duration_ms=0):
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO verification_runs (task_id, project, level, checks,
               passed, failed, skipped, duration_ms, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (task_id, project, level, json.dumps(checks), passed, failed, skipped, duration_ms)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def log_candidate(candidate_id, project, problem, approach, worktree_path=None):
    conn = get_db()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO candidates (id, project, problem, approach, worktree_path)
               VALUES (?, ?, ?, ?, ?)""",
            (candidate_id, project, problem, approach, worktree_path)
        )
        conn.commit()
    finally:
        conn.close()


def update_candidate(candidate_id, **kwargs):
    conn = get_db()
    try:
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in ("status", "test_result", "verification_result", "selected", "notes"):
                sets.append(f"{k}=?")
                vals.append(v)
        if sets:
            vals.append(candidate_id)
            conn.execute(f"UPDATE candidates SET {', '.join(sets)} WHERE id=?", vals)
            conn.commit()
    finally:
        conn.close()


def register_skill(name, project, category, description, preconditions=None, verification_level=None):
    conn = get_db()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO skills (name, project, category, description,
               preconditions, verification_level) VALUES (?, ?, ?, ?, ?, ?)""",
            (name, project, category, description, preconditions, verification_level)
        )
        conn.commit()
    finally:
        conn.close()


def record_skill_use(name, success=True):
    conn = get_db()
    try:
        if success:
            conn.execute(
                "UPDATE skills SET success_count=success_count+1, last_used=CURRENT_TIMESTAMP WHERE name=?",
                (name,)
            )
        else:
            conn.execute(
                "UPDATE skills SET failure_count=failure_count+1, last_used=CURRENT_TIMESTAMP WHERE name=?",
                (name,)
            )
        conn.commit()
    finally:
        conn.close()


def get_project_stats(project):
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT
                COUNT(*) as total_events,
                SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures,
                SUM(duration_ms) as total_duration_ms,
                SUM(COALESCE(tokens_in,0)) + SUM(COALESCE(tokens_out,0)) as total_tokens,
                SUM(COALESCE(cost_usd,0)) as total_cost
               FROM events WHERE project=?""",
            (project,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_recent_events(project=None, limit=50):
    conn = get_db()
    try:
        if project:
            rows = conn.execute(
                "SELECT * FROM events WHERE project=? ORDER BY timestamp DESC LIMIT ?",
                (project, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Event log initialized at {DB_PATH}")
