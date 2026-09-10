"""Candidate engine - propose, isolate, evaluate, select."""

import uuid
import json
from pathlib import Path
from typing import Dict, List, Optional
from .worktree_engine import create_worktree, remove_worktree, commit_in_worktree, run_in_worktree
from .verification import run_verification
from .event_log import log_candidate, update_candidate, get_db


def propose_candidates(problem: str, approaches: List[str], repo_path: str, base_branch: str = "main") -> List[Dict]:
    """Create candidate worktrees for each approach."""
    candidates = []
    for i, approach in enumerate(approaches):
        cid = f"cand-{uuid.uuid4().hex[:8]}"
        wt = create_worktree(repo_path, cid, base_branch)
        
        log_candidate(cid, Path(repo_path).name, problem, approach, wt.get("path"))
        
        candidates.append({
            "id": cid,
            "approach": approach,
            "worktree": wt,
        })
    return candidates


def evaluate_candidate(candidate_id: str, repo_path: str, verification_level: str = "standard", profile: Dict = None) -> Dict:
    """Run verification on a candidate worktree."""
    with get_db() as conn:
        row = conn.execute("SELECT worktree_path FROM candidates WHERE id=?", (candidate_id,)).fetchone()
    
    if not row or not row["worktree_path"]:
        return {"success": False, "error": "Candidate worktree not found"}
    
    wt_path = row["worktree_path"]
    result = run_verification(wt_path, verification_level, profile=profile)
    result_dict = result.to_dict()
    
    update_candidate(candidate_id,
                     status="evaluated",
                     verification_result=json.dumps(result_dict),
                     test_result="pass" if result_dict["success"] else "fail")
    
    return result_dict


def select_winner(candidates: List[Dict]) -> Optional[Dict]:
    """Select the best candidate based on verification results."""
    scored = []
    for c in candidates:
        if c.get("verification_result"):
            vr = json.loads(c["verification_result"]) if isinstance(c["verification_result"], str) else c["verification_result"]
            score = vr.get("passed", 0) - vr.get("failed", 0) * 2
            scored.append((score, c))
    
    if not scored:
        return None
    
    scored.sort(key=lambda x: x[0], reverse=True)
    winner = scored[0][1]
    
    update_candidate(winner["id"], selected=1, status="winner")
    
    for _, c in scored[1:]:
        update_candidate(c["id"], status="rejected")
    
    return winner


def apply_winner(winner: Dict, target_repo: str) -> bool:
    """Apply the winning candidate to the target repository."""
    wt_path = winner.get("worktree")
    if not wt_path:
        return False
    
    ok, out, _ = run_in_worktree(wt_path, f"git diff HEAD > /tmp/candidate.patch")
    if not ok:
        return False
    
    from .worktree_engine import _run
    ok, out, _ = _run(f'git apply /tmp/candidate.patch', cwd=target_repo)
    return ok


def cleanup_candidates(candidates: List[Dict], repo_path: str):
    """Remove all candidate worktrees."""
    for c in candidates:
        if c.get("worktree") and c["id"] not in [c.get("id") for c in candidates if c.get("status") == "winner"]:
            remove_worktree(repo_path, c["id"])


if __name__ == "__main__":
    print("Candidate engine ready")
