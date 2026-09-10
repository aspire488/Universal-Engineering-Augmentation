"""Symbol Impact Model - Track impact at class/function level."""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict


def find_references(symbol: str, root: Path) -> List[Dict]:
    """Find all references to a symbol across the codebase."""
    references = []
    
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                # Search for symbol as word boundary
                if re.search(rf'\b{re.escape(symbol)}\b', line):
                    rel = py_file.relative_to(root)
                    references.append({
                        "file": str(rel),
                        "line": i,
                        "content": stripped[:100],
                    })
        except Exception:
            pass
    
    return references


def find_class_definitions(root: Path) -> Dict[str, str]:
    """Find all class definitions and their file locations."""
    classes = {}
    
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                classes[m.group(1)] = str(py_file.relative_to(root))
        except Exception:
            pass
    
    return classes


def find_function_definitions(root: Path) -> Dict[str, str]:
    """Find all function definitions and their file locations."""
    functions = {}
    
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'^def\s+(\w+)', content, re.MULTILINE):
                functions[m.group(1)] = str(py_file.relative_to(root))
        except Exception:
            pass
    
    return functions


def analyze_event_emitters(root: Path) -> Dict[str, List[Dict]]:
    """Analyze all emit_runtime_trace() calls and their event types."""
    emitters = defaultdict(list)
    
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if "emit_runtime_trace(" in line:
                    m = re.search(r'emit_runtime_trace\(\s*["\'](\w+)', line)
                    if m:
                        event_type = m.group(1)
                        emitters[event_type].append({
                            "file": str(py_file.relative_to(root)),
                            "line": i,
                        })
        except Exception:
            pass
    
    return dict(emitters)


def analyze_test_coverage(root: Path) -> Dict[str, List[str]]:
    """Map test files to the modules they test."""
    coverage = defaultdict(list)
    
    test_dir = root / "tests"
    if not test_dir.exists():
        return {}
    
    for test_file in test_dir.rglob("*.py"):
        if "__pycache__" in str(test_file):
            continue
        try:
            content = test_file.read_text(encoding="utf-8", errors="ignore")
            # Find imports from project modules
            for m in re.finditer(r'from\s+([\w]+\.[\w.]+)', content):
                module = m.group(1)
                coverage[module].append(str(test_file.relative_to(root)))
            # Also check for string references to module names
            for module_name in ["pipeline", "runtime", "config", "context_manager", "command_router"]:
                if module_name in content:
                    coverage[module_name].append(str(test_file.relative_to(root)))
        except Exception:
            pass
    
    return dict(coverage)


def generate_comprehensive_report(root: Path) -> Dict:
    """Generate a comprehensive impact and regression report for a project."""
    classes = find_class_definitions(root)
    functions = find_function_definitions(root)
    event_emitters = analyze_event_emitters(root)
    test_coverage = analyze_test_coverage(root)
    
    # Count modules with/without tests
    all_modules = set()
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            rel = py_file.relative_to(root)
            module = str(rel).replace("\\", "/").replace("/", ".").replace(".py", "")
            all_modules.add(module)
        except Exception:
            pass
    
    tested_modules = set(test_coverage.keys())
    untested_modules = all_modules - tested_modules
    
    return {
        "summary": {
            "total_classes": len(classes),
            "total_functions": len(functions),
            "total_event_types": len(event_emitters),
            "total_modules": len(all_modules),
            "tested_modules": len(tested_modules),
            "untested_modules": len(untested_modules),
            "test_coverage_pct": round(len(tested_modules) / max(len(all_modules), 1) * 100, 1),
        },
        "event_emitters": {k: len(v) for k, v in sorted(event_emitters.items(), key=lambda x: -len(x[1]))},
        "hub_classes": sorted(classes.keys())[:20],
        "test_coverage": {k: len(v) for k, v in sorted(test_coverage.items(), key=lambda x: -len(x[1]))[:20]},
    }


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if len(sys.argv) > 2:
        symbol = sys.argv[2]
        refs = find_references(symbol, root)
        print(json.dumps({"symbol": symbol, "references": refs[:30], "total": len(refs)}, indent=2))
    else:
        report = generate_comprehensive_report(root)
        print(json.dumps(report, indent=2))
