"""Git worktree engine for candidate isolation."""

import subprocess
import os
import uuid
from pathlib import Path
from typing import Optional, List

_ROOT = Path(__file__).resolve().parent.parent
WORKTREES_DIR = Path(os.environ.get("AUGMENTATION_WORKTREES", str(_ROOT / "worktrees")))


def create_worktree(repo_path: str, branch_name: str = None, base_branch: str = "main") -> dict:
    """Create an isolated git worktree for a candidate."""
    if not branch_name:
        branch_name = f"candidate-{uuid.uuid4().hex[:8]}"
    
    worktree_path = WORKTREES_DIR / branch_name
    worktree_path.mkdir(parents=True, exist_ok=True)
    
    ok, out, code = _run(f'git worktree add "{worktree_path}" -b {branch_name} {base_branch}', cwd=repo_path)
    
    if ok:
        return {"success": True, "path": str(worktree_path), "branch": branch_name}
    else:
        return {"success": False, "error": out, "branch": branch_name}


def remove_worktree(repo_path: str, branch_name: str):
    """Remove a worktree after candidate evaluation."""
    worktree_path = WORKTREES_DIR / branch_name
    _run(f'git worktree remove "{worktree_path}" --force', cwd=repo_path)
    _run(f'git branch -D {branch_name}', cwd=repo_path)


def list_worktrees(repo_path: str) -> List[dict]:
    """List all active worktrees."""
    ok, out, _ = _run("git worktree list --porcelain", cwd=repo_path)
    if not ok:
        return []
    
    trees = []
    current = {}
    for line in out.strip().split("\n"):
        if line.startswith("worktree "):
            if current:
                trees.append(current)
            current = {"path": line[len("worktree "):]}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):]
    if current:
        trees.append(current)
    return trees


def copy_file_to_worktree(worktree_path: str, file_path: str, content: str):
    """Write a file into a worktree."""
    full_path = Path(worktree_path) / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")


def run_in_worktree(worktree_path: str, cmd: str) -> tuple:
    """Run a command inside a worktree."""
    return _run(cmd, cwd=worktree_path)


def diff_worktree(worktree_path: str, base_branch: str = "main") -> str:
    """Get diff between worktree and base branch."""
    ok, out, _ = _run(f"git diff {base_branch}..HEAD", cwd=worktree_path)
    return out if ok else ""


def commit_in_worktree(worktree_path: str, message: str) -> bool:
    """Stage all and commit in a worktree."""
    _run("git add -A", cwd=worktree_path)
    ok, _, _ = _run(f'git commit -m "{message}"', cwd=worktree_path)
    return ok


def _run(cmd: str, cwd: str = None) -> tuple:
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
        return r.returncode == 0, r.stdout + r.stderr, r.returncode
    except Exception as e:
        return False, str(e), -1


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(list_worktrees(repo))
