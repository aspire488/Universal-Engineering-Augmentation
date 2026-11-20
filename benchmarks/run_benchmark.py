"""Run a small, reproducible benchmark over deterministic capabilities.

The harness measures work performed by the augmentation layer itself. It deliberately
does not invent LLM call/token/cost measurements when the host agent does not expose them.
"""
from __future__ import annotations

import json
import platform
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def timed(name, fn):
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"name": name, "elapsed_ms": round(elapsed_ms, 3), "result": result}


def benchmark_tree_sitter():
    from core.tree_sitter_engine import parse_file

    target = ROOT / "scripts" / "sample_target.py"
    parsed = parse_file(str(target))
    return {"functions": len(parsed.get("functions", [])), "imports": len(parsed.get("imports", []))}


def benchmark_go_rust():
    """Benchmark structural extraction for the newly supported Go and Rust grammars."""
    from core.tree_sitter_engine import parse_file

    fixtures = {
        "sample.go": '''package main

import "fmt"

type Counter struct { value int }

func (c *Counter) Increment() {
    c.value++
    fmt.Println(c.value)
}
''',
        "sample.rs": '''use std::fmt;

struct Counter { value: i32 }

enum Mode { Fast, Slow }

trait Incrementable {
    fn increment(&mut self);
}

fn add(a: i32, b: i32) -> i32 {
    a + b
}
''',
    }
    results = {}
    with tempfile.TemporaryDirectory(prefix="uea-benchmark-") as tmpdir:
        for filename, source in fixtures.items():
            target = Path(tmpdir) / filename
            target.write_text(source, encoding="utf-8")
            parsed = parse_file(str(target))
            if "error" in parsed:
                raise RuntimeError(
                    f"Could not parse benchmark fixture {filename}: {parsed['error']}"
                )
            results[Path(filename).suffix.lstrip(".")] = {
                "functions": len(parsed.get("functions", [])),
                "types": len(parsed.get("classes", [])),
                "imports": len(parsed.get("imports", [])),
                "nodes": parsed.get("node_count", 0),
            }
    return results


def benchmark_z3():
    from core.sat_engine import verify_preconditions

    result = verify_preconditions(
        pre=["x > 0", "y > 0"],
        post=["x + y > 0"],
        variables={"x": "int", "y": "int"},
    )
    return {"valid": bool(result["valid"])}


def benchmark_property_testing():
    from hypothesis import given, strategies as st, settings
    from core.property_testing import run_property_test

    @given(a=st.integers(), b=st.integers())
    @settings(max_examples=50, deadline=None)
    def commutative_addition(a, b):
        assert a + b == b + a

    result = run_property_test(commutative_addition, max_examples=50)
    return {"passed": bool(result.passed), "max_examples": 50}


def benchmark_verification():
    from core.verification import run_verification

    result = run_verification(str(ROOT), "minimal")
    return {"passed": result.passed, "failed": result.failed}


def main():
    benchmarks = [
        ("tree_sitter_python", benchmark_tree_sitter),
        ("tree_sitter_go_rust", benchmark_go_rust),
        ("z3_pre_post", benchmark_z3),
        ("hypothesis", benchmark_property_testing),
        ("verification", benchmark_verification),
    ]

    measurements = []
    for name, fn in benchmarks:
        measurements.append(timed(name, fn))

    output = {
        "schema_version": 1,
        "benchmark": "uea-deterministic-core",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "measurements": measurements,
        "llm_telemetry": {
            "available": False,
            "reason": "The benchmark runner has no host-agent token/call telemetry source.",
        },
    }

    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
