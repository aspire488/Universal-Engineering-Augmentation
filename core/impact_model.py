"""Impact Model - Deterministic analysis of code change impact."""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict


def find_imports(file_path: Path) -> Set[str]:
    """Extract import targets from a Python file."""
    imports = set()
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            # from X import Y
            m = re.match(r"from\s+([\w.]+)\s+import", line)
            if m:
                imports.add(m.group(1))
            # import X
            m = re.match(r"import\s+([\w.]+)", line)
            if m:
                imports.add(m.group(1))
    except Exception:
        pass
    return imports


def find_function_calls(file_path: Path) -> Set[str]:
    """Extract function/method calls from a Python file."""
    calls = set()
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"(\w+)\s*\(", content):
            calls.add(m.group(1))
    except Exception:
        pass
    return calls


def find_emitters(file_path: Path) -> List[str]:
    """Find emit_runtime_trace() calls in a file."""
    emitters = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(content.splitlines(), 1):
            if "emit_runtime_trace(" in line:
                # Extract event name
                m = re.search(r'emit_runtime_trace\(\s*["\'](\w+)', line)
                if m:
                    emitters.append(f"{file_path.name}:{i}:{m.group(1)}")
    except Exception:
        pass
    return emitters


def find_test_files(module_path: Path, root: Path) -> List[Path]:
    """Find test files that might test a given module."""
    tests = []
    test_dir = root / "tests"
    if not test_dir.exists():
        return tests
    
    module_name = module_path.stem
    module_rel = module_path.relative_to(root) if module_path.is_relative_to(root) else module_path
    
    for test_file in test_dir.rglob("*.py"):
        try:
            content = test_file.read_text(encoding="utf-8", errors="ignore")
            if module_name in content or str(module_rel).replace("\\", "/") in content:
                tests.append(test_file)
        except Exception:
            pass
    return tests


def build_import_graph(root: Path) -> Dict[str, Set[str]]:
    """Build a complete import graph for a project root."""
    graph = defaultdict(set)
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            rel = py_file.relative_to(root)
            module_key = str(rel).replace("\\", "/").replace("/", ".").replace(".py", "")
            if module_key.endswith(".__init__"):
                module_key = module_key[:-9]
            imports = find_imports(py_file)
            for imp in imports:
                graph[module_key].add(imp)
        except Exception:
            pass
    return dict(graph)


def build_reverse_import_graph(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Build reverse import graph (who imports me)."""
    reverse = defaultdict(set)
    for module, deps in graph.items():
        for dep in deps:
            reverse[dep].add(module)
    return dict(reverse)


def analyze_symbol_impact(symbol_name: str, reverse_graph: Dict[str, Set[str]]) -> Dict:
    """Analyze impact of changing a symbol."""
    direct_callers = reverse_graph.get(symbol_name, set())
    transitive = set()
    for caller in direct_callers:
        transitive.update(reverse_graph.get(caller, set()))
    
    risk = "LOW"
    if len(direct_callers) >= 10:
        risk = "HIGH"
    elif len(direct_callers) >= 4:
        risk = "MEDIUM"
    
    return {
        "symbol": symbol_name,
        "direct_callers": list(direct_callers),
        "transitive_dependents": list(transitive - direct_callers),
        "risk_level": risk,
    }


def analyze_file_impact(file_path: Path, root: Path) -> Dict:
    """Analyze impact of changing a file."""
    rel = file_path.relative_to(root) if file_path.is_relative_to(root) else file_path
    module_key = str(rel).replace("\\", "/").replace("/", ".").replace(".py", "")
    if module_key.endswith(".__init__"):
        module_key = module_key[:-9]
    
    imports = find_imports(file_path)
    calls = find_function_calls(file_path)
    emitters = find_emitters(file_path)
    tests = find_test_files(file_path, root)
    
    return {
        "file": str(rel),
        "module": module_key,
        "imports": list(imports),
        "calls": list(calls)[:50],
        "emitters": emitters,
        "test_files": [str(t.relative_to(root)) for t in tests],
        "test_count": len(tests),
    }


def generate_impact_report(root: Path, target_file: str = None, target_symbol: str = None) -> Dict:
    """Generate a full impact report for a project root."""
    graph = build_import_graph(root)
    reverse_graph = build_reverse_import_graph(graph)
    
    report = {
        "total_modules": len(graph),
        "total_dependencies": sum(len(v) for v in graph.values()),
    }
    
    if target_file:
        target = Path(target_file)
        if not target.is_absolute():
            target = root / target
        report["file_impact"] = analyze_file_impact(target, root)
    
    if target_symbol:
        report["symbol_impact"] = analyze_symbol_impact(target_symbol, reverse_graph)
    
    hub_modules = sorted(reverse_graph.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    report["hub_modules"] = [{"module": m, "dependents": len(d)} for m, d in hub_modules]
    
    leaf_modules = [m for m in graph if m not in reverse_graph or len(reverse_graph[m]) == 0]
    report["leaf_count"] = len(leaf_modules)
    
    return report


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if len(sys.argv) > 2:
        target = sys.argv[2]
        if os.path.isfile(target):
            result = generate_impact_report(root, target_file=target)
        else:
            result = generate_impact_report(root, target_symbol=target)
    else:
        result = generate_impact_report(root)
    
    print(json.dumps(result, indent=2, default=str))
