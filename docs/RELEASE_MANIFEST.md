# Release Manifest

**Repository**: Universal-Engineering-Augmentation
**Date**: 2026-09-10
**Status**: READY TO PUSH
**License**: MIT

## Identity

This repository is an **agent-neutral engineering augmentation layer**. It provides deterministic tools, specialist reasoning, and provenance tracking that work with any coding agent (OpenCode, Claude Code, Codex, Cursor, etc.).

OpenCode is described as a **reference adapter/integration**, not the identity of the project.

## Release File Count: 56

### Root (4 files)
| File | Purpose |
|------|---------|
| `.gitignore` | Exclusion rules for private/temporary files |
| `LICENSE` | MIT License |
| `README.md` | Project overview and usage |
| `requirements.txt` | Python runtime dependencies |

### core/ (18 files)
| Module | Purpose |
|--------|---------|
| `__init__.py` | Package init |
| `analytics.py` | DuckDB analytics queries |
| `candidate_engine.py` | Candidate proposal/evaluation |
| `event_log.py` | SQLite event logging |
| `impact_model.py` | File-level impact analysis |
| `mutation_testing.py` | Mutation test generation |
| `project_detector.py` | Project type detection |
| `property_testing.py` | Hypothesis property tests |
| `provenance.py` | Evidence chain tracking |
| `sat_engine.py` | Z3/SMT constraint solving |
| `scale_decision.py` | Task scale classification |
| `scoring.py` | Deterministic multi-dimension scoring |
| `specialist_registry.py` | Specialist lookup and management |
| `specialist_router.py` | Deterministic-first task routing |
| `symbol_impact.py` | Symbol-level impact analysis |
| `tree_sitter_engine.py` | Tree-sitter code parsing |
| `verification.py` | Tiered verification engine |
| `worktree_engine.py` | Git worktree management |

### data/ (12 files)
| Path | Purpose |
|------|---------|
| `specialists/index.json` | Specialist registry index |
| `specialists/*/` | 10 specialist JSON configs |
| `sqlite/schema.sql` | Database schema (7 tables) |

### docs/ (7 files)
| Document | Purpose |
|----------|---------|
| `BENCHMARK_REPORT.md` | Performance benchmarks |
| `FINAL_PRE_PUSH_VALIDATION.md` | 26-phase validation report |
| `FINAL_RELEASE_SCORECARD.md` | Release scorecard |
| `LLM_LOAD_REDUCTION_AUDIT.md` | LLM usage reduction analysis |
| `RELEASE_AUDIT.md` | Release audit checklist |
| `SPECIALIST_AGENTS_FEYNMAN_INVESTIGATION.md` | External specialist investigation |
| `UNIVERSAL_SPECIALIST_INTEGRATION.md` | Integration report |

### examples/ (6 files)
| File | Purpose |
|------|---------|
| `live/README.md` | Examples overview |
| `live/event_log_sample.json` | Event log example |
| `live/impact_analysis.json` | Impact analysis example |
| `live/tool_timing.json` | Tool timing example |
| `live/tree_sitter_output.json` | Tree-sitter output example |
| `live/verification_result.json` | Verification result example |

### scripts/ (5 files)
| Script | Purpose |
|--------|---------|
| `sample_target.py` | Sample code for testing |
| `test_mutation.py` | Mutation testing demo |
| `test_property.py` | Property testing demo |
| `test_target.py` | Test target code |
| `verify_all.py` | Full verification suite |

### skills/ (3 files)
| Skill | Purpose |
|-------|---------|
| `research-workflow/SKILL.md` | Research workflow patterns |
| `systematic-debugging/SKILL.md` | Debugging methodology |
| `verification-before-completion/SKILL.md` | Verification patterns |

### tests/ (1 file)
| Test | Purpose |
|------|---------|
| `test_specialist_system.py` | Specialist integration tests |

## Dependencies (requirements.txt)
| Package | Version | Purpose |
|---------|---------|---------|
| tree-sitter | 0.26.0 | Code parsing engine |
| tree-sitter-python | 0.25.0 | Python grammar |
| tree-sitter-javascript | 0.25.0 | JavaScript grammar |
| tree-sitter-typescript | 0.23.2 | TypeScript grammar |
| tree-sitter-json | 0.24.8 | JSON grammar |
| hypothesis | 6.167.1 | Property-based testing |
| z3-solver | 5.1.0.0 | SAT/SMT constraint solving |
| duckdb | 1.5.5 | Analytics database |

## Excluded from Release

### KIO (Private)
- `profiles/kio/` — KIO profile data, prompts, credentials
- `scripts/kio_verify.py` — KIO-specific verification
- `scripts/test_treesitter.py` — KIO test scripts
- `scripts/test_treesitter2.py` — KIO test scripts

### Worktrees (Test Fixtures)
- `worktrees/` — 4122 files of KIO candidate worktrees

### Internal Documentation (KIO-contaminated)
- `docs/STATUS.md` — Internal status with KIO references
- `docs/KIO_BENCHMARK_*.md` — KIO-specific benchmarks
- `docs/PROJECT_FREEZE.md` — KIO project freeze notice
- `docs/GLOBAL_*.md` — Internal inventory with personal paths
- `docs/EXTERNAL_*.md` — External validation with KIO references

### Temporary/Generated
- `__pycache__/`, `*.pyc` — Python bytecode
- `.hypothesis/` — Hypothesis test cache
- `data/sqlite/*.db` — Runtime databases
- `tests/_phase*.py` — Validation scripts
- `*.log` — Log files

### Machine-Specific
- `.venv/`, `venv/`, `ENV/` — Virtual environments
- `.vscode/`, `.idea/` — IDE configs
- `.DS_Store`, `Thumbs.db` — OS artifacts

## Verification Summary
| Check | Result |
|-------|--------|
| Regression tests | 15/15 PASS |
| Integration tests | 28/28 PASS |
| Core module imports | 15/15 PASS |
| Dependency validation | 8/8 PASS |
| Secret scan | 0 hits |
| KIO contamination | 0 hits |
| Personal paths | 0 hits |
| Documentation cross-refs | 0 broken |
