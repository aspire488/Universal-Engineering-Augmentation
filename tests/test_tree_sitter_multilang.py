from pathlib import Path

from core.tree_sitter_engine import (
    extract_classes,
    extract_function_body,
    extract_functions,
    extract_imports,
    get_import_graph,
    parse_file,
)


def test_go_structural_analysis(tmp_path: Path) -> None:
    source = '''package main

import (
    "fmt"
    "strings"
)

type Counter struct {
    value int
}

func Add(a int, b int) int {
    fmt.Println(a)
    return a + b
}

func (c *Counter) Increment() {
    c.value++
}
'''
    filepath = tmp_path / "sample.go"
    filepath.write_text(source, encoding="utf-8")

    parsed = parse_file(str(filepath))
    assert "error" not in parsed
    assert parsed["language"] == ".go"
    assert [item["name"] for item in extract_functions(str(filepath))] == [
        "Add",
        "Increment",
    ]
    assert [item["name"] for item in extract_classes(str(filepath))] == ["Counter"]
    assert len(extract_imports(str(filepath))) == 1
    assert {"fmt", "strings"} <= set(
        get_import_graph(str(filepath))["top_level_modules"]
    )
    assert "return a + b" in (
        extract_function_body(str(filepath), "Add") or ""
    )
    assert "c.value++" in (
        extract_function_body(str(filepath), "Increment") or ""
    )


def test_rust_structural_analysis(tmp_path: Path) -> None:
    source = '''use std::fmt;

struct Counter {
    value: i32,
}

fn add(a: i32, b: i32) -> i32 {
    a + b
}
'''
    filepath = tmp_path / "sample.rs"
    filepath.write_text(source, encoding="utf-8")

    parsed = parse_file(str(filepath))
    assert "error" not in parsed
    assert parsed["language"] == ".rs"
    assert [item["name"] for item in extract_functions(str(filepath))] == ["add"]
    assert [item["name"] for item in extract_classes(str(filepath))] == ["Counter"]
    assert len(extract_imports(str(filepath))) == 1
    assert "std" in get_import_graph(str(filepath))["top_level_modules"]
    assert "a + b" in (extract_function_body(str(filepath), "add") or "")
