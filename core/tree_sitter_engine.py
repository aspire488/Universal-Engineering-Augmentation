"""Tree-sitter structural code intelligence engine."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjs
    import tree_sitter_typescript as tsts
    import tree_sitter_json as tsjson
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

LANG_MAP = {}
if AVAILABLE:
    LANG_MAP = {
        ".py": Language(tspython.language()),
        ".js": Language(tsjs.language()),
        ".jsx": Language(tsjs.language()),
        ".ts": Language(tsts.language_typescript()),
        ".tsx": Language(tsts.language_tsx()),
        ".json": Language(tsjson.language()),
    }


def _parser_for(filepath: str) -> Optional[Parser]:
    ext = Path(filepath).suffix
    lang = LANG_MAP.get(ext)
    if not lang:
        return None
    return Parser(lang)


def _node_info(node, source_bytes: bytes) -> Dict:
    return {
        "type": node.type,
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
        "start_col": node.start_point[1],
        "end_col": node.end_point[1],
        "text": source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace"),
    }


def parse_file(filepath: str) -> Dict:
    """Parse a file and return its structural AST summary."""
    parser = _parser_for(filepath)
    if not parser:
        return {"error": f"Unsupported file type: {Path(filepath).suffix}"}

    source = Path(filepath).read_bytes()
    tree = parser.parse(source)
    root = tree.root_node

    return {
        "file": filepath,
        "language": Path(filepath).suffix,
        "root_type": root.type,
        "node_count": _count_nodes(root),
        "functions": extract_functions(filepath),
        "classes": extract_classes(filepath),
        "imports": extract_imports(filepath),
    }


def _count_nodes(node) -> int:
    count = 1
    for child in node.children:
        count += _count_nodes(child)
    return count


def extract_functions(filepath: str) -> List[Dict]:
    """Extract all function definitions with name, args, and line range."""
    parser = _parser_for(filepath)
    if not parser:
        return []

    source = Path(filepath).read_bytes()
    tree = parser.parse(source)

    functions = []
    _walk_for_type(tree.root_node, source, "function_definition", functions)

    result = []
    for fn in functions:
        name_node = _child_by_type(fn, "identifier")
        params_node = _child_by_type(fn, "parameters")
        result.append({
            "name": name_node.text.decode() if name_node else "<anonymous>",
            "start_line": fn.start_point[0] + 1,
            "end_line": fn.end_point[0] + 1,
            "params": params_node.text.decode() if params_node else "()",
            "decorators": _get_decorators(fn, source),
        })
    return result


def extract_classes(filepath: str) -> List[Dict]:
    """Extract all class definitions with name, bases, and line range."""
    parser = _parser_for(filepath)
    if not parser:
        return []

    source = Path(filepath).read_bytes()
    tree = parser.parse(source)

    classes = []
    _walk_for_type(tree.root_node, source, "class_definition", classes)

    result = []
    for cls in classes:
        name_node = _child_by_type(cls, "identifier")
        result.append({
            "name": name_node.text.decode() if name_node else "<anonymous>",
            "start_line": cls.start_point[0] + 1,
            "end_line": cls.end_point[0] + 1,
            "bases": _get_class_bases(cls, source),
            "methods": _get_methods_in_class(cls, source),
        })
    return result


def extract_imports(filepath: str) -> List[Dict]:
    """Extract all import statements."""
    parser = _parser_for(filepath)
    if not parser:
        return []

    source = Path(filepath).read_bytes()
    tree = parser.parse(source)

    imports = []
    for node in _walk_for_type(tree.root_node, source, "import_statement", []):
        imports.append({
            "text": source[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip(),
            "line": node.start_point[0] + 1,
        })
    for node in _walk_for_type(tree.root_node, source, "import_from_statement", []):
        imports.append({
            "text": source[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip(),
            "line": node.start_point[0] + 1,
        })
    return imports


def find_symbol(filepath: str, name: str) -> Optional[Dict]:
    """Find a specific symbol by name in a file."""
    parser = _parser_for(filepath)
    if not parser:
        return None

    source = Path(filepath).read_bytes()
    tree = parser.parse(source)

    for func in extract_functions(filepath):
        if func["name"] == name:
            func["kind"] = "function"
            return func
    for cls in extract_classes(filepath):
        if cls["name"] == name:
            cls["kind"] = "class"
            return cls
        for method in cls.get("methods", []):
            if method["name"] == name:
                method["kind"] = "method"
                method["class"] = cls["name"]
                return method
    return None


def get_definition_range(filepath: str, name: str) -> Optional[Tuple[int, int]]:
    """Get line range (start, end) for a symbol definition."""
    symbol = find_symbol(filepath, name)
    if symbol:
        return (symbol["start_line"], symbol["end_line"])
    return None


def extract_function_body(filepath: str, name: str) -> Optional[str]:
    """Extract the full source text of a function."""
    parser = _parser_for(filepath)
    if not parser:
        return None

    source = Path(filepath).read_bytes()
    tree = parser.parse(source)

    for fn in _walk_for_type(tree.root_node, source, "function_definition", []):
        name_node = _child_by_type(fn, "identifier")
        if name_node and name_node.text.decode() == name:
            return source[fn.start_byte:fn.end_byte].decode("utf-8", errors="replace")
    return None


def get_import_graph(filepath: str) -> Dict:
    """Extract import relationships from a file for graph analysis."""
    imports = extract_imports(filepath)
    modules = []
    for imp in imports:
        text = imp["text"]
        if text.startswith("from "):
            parts = text.split()
            if len(parts) >= 2:
                modules.append(parts[1].split(".")[0])
        elif text.startswith("import "):
            parts = text.split()
            if len(parts) >= 2:
                modules.append(parts[1].split(".")[0])
    return {
        "file": filepath,
        "imports": imports,
        "top_level_modules": list(set(modules)),
    }


def batch_parse(filepaths: List[str]) -> Dict:
    """Parse multiple files and return aggregate stats."""
    total_functions = 0
    total_classes = 0
    total_imports = 0
    total_nodes = 0
    results = []

    for fp in filepaths:
        parsed = parse_file(fp)
        if "error" not in parsed:
            total_functions += len(parsed["functions"])
            total_classes += len(parsed["classes"])
            total_imports += len(parsed["imports"])
            total_nodes += parsed["node_count"]
            results.append(parsed)

    return {
        "files_parsed": len(results),
        "total_functions": total_functions,
        "total_classes": total_classes,
        "total_imports": total_imports,
        "total_nodes": total_nodes,
        "results": results,
    }


def _walk_for_type(node, source_bytes, target_type, acc):
    if node.type == target_type:
        acc.append(node)
    for child in node.children:
        _walk_for_type(child, source_bytes, target_type, acc)
    return acc


def _child_by_type(node, target_type):
    for child in node.children:
        if child.type == target_type:
            return child
    return None


def _get_decorators(fn_node, source_bytes):
    decos = []
    for child in fn_node.children:
        if child.type == "decorated_definition":
            for sub in child.children:
                if sub.type == "decorator":
                    decos.append(source_bytes[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace").strip())
    return decos


def _get_class_bases(cls_node, source_bytes):
    bases = []
    for child in cls_node.children:
        if child.type == "argument_list":
            for arg in child.children:
                if arg.type == "identifier":
                    bases.append(arg.text.decode())
    return bases


def _get_methods_in_class(cls_node, source_bytes):
    methods = []
    for child in cls_node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "function_definition":
                    name_node = _child_by_type(stmt, "identifier")
                    if name_node:
                        methods.append({
                            "name": name_node.text.decode(),
                            "start_line": stmt.start_point[0] + 1,
                            "end_line": stmt.end_point[0] + 1,
                        })
    return methods


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: tree_sitter_engine.py <file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]
    if Path(target).is_file():
        result = parse_file(target)
        print(json.dumps(result, indent=2))
    elif Path(target).is_dir():
        files = [str(p) for p in Path(target).rglob("*.py")]
        result = batch_parse(files[:50])
        print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=2))
    else:
        print(f"Not found: {target}")
