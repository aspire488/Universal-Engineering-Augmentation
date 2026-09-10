# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-10

### Added

- **Tree-sitter structural analysis** — Parse Python, JavaScript, TypeScript, and JSON files; extract functions, classes, imports, and symbols without LLM guessing
- **Impact analysis** — Build import graphs, trace function calls, compute blast radius before code changes
- **Symbol impact** — Cross-file symbol reference tracking, hub detection, test coverage mapping
- **Tiered verification** — Five verification levels (minimal, standard, strict, security, full) with deterministic checks
- **Property testing** — Hypothesis-based property testing with configurable strategies
- **Mutation testing** — Fault injection and test quality measurement via custom engine
- **SAT/SMT engine** — Z3-based formal constraint solving for pre/post conditions
- **Candidate engine** — Multi-approach candidate proposal and evaluation lifecycle
- **Worktree isolation** — Git worktree-based experiment branching and isolation
- **Event logging** — Structured SQLite event recording with metadata
- **Analytics** — DuckDB-powered SQL analytics over engineering event data
- **Project detection** — Automatic project type detection and capability profile loading
- **Specialist registry** — Domain specialist configuration lookup and management
- **Specialist router** — Deterministic-first task routing to appropriate specialists
- **Scoring** — Multi-dimension deterministic scoring engine
- **Provenance** — Audit trail and evidence chain tracking
- **Scale decisions** — Task scale and complexity classification
- **Verification suite** — 16-check validation script covering all core modules
- **Example artifacts** — Pre-generated demonstration outputs in `examples/live/`
- **Agent skills** — Research workflow, systematic debugging, verification-before-completion
- **Canonical Python packaging** — PEP 621 metadata and editable installation path
- **Multi-version CI** — Python 3.10, 3.11, and 3.12 validation
- **Reproducible benchmark harness** — Machine-readable deterministic measurements with explicit telemetry limitations
- **Dependency update automation** — Weekly Dependabot updates for Python and GitHub Actions dependencies
- **Public-development governance** — Contributing guide, security policy, code of conduct, issue/PR templates
- **Tagged release automation** — Version validation, verification, package builds, changelog extraction, and GitHub Releases

### Architecture

- Agent-neutral core — no core module requires any specific coding agent
- OpenCode reference adapter — first integration, not the project identity
- Deterministic-first philosophy — LLMs used for strategy and ambiguity, not repeatable operations
- MCP-compatible — works alongside any MCP server

### Verification

- 51 automated tests passing at the public-alpha maturity baseline
- 16/16 verification suite checks passing
- 15/15 core module imports validated
- 0 secrets detected
- 0 KIO/private data in publishable paths

### Known Limitations

- `semgrep` is not bundled — static-analysis verification tiers require separate installation
- `mutmut` has platform-specific requirements — mutation testing may require a compatible execution environment
- Tree-sitter grammars currently cover Python, JavaScript, TypeScript, and JSON — additional languages are planned
- LLM token/call reduction is not measured — the project does not claim token savings without reproducible host-agent instrumentation
- First-class Claude Code and Codex adapters remain roadmap work

### Release Process

Releases are tag-driven. A `vX.Y.Z` tag must match `core.__version__` and an entry in this changelog. The release workflow runs the normal verification and test gates, builds Python distributions, and publishes a GitHub Release with notes extracted from this file.
