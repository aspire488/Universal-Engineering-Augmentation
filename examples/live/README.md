# Live Demo

This directory contains demonstration artifacts from running the augmentation layer against a real Python codebase.

## How to Reproduce

```bash
# Install dependencies
pip install tree-sitter tree-sitter-python hypothesis z3-solver duckdb

# Set augmentation root (optional — defaults to repo root)
export AUGMENTATION_ROOT=$(pwd)

# Run verification
python scripts/verify_all.py

# Run against your own codebase
python -c "
import sys; sys.path.insert(0, '.')
from core.tree_sitter_engine import parse_file
from core.impact_model import analyze_file_impact
from pathlib import Path

# Parse any Python file
r = parse_file('your_file.py')
print(f'Functions: {len(r[\"functions\"])}, Imports: {len(r[\"imports\"])}')

# Analyze impact
impact = analyze_file_impact(Path('your_file.py'), Path('.'))
print(f'Impact: {impact}')
"
```

## Demo Artifacts

| File | What | How | Expected | Actual |
|------|------|-----|----------|--------|
| `tree_sitter_output.json` | AST analysis of 10 Python files | tree_sitter_engine.parse_file() | Functions, classes, imports extracted | 33,101 nodes, 122 imports across 10 files |
| `impact_analysis.json` | Import graph and file impact | impact_model.analyze_file_impact() | Import/call dependencies mapped | 5 files analyzed, 31,523 graph edges |
| `event_log_sample.json` | Event recording to SQLite | event_log.log_event() | Event stored with metadata | 3 events recorded, queryable via DuckDB |
| `verification_result.json` | Tiered verification | verification.run_verification() | Check results | Minimal tier executed |
| `tool_timing.json` | Performance measurements | time.time() around each tool | Latency per operation | Parse: 39ms, Impact: 83ms, Log: 43ms |
