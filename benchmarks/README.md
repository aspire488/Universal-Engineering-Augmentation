# Reproducible benchmarks

`run_benchmark.py` measures a small fixed corpus of deterministic UEA capabilities:

- Tree-sitter structural parsing for Python, Go, and Rust
- Z3 pre/post-condition verification
- Hypothesis property testing
- the existing minimal verification pipeline

Each run emits machine-readable JSON with elapsed milliseconds and capability results. The Go/Rust measurement parses temporary fixtures and reports extracted functions, types, imports, and syntax-tree node counts for each language; fixtures are recreated on every run and do not modify the repository.

## Run

```bash
python benchmarks/run_benchmark.py
```

The output is intentionally environment-specific: latency is measured on the machine that runs the benchmark and should not be presented as a universal performance claim.

### LLM telemetry

The benchmark reports LLM telemetry as unavailable unless the host coding agent explicitly provides a token/call measurement interface. It never estimates or fabricates token savings.

For comparable experiments, keep the benchmark corpus and capability configuration fixed and compare multiple runs rather than relying on a single latency sample.
