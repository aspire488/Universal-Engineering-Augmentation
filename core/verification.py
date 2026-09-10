"""Tiered verification engine for Universal Engineering Augmentation."""

import subprocess
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
WORKDIR = Path(os.environ.get("AUGMENTATION_WORKDIR", str(_ROOT)))


class VerificationResult:
    def __init__(self, level: str):
        self.level = level
        self.checks: List[Dict] = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.duration_ms = 0

    def add(self, name: str, passed: bool, detail: str = "", skipped: bool = False):
        self.checks.append({"name": name, "passed": passed, "detail": detail, "skipped": skipped})
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1

    def to_dict(self):
        return {
            "level": self.level,
            "checks": self.checks,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "success": self.failed == 0,
        }


def run_command(cmd: str, cwd: str = None, timeout: int = 120) -> Tuple[bool, str, int]:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return False, "Command timed out", -1
    except Exception as e:
        return False, str(e), -1


def verify_syntax(project_root: str, files: List[str] = None) -> VerificationResult:
    """Level 1: Syntax check."""
    result = VerificationResult("syntax")
    start = time.time()
    
    if files:
        for f in files:
            if f.endswith(".py"):
                ok, out, _ = run_command(f'python -m py_compile "{f}"', cwd=project_root)
                result.add(f"python-syntax:{Path(f).name}", ok, out[:200])
            elif f.endswith((".ts", ".js")):
                ok, out, _ = run_command(f'npx tsc --noEmit "{f}"', cwd=project_root, timeout=60)
                result.add(f"ts-syntax:{Path(f).name}", ok, out[:200])
    else:
        ok, out, _ = run_command("python -m compileall . -q", cwd=project_root, timeout=60)
        result.add("python-syntax-all", ok, out[:500])
    
    result.duration_ms = int((time.time() - start) * 1000)
    return result


def verify_typecheck(project_root: str) -> VerificationResult:
    """Level 2: Type checking."""
    result = VerificationResult("typecheck")
    start = time.time()
    
    if Path(project_root, "pyproject.toml").exists() or Path(project_root, "setup.py").exists():
        ok, out, _ = run_command("python -m mypy . --ignore-missing-imports", cwd=project_root, timeout=120)
        result.add("mypy", ok, out[:500])
    elif Path(project_root, "tsconfig.json").exists():
        ok, out, _ = run_command("npx tsc --noEmit", cwd=project_root, timeout=120)
        result.add("tsc", ok, out[:500])
    else:
        result.add("typecheck", True, "No type checker configured", skipped=True)
    
    result.duration_ms = int((time.time() - start) * 1000)
    return result


def verify_tests(project_root: str, test_files: List[str] = None) -> VerificationResult:
    """Level 3: Test execution."""
    result = VerificationResult("tests")
    start = time.time()
    
    if test_files:
        cmd = f"python -m pytest {' '.join(test_files)} -x -q --tb=short"
    elif Path(project_root, "pytest.ini").exists() or Path(project_root, "pyproject.toml").exists():
        cmd = "python -m pytest -x -q --tb=short"
    elif Path(project_root, "package.json").exists():
        ok, out, _ = run_command("npm test -- --passWithNoTests", cwd=project_root, timeout=300)
        result.add("npm-test", ok, out[:1000])
        result.duration_ms = int((time.time() - start) * 1000)
        return result
    else:
        result.add("tests", True, "No test framework found", skipped=True)
        return result
    
    ok, out, _ = run_command(cmd, cwd=project_root, timeout=300)
    result.add("pytest", ok, out[:1000])
    result.duration_ms = int((time.time() - start) * 1000)
    return result


def verify_integration(project_root: str) -> VerificationResult:
    """Level 4: Integration checks."""
    result = VerificationResult("integration")
    start = time.time()
    
    ok, out, _ = run_command("python -m pytest -x -q --tb=short -m integration", cwd=project_root, timeout=300)
    result.add("integration-tests", ok, out[:1000])
    
    result.duration_ms = int((time.time() - start) * 1000)
    return result


def verify_security(project_root: str) -> VerificationResult:
    """Level 5: Security scan."""
    result = VerificationResult("security")
    start = time.time()
    
    ok, out, _ = run_command("pip show semgrep >nul 2>&1 && semgrep --config=auto --quiet .", cwd=project_root, timeout=180)
    result.add("semgrep", ok, out[:1000])
    
    result.duration_ms = int((time.time() - start) * 1000)
    return result


def verify_structural(project_root: str, profile: Dict = None) -> VerificationResult:
    """Level 6: Structural/architectural checks."""
    result = VerificationResult("structural")
    start = time.time()
    
    if profile and profile.get("event_driven"):
        ok, out, _ = run_command(
            f'python -c "import ast; [ast.parse(open(f).read()) for f in __import__(\'glob\').glob(\'**/*.py\', recursive=True)]"',
            cwd=project_root, timeout=60
        )
        result.add("ast-parse-all", ok, out[:500])
    
    result.duration_ms = int((time.time() - start) * 1000)
    return result


VERIFICATION_LEVELS = {
    "minimal": [verify_syntax],
    "standard": [verify_syntax, verify_typecheck, verify_tests],
    "strict": [verify_syntax, verify_typecheck, verify_tests, verify_integration, verify_structural],
    "security": [verify_syntax, verify_typecheck, verify_tests, verify_security],
    "full": [verify_syntax, verify_typecheck, verify_tests, verify_integration, verify_security, verify_structural],
}


def run_verification(project_root: str, level: str = "standard", files: List[str] = None, profile: Dict = None) -> VerificationResult:
    """Run verification at the specified level."""
    checkers = VERIFICATION_LEVELS.get(level, VERIFICATION_LEVELS["standard"])
    
    combined = VerificationResult(level)
    total_start = time.time()
    
    for checker in checkers:
        if checker == verify_syntax and files:
            vr = checker(project_root, files)
        elif checker == verify_structural:
            vr = checker(project_root, profile)
        else:
            vr = checker(project_root)
        
        for c in vr.checks:
            combined.add(c["name"], c["passed"], c.get("detail", ""), c.get("skipped", False))
        
        if combined.failed > 0 and level != "full":
            break
    
    combined.duration_ms = int((time.time() - total_start) * 1000)
    return combined


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    level = sys.argv[2] if len(sys.argv) > 2 else "standard"
    result = run_verification(root, level)
    print(json.dumps(result.to_dict(), indent=2))
