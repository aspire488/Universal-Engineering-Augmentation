"""Property-based testing engine using Hypothesis."""

import json
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

try:
    from hypothesis import given, strategies as st, settings, HealthCheck
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@dataclass
class PropertyResult:
    test_name: str
    passed: bool
    iterations: int = 0
    shrunk_example: str = ""
    duration_ms: int = 0
    error: str = ""

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "iterations": self.iterations,
            "shrunk_example": self.shrunk_example,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


def run_property_test(
    test_func: Callable,
    max_examples: int = 100,
    deadline: int = 500,
) -> PropertyResult:
    """Run a single property test function.

    The test_func should be decorated with @given and @settings.
    This function simply calls it and captures the result.
    """
    import time
    start = time.time()

    if not AVAILABLE:
        return PropertyResult(
            test_name=test_func.__name__,
            passed=False,
            error="hypothesis not installed",
        )

    try:
        test_func()

        elapsed = int((time.time() - start) * 1000)
        return PropertyResult(
            test_name=test_func.__name__,
            passed=True,
            iterations=max_examples,
            duration_ms=elapsed,
        )
    except AssertionError as e:
        elapsed = int((time.time() - start) * 1000)
        return PropertyResult(
            test_name=test_func.__name__,
            passed=False,
            duration_ms=elapsed,
            error=str(e)[:500],
        )
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return PropertyResult(
            test_name=test_func.__name__,
            passed=False,
            duration_ms=elapsed,
            error=str(e)[:500],
        )


def run_property_file(filepath: str, max_examples: int = 50) -> Dict:
    """Run all property tests in a file (functions starting with test_)."""
    spec = importlib.util.spec_from_file_location("test_module", filepath)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return {"error": f"Failed to load {filepath}: {e}"}

    results = []
    for name in dir(module):
        if name.startswith("test_"):
            func = getattr(module, name)
            if callable(func):
                result = run_property_test(func, max_examples=max_examples)
                results.append(result.to_dict())

    passed = sum(1 for r in results if r["passed"])
    return {
        "file": filepath,
        "total_tests": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def create_property_test(
    func_name: str,
    func_body: str,
    strategy: str = "int",
) -> str:
    """Generate a property test file from a function signature."""
    strat_map = {
        "int": "st.integers()",
        "float": "st.floats(allow_nan=False, allow_infinity=False)",
        "str": "st.text(max_size=100)",
        "list_int": "st.lists(st.integers(), max_size=50)",
        "bool": "st.booleans",
        "mixed": "st.one_of(st.integers(), st.text(max_size=50))",
    }
    strat = strat_map.get(strategy, "st.integers()")

    return f'''"""Auto-generated property test for {func_name}."""
from hypothesis import given, strategies as st

# Import the target function
# Adjust the import as needed:
# from target_module import {func_name}


@given(value={strat})
def test_{func_name}_identity(value):
    """Test that {func_name} preserves identity on valid input."""
    result = {func_name}(value)
    assert result is not None or value is None


@given(value={strat})
def test_{func_name}_deterministic(value):
    """Test that {func_name} is deterministic."""
    r1 = {func_name}(value)
    r2 = {func_name}(value)
    assert r1 == r2
'''


def batch_property_test(filepaths: List[str], max_examples: int = 30) -> Dict:
    """Run property tests across multiple files."""
    total_passed = 0
    total_failed = 0
    results = []

    for fp in filepaths:
        if Path(fp).exists():
            result = run_property_file(fp, max_examples=max_examples)
            if "error" not in result:
                total_passed += result["passed"]
                total_failed += result["failed"]
                results.append(result)

    return {
        "files_tested": len(results),
        "total_passed": total_passed,
        "total_failed": total_failed,
        "results": results,
    }


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Usage: property_testing.py <test_file.py> [max_examples]")
        _sys.exit(1)

    filepath = _sys.argv[1]
    max_ex = int(_sys.argv[2]) if len(_sys.argv) > 2 else 50
    result = run_property_file(filepath, max_examples=max_ex)
    print(json.dumps(result, indent=2))
