# Universal Engineering Augmentation

A tool-agnostic engineering augmentation layer for coding agents.

## What it is

A deterministic/specialized capability layer that coding agents can use alongside LLM reasoning. Coding agents should not use an LLM for work that can be performed deterministically.

## Why

LLMs are powerful but expensive and non-deterministic for tasks that have known algorithms. This layer provides:

- **Structural code analysis** — parse any language via tree-sitter, extract functions/classes/imports without LLM guessing
- **Symbol and import analysis** — trace call graphs, find dependencies, map impact
- **Property testing** — generate edge cases via Hypothesis without LLM reasoning
- **Mutation testing** — verify test quality by injecting faults
- **Formal constraints** — SAT/SMT solving for pre/post conditions via Z3
- **Verification** — tiered verification (minimal → full) with deterministic checks
- **Impact analysis** — blast radius computation before any code change
- **Candidate isolation** — git worktree-based experiment branching
- **Event logging** — structured SQLite/DuckDB event recording for observability
- **Analytics** — SQL-queryable metrics on engineering activity

## Architecture

```
Agent (OpenCode / Claude Code / Codex / other)
  │
  ▼
Augmentation Layer
  ├── Code Intelligence (tree-sitter, impact model)
  ├── Verification (tiered checks, regression detection)
  ├── Testing (property, mutation, formal)
  ├── Candidate Engine (propose, evaluate, select)
  ├── Worktree Isolation (git worktree per candidate)
  ├── Event Log (SQLite structured recording)
  └── Analytics (DuckDB SQL queries)
```

The LLM remains responsible for:
- Strategy and architecture decisions
- Ambiguity resolution
- Novel reasoning
- Candidate generation
- Judgment calls

Deterministic systems handle repeatable engineering operations.

## Capabilities

| Module | What it does |
|--------|-------------|
| `tree_sitter_engine` | Parse Python/JS/TS/JSON via tree-sitter, extract functions/classes/imports/symbols |
| `impact_model` | Build import graphs, trace function calls, compute blast radius |
| `symbol_impact` | Cross-file symbol impact analysis, hub detection, test coverage mapping |
| `verification` | Tiered verification (minimal/standard/strict/security/full) |
| `property_testing` | Hypothesis-based property testing with configurable strategies |
| `mutation_testing` | Fault injection and test quality measurement |
| `sat_engine` | Z3-based SAT/SMT solving for formal constraints |
| `candidate_engine` | Multi-approach candidate proposal and evaluation |
| `worktree_engine` | Git worktree creation, isolation, diff, and merge |
| `event_log` | Structured SQLite event recording with metadata |
| `analytics` | DuckDB-powered SQL analytics over event data |
| `project_detector` | Detect project type and load appropriate capability profile |

## Current Integrations

The architecture is agent-neutral. OpenCode is the first/reference integration.

**Agent adapters** (planned):
- OpenCode (reference implementation)
- Claude Code
- Codex
- Other agents via simple adapter interface

**MCP servers** (compatible):
- Any MCP-compatible server can be used alongside the augmentation layer

## Installation

```bash
# Clone
git clone <repo-url> Universal-Engineering-Augmentation
cd Universal-Engineering-Augmentation

# Install Python dependencies
pip install tree-sitter tree-sitter-python hypothesis z3-solver duckdb mutmut

# Verify
python scripts/verify_all.py
```

**Requirements:**
- Python 3.10+
- Git
- Node.js (for MCP servers, optional)

**Optional:**
- `semgrep` — for static analysis verification tier
- `mutmut` — for mutation testing (requires WSL on Windows)

## Examples

See `examples/live/` for demonstration artifacts:

| File | What it shows |
|------|---------------|
| `tree_sitter_output.json` | AST analysis of Python files — functions, classes, imports extracted |
| `impact_analysis.json` | Import graph and file-level impact analysis |
| `event_log_sample.json` | Structured event recording to SQLite |
| `verification_result.json` | Tiered verification output |
| `tool_timing.json` | Performance measurements |

Each artifact includes WHAT was measured, HOW, and the ACTUAL RESULT.

## Verification

Run the complete verification suite:

```bash
python scripts/verify_all.py
```

This runs 16 checks across all augmentation modules:
- Database connectivity
- Event logging
- Task logging
- Verification engine
- Project detection
- Skill registration
- Worktree listing
- Candidate logging
- Project statistics
- Tree-sitter parsing
- Tree-sitter symbol lookup
- Property testing
- Mutation testing
- Z3 SAT solving
- Z3 pre/post verification
- DuckDB analytics

## Benchmarks

Performance measurements on a real-world Python codebase (30+ subdirectories):

| Operation | Time |
|-----------|------|
| Tree-sitter parse (10 files) | 176ms |
| Impact analysis (1 file) | 24ms |
| Event log (1 event) | 16ms |
| Candidate proposal (2 candidates) | 1.1s |
| Property test | 253ms |
| DuckDB query | 77ms |

**LLM token reduction:** Not measurable. The augmentation layer provides capabilities that LLMs cannot perform deterministically, rather than replacing LLM calls. Token savings are not the value proposition — capability expansion is.

## Security

- No secrets or credentials are stored in the augmentation layer
- Private project configuration is excluded via `.gitignore`
- Generated/runtime artifacts (SQLite databases, worktrees) are ignored
- Event logs store metadata only — no source code or secrets

## Limitations

- **semgrep** — not installed by default; static analysis tier unavailable without it
- **mutmut** — requires WSL on Windows; mutation testing limited on native Windows
- **OpenCode telemetry** — token/call measurement depends on agent implementation; not all agents expose this data
- **Language support** — tree-sitter modules bundled for Python, JavaScript, TypeScript, JSON; other languages require additional tree-sitter grammars

## Roadmap

- Agent adapter interface for Claude Code, Codex integration
- Additional tree-sitter grammars (Rust, Go, Java)
- CI/CD integration for automated verification
- Web dashboard for analytics visualization

## License

[License to be determined]
