"""DuckDB analytics engine for augmentation event data."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    import duckdb
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("AUGMENTATION_DB", str(_ROOT / "data" / "sqlite" / "augmentation.db")))


@dataclass
class QueryResult:
    columns: List[str]
    rows: List[Dict]
    row_count: int

    def to_dict(self):
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
        }


def query(sql: str, db_path: str = None) -> QueryResult:
    """Execute a SQL query against the augmentation SQLite DB via DuckDB."""
    if not AVAILABLE:
        return QueryResult(columns=[], rows=[], row_count=0)

    db = db_path or str(DB_PATH)
    try:
        conn = duckdb.connect()
        conn.execute(f"ATTACH '{db}' AS aug (TYPE SQLITE)")
        result = conn.execute(f"SELECT * FROM aug.{sql}" if not sql.strip().upper().startswith("SELECT") else f"SELECT * FROM aug.({sql})" if "(" not in sql else f"SELECT * FROM aug.{sql}")
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        conn.close()
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
    except Exception as e:
        # Fallback: try direct path
        try:
            conn = duckdb.connect()
            result = conn.execute(f"SELECT * FROM sqlite_scan('{db}', 'events') LIMIT 5")
            columns = [desc[0] for desc in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            conn.close()
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        except Exception as e2:
            return QueryResult(columns=[], rows=[{"error": str(e2)}], row_count=0)


def get_event_summary(project: str = None) -> Dict:
    """Get event summary statistics."""
    if not AVAILABLE:
        return {"error": "duckdb not installed"}

    try:
        conn = duckdb.connect()
        conn.execute(f"ATTACH '{DB_PATH}' AS aug (TYPE SQLITE)")

        where = f"WHERE project = '{project}'" if project else ""
        result = conn.execute(f"""
            SELECT
                event_type,
                COUNT(*) as count,
                AVG(duration_ms) as avg_duration_ms,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures
            FROM aug.events
            {where}
            GROUP BY event_type
            ORDER BY count DESC
        """)
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        conn.close()
        return {"summary": rows}
    except Exception as e:
        return {"error": str(e)}


def get_task_metrics(project: str = None) -> Dict:
    """Get task completion metrics."""
    if not AVAILABLE:
        return {"error": "duckdb not installed"}

    try:
        conn = duckdb.connect()
        conn.execute(f"ATTACH '{DB_PATH}' AS aug (TYPE SQLITE)")

        where = f"WHERE project = '{project}'" if project else ""
        result = conn.execute(f"""
            SELECT
                task_type,
                COUNT(*) as total,
                SUM(CASE WHEN result = 'pass' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN result = 'fail' THEN 1 ELSE 0 END) as failed,
                AVG(CASE WHEN files_changed IS NOT NULL THEN CAST(files_changed AS DOUBLE) END) as avg_files_changed
            FROM aug.tasks
            {where}
            GROUP BY task_type
        """)
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        conn.close()
        return {"metrics": rows}
    except Exception as e:
        return {"error": str(e)}


def get_verification_trends() -> Dict:
    """Get verification run trends over time."""
    if not AVAILABLE:
        return {"error": "duckdb not installed"}

    try:
        conn = duckdb.connect()
        conn.execute(f"ATTACH '{DB_PATH}' AS aug (TYPE SQLITE)")

        result = conn.execute("""
            SELECT
                level,
                COUNT(*) as runs,
                AVG(passed) as avg_passed,
                AVG(failed) as avg_failed,
                AVG(duration_ms) as avg_duration_ms
            FROM aug.verification_runs
            GROUP BY level
            ORDER BY runs DESC
        """)
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        conn.close()
        return {"trends": rows}
    except Exception as e:
        return {"error": str(e)}


def execute_custom(sql: str) -> Dict:
    """Execute arbitrary SQL against the augmentation DB."""
    if not AVAILABLE:
        return {"error": "duckdb not installed"}

    try:
        conn = duckdb.connect()
        conn.execute(f"ATTACH '{DB_PATH}' AS aug (TYPE SQLITE)")
        result = conn.execute(f"SELECT * FROM aug.({sql})")
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        conn.close()
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Demo queries
    print("=== Event Summary ===")
    print(json.dumps(get_event_summary(), indent=2))

    print("\n=== Task Metrics ===")
    print(json.dumps(get_task_metrics(), indent=2))

    print("\n=== Verification Trends ===")
    print(json.dumps(get_verification_trends(), indent=2))
