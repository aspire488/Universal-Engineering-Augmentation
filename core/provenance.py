"""Feynman Provenance - Evidence lineage and audit trail.

Tracks the complete chain of evidence for every engineering decision:
    file_hash → timestamp → git_sha → source/tool/specialist → evidence lineage

This is NOT metadata logging — it's the Feynman principle:
"State your evidence. Show your work. Let others verify."
"""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("AUGMENTATION_DB", str(_ROOT / "data" / "sqlite" / "augmentation.db")))


@dataclass
class EvidenceNode:
    """A single piece of evidence in the lineage chain."""
    tool: str                  # which tool produced this evidence
    evidence_type: str         # syntax/type/test/security/complexity/etc.
    passed: bool               # did it pass?
    detail: str                # human-readable detail
    tool_version: str = "1.0"  # version of the tool
    metrics: Dict[str, Any] = field(default_factory=dict)  # numeric measurements
    timestamp: float = field(default_factory=time.time)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvenanceRecord:
    """Complete provenance for a single engineering action."""
    record_id: str                  # unique identifier
    file_path: str                  # file(s) affected
    file_hash: str                  # SHA-256 of file content before action
    git_sha: str                    # git SHA at time of action
    git_branch: str                 # git branch
    timestamp: float                # when the action happened
    specialist: Optional[str]       # which specialist was involved (if any)
    specialist_hash: Optional[str]  # hash of specialist definition
    tool: str                       # primary tool used
    evidence_chain: List[EvidenceNode] = field(default_factory=list)
    decision: str = ""              # what was decided
    outcome: str = ""               # what actually happened
    verification_level: str = "standard"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["evidence_chain"] = [e.to_dict() for e in self.evidence_chain]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file's content."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_git_info(workdir: str = None) -> Dict[str, str]:
    """Get current git SHA and branch."""
    workdir = workdir or os.getcwd()
    result = {"sha": "unknown", "branch": "unknown"}

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workdir, capture_output=True, text=True, timeout=5
        )
        if sha.returncode == 0:
            result["sha"] = sha.stdout.strip()[:12]
    except Exception:
        pass

    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workdir, capture_output=True, text=True, timeout=5
        )
        if branch.returncode == 0:
            result["branch"] = branch.stdout.strip()
    except Exception:
        pass

    return result


def generate_record_id() -> str:
    """Generate a unique record ID."""
    import uuid
    return f"prov-{uuid.uuid4().hex[:12]}"


class ProvenanceTracker:
    """Track evidence lineage for engineering actions.

    Each action gets a complete provenance record:
    - What file was changed
    - What its hash was before the change
    - What git state existed
    - What tools ran
    - What evidence each tool produced
    - What specialist was involved
    - What was decided and why

    This is the Feynman principle applied to engineering:
    every decision has a traceable evidence chain.

    Usage:
        tracker = ProvenanceTracker()
        record = tracker.start_record("src/auth.py", tool="systematic-debugging")
        record.evidence_chain.append(EvidenceNode(
            tool="tree-sitter", evidence_type="syntax", passed=True, detail="OK"
        ))
        record.decision = "Root cause: missing null check in line 42"
        tracker.commit_record(record)
    """

    def __init__(self, workdir: str = None):
        self._workdir = workdir or os.getcwd()
        self._records: List[ProvenanceRecord] = []

    def start_record(self, file_path: str, tool: str = "unknown",
                     specialist: str = None, specialist_hash: str = None) -> ProvenanceRecord:
        """Start a new provenance record. Call commit_record() when done."""
        git_info = get_git_info(self._workdir)
        abs_path = os.path.abspath(file_path)
        file_hash = compute_file_hash(abs_path) if os.path.exists(abs_path) else "nonexistent"

        record = ProvenanceRecord(
            record_id=generate_record_id(),
            file_path=abs_path,
            file_hash=file_hash,
            git_sha=git_info["sha"],
            git_branch=git_info["branch"],
            timestamp=time.time(),
            specialist=specialist,
            specialist_hash=specialist_hash,
            tool=tool,
        )
        self._records.append(record)
        return record

    def commit_record(self, record: ProvenanceRecord) -> str:
        """Commit a provenance record to the database."""
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                """INSERT INTO provenance
                   (record_id, file_path, file_hash, git_sha, git_branch,
                    timestamp, specialist, specialist_hash, tool,
                    evidence_chain, decision, outcome, verification_level, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.record_id, record.file_path, record.file_hash,
                    record.git_sha, record.git_branch, record.timestamp,
                    record.specialist, record.specialist_hash, record.tool,
                    json.dumps([e.to_dict() for e in record.evidence_chain]),
                    record.decision, record.outcome,
                    record.verification_level, json.dumps(record.metadata),
                )
            )
            conn.commit()
            return record.record_id
        finally:
            conn.close()

    def get_record(self, record_id: str) -> Optional[ProvenanceRecord]:
        """Retrieve a provenance record by ID."""
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM provenance WHERE record_id=?", (record_id,)
            ).fetchone()
            if row:
                return self._row_to_record(row)
            return None
        finally:
            conn.close()

    def get_records_for_file(self, file_path: str, limit: int = 50) -> List[ProvenanceRecord]:
        """Get all provenance records for a file."""
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            abs_path = os.path.abspath(file_path)
            rows = conn.execute(
                "SELECT * FROM provenance WHERE file_path=? ORDER BY timestamp DESC LIMIT ?",
                (abs_path, limit)
            ).fetchall()
            return [self._row_to_record(r) for r in rows]
        finally:
            conn.close()

    def get_records_by_specialist(self, specialist: str, limit: int = 50) -> List[ProvenanceRecord]:
        """Get all provenance records for a specialist."""
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM provenance WHERE specialist=? ORDER BY timestamp DESC LIMIT ?",
                (specialist, limit)
            ).fetchall()
            return [self._row_to_record(r) for r in rows]
        finally:
            conn.close()

    def verify_integrity(self, record: ProvenanceRecord) -> Dict[str, Any]:
        """Verify the integrity of a provenance record.
        Checks that the file hash matches current content.
        """
        result = {"valid": True, "checks": []}

        if os.path.exists(record.file_path):
            current_hash = compute_file_hash(record.file_path)
            hash_match = current_hash == record.file_hash
            result["checks"].append({
                "check": "file_hash",
                "valid": hash_match,
                "detail": f"Recorded: {record.file_hash[:8]}, Current: {current_hash[:8]}",
            })
            if not hash_match:
                result["valid"] = False
        else:
            result["checks"].append({
                "check": "file_exists",
                "valid": False,
                "detail": f"File {record.file_path} no longer exists",
            })

        # Verify evidence chain is non-empty
        has_evidence = len(record.evidence_chain) > 0
        result["checks"].append({
            "check": "evidence_chain",
            "valid": has_evidence,
            "detail": f"{len(record.evidence_chain)} evidence nodes",
        })
        if not has_evidence:
            result["valid"] = False

        return result

    def _row_to_record(self, row) -> ProvenanceRecord:
        """Convert a database row to a ProvenanceRecord."""
        evidence_chain = json.loads(row["evidence_chain"]) if row["evidence_chain"] else []
        return ProvenanceRecord(
            record_id=row["record_id"],
            file_path=row["file_path"],
            file_hash=row["file_hash"],
            git_sha=row["git_sha"],
            git_branch=row["git_branch"],
            timestamp=row["timestamp"],
            specialist=row["specialist"],
            specialist_hash=row["specialist_hash"],
            tool=row["tool"],
            evidence_chain=[
                EvidenceNode(**e) for e in evidence_chain
            ],
            decision=row["decision"] or "",
            outcome=row["outcome"] or "",
            verification_level=row["verification_level"] or "standard",
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )


if __name__ == "__main__":
    tracker = ProvenanceTracker()
    record = tracker.start_record(__file__, tool="provenance-test")
    record.evidence_chain.append(EvidenceNode(
        tool="manual", evidence_type="test", passed=True,
        detail="Provenance system self-test"
    ))
    record.decision = "Test provenance record"
    record.outcome = "Created successfully"
    rid = tracker.commit_record(record)
    print(f"Provenance record created: {rid}")

    # Verify integrity
    integrity = tracker.verify_integrity(record)
    print(f"Integrity: {integrity}")


