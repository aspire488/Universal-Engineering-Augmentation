"""Project detection and capability routing for Universal Engineering Augmentation."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = Path(os.environ.get("AUGMENTATION_PROFILES", str(_ROOT / "profiles")))


def detect_project(workdir: str = None) -> Dict[str, Any]:
    """Detect project type and load appropriate profile."""
    workdir = workdir or os.getcwd()
    root = _find_git_root(workdir) or workdir
    
    profile = {"type": "generic", "name": Path(root).name, "root": root, "capabilities": {}}
    
    # Check for telegram bot projects
    if _is_telegram_bot(root):
        profile["type"] = "telegram-bot"
        profile["name"] = "telegram-bot"
        profile["capabilities"] = _load_profile("telegram-bot")
    # Check for AURA (future)
    elif _is_aura(root):
        profile["type"] = "aura"
        profile["name"] = "aura"
        profile["capabilities"] = _load_profile("aura")
    else:
        profile["capabilities"] = _load_profile("generic")
    
    return profile


def _find_git_root(path: str) -> Optional[str]:
    current = Path(path)
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return str(parent)
    return None


def _is_telegram_bot(root: str) -> bool:
    indicators = [
        Path(root, "bot.py").exists(),
        Path(root, "runtime").is_dir(),
        Path(root, "runtime", "events.py").exists(),
        Path(root, "handlers").is_dir(),
    ]
    return sum(indicators) >= 2


def _is_aura(root: str) -> bool:
    return Path(root, "aura").is_dir() and Path(root, "aura", "README.md").exists()


def _load_profile(profile_name: str) -> Dict[str, Any]:
    profile_path = PROFILES_DIR / f"{profile_name}.json"
    if profile_path.exists():
        with open(profile_path) as f:
            return json.load(f)
    return _default_profile(profile_name)


def _default_profile(profile_name: str) -> Dict[str, Any]:
    profiles = {
        "generic": {
            "verification_level": "standard",
            "skills": ["impact-analysis", "verify-change", "code-quality"],
            "engines": ["git-worktree"],
            "max_candidates": 0,
        },
        "telegram-bot": {
            "verification_level": "strict",
            "skills": [
                "impact-analysis", "verify-change", "code-quality",
                "architecture", "event-flow", "regression"
            ],
            "engines": ["git-worktree", "candidate-engine"],
            "max_candidates": 3,
            "architectural_domains": [
                "runtime", "cognition", "continuity", "proactivity",
                "stewardship", "skills", "agent-harness", "media"
            ],
            "strict_verification": True,
            "event_driven": True,
        },
        "aura": {
            "verification_level": "standard",
            "skills": ["impact-analysis", "verify-change"],
            "engines": ["git-worktree"],
            "max_candidates": 2,
        }
    }
    return profiles.get(profile_name, profiles["generic"])


if __name__ == "__main__":
    import sys
    workdir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    profile = detect_project(workdir)
    print(json.dumps(profile, indent=2))
