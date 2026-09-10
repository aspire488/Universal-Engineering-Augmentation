# Universal Specialist Integration Report

**Date:** 2026-09-08
**Status:** Implemented and tested (6/6 integration tests passing)

## Summary

Implemented a universal, agent-neutral specialist system that extends the
deterministic engineering augmentation layer with specialist reasoning capabilities.
The specialist layer **increases reasoning capability** — it does not replace
deterministic tools.

## Architecture

```
PUBLIC UNIVERSAL CORE
├── deterministic engines (tree-sitter, Z3, semgrep, mutation, property)
├── specialist registry       ← NEW: runtime-neutral metadata store
├── specialist definitions    ← NEW: 10 normalized specialists
├── router                    ← NEW: deterministic-first task routing
├── provenance                ← NEW: Feynman evidence lineage
├── scoring                   ← NEW: metrics-first quality scoring
├── scale_decision            ← NEW: task complexity classification
├── research workflow         ← NEW: clean-room discovery pattern
├── verification              ← existing: tiered verification
├── generic skills            ← existing + 3 new skills
├── tests                     ← existing + new integration tests
└── adapters/                 ← harness-specific formatting (future)

PRIVATE
└── KIO-specific everything (profiles, configs, domain data)
```

## What Was Built

### 1. Specialist Registry (`core/specialist_registry.py`)

Runtime-neutral metadata store for specialist definitions. No harness-specific
formatting. Specialists are normalized from external sources into a universal schema.

**Features:**
- Register/lookup/disable specialists
- Find by domain, capability, or tag
- Deduplication (same name, different domains)
- SHA-256 hashing for provenance
- On-demand loading (never permanently loaded)

**Built-in specialists (10):**
| Name | Domain | Source |
|------|--------|--------|
| systematic-debugging | debugging | 100x-agent-toolkit (adapted) |
| verification-before-completion | code_quality | Feynman principles |
| research-workflow | research | Feynman workflow pattern |
| security-audit | security | wshobson/agents (normalized) |
| architecture-review | architecture | wshobson/agents (normalized) |
| performance-analysis | performance | 100x-agent-toolkit (adapted) |
| test-generation | testing | Built-in |
| code-review | code_quality | wshobson/agents (normalized) |
| deployment-analysis | deployment | Feynman scale decision |
| documentation-generation | documentation | 100x-agent-toolkit (adapted) |

### 2. Specialist Router (`core/specialist_router.py`)

Deterministic-first task routing. Specialists only augment when deterministic
capability is insufficient.

**Flow:**
```
task → classification → deterministic evidence → specialist (if needed) → verification
```

**Key decisions:**
- Trivial/SMALL tasks: no specialist needed
- MODERATE tasks: specialist if domain match exists
- COMPLEX/CRITICAL tasks: specialist + candidate worktrees
- Security tasks: always "full" verification tier
- No multi-agent fan-out: one specialist at a time

### 3. Feynman Provenance (`core/provenance.py`)

Evidence lineage tracking. Every engineering action gets a complete provenance
record with file hash, git SHA, tool evidence chain, specialist involvement,
and decision rationale.

**Schema:** `provenance` table added to `data/sqlite/schema.sql`

**Key fields:**
- `file_hash`: SHA-256 of file content before action
- `git_sha` / `git_branch`: repository state at time of action
- `evidence_chain`: ordered list of tool outputs
- `specialist` / `specialist_hash`: which specialist was involved
- `decision` / `outcome`: what was decided and what happened
- `verification_level`: which verification tier was used

### 4. Deterministic Scoring (`core/scoring.py`)

Metrics-first quality scoring. Never let the LLM invent measurements.

**Dimensions:**
- correctness, maintainability, security, performance
- test_coverage, structural_integrity, complexity, documentation

**Algorithm:**
1. Collect metric evidence from deterministic tools
2. Calculate per-dimension scores (weighted average)
3. Calculate overall score (weighted average of dimensions)
4. Calculate confidence (based on evidence density)
5. Identify warnings and recommendations

**Scoring from:** verification results, test results, complexity analysis

### 5. Scale Decision (`core/scale_decision.py`)

Task complexity classification with recommendations.

| Scale | Files | Lines | Approach | Verification | Candidates |
|-------|-------|-------|----------|--------------|------------|
| small | 1-2 | <50 | direct | standard | 0 |
| medium | 3-5 | 50-200 | specialist | standard | 2 |
| large | 5-15 | 200-500 | candidates | strict | 3 |
| complex | >15 | >500 | parallel | strict | 4 |
| critical | any | any | parallel+verify | full/security | 5 |

**Risk detection:** security, data-layer, production, backward-compatibility

### 6. New Skills

| Skill | Domain | Purpose |
|-------|--------|---------|
| systematic-debugging | debugging | Reproduce → hypothesize → test → fix |
| verification-before-completion | code_quality | No silent failures, verify before done |
| research-workflow | research | Clean-room discovery before solutions |

### 7. Integration Tests (`tests/test_specialist_system.py`)

6 test suites, all passing:
1. Specialist Registry: register, lookup, deduplicate, disable
2. Specialist Router: classify, route, verify complexity levels
3. Deterministic Scoring: metrics → score → confidence
4. Scale Decision: small→direct, large→candidates, security→critical
5. Provenance Tracking: record → retrieve → verify integrity
6. Full Chain Integration: task → router → evidence → specialist → verification → provenance

## The Specialist Pipeline

```
specialist
    ↓
required deterministic evidence
    ↓
specialist reasoning
    ↓
required verification
```

This preserves the architecture: specialists **consume** evidence from
deterministic tools (tree-sitter, Z3, semgrep, mutation testing, etc.),
they do not replace them.

## External Sources Investigated

| Source | Verdict | Extracted |
|--------|---------|-----------|
| 100 Agentic AI Skills | REJECTED | 0 (identical boilerplate) |
| 100x Agent Toolkit | Selective | 8 skills adapted |
| Feynman (Goldin labs) | Selective | Provenance, scoring, scale, research patterns |
| PaperRank | DO NOT INTEGRATE | Domain-specific |
| wshobson/agents | Normalized | 4 specialists adapted |
| herbert-julio-azion/specialist-agent | Referenced | Multi-harness pattern |

## What Was NOT Done

- No KIO-specific data added (PRIVATE boundary preserved)
- No harness-specific formatting (stays at adapter layer)
- No vendor dependencies introduced
- No permanent specialist loading (on-demand only)
- No multi-agent fan-out (one specialist at a time)

## Files Created/Modified

**New files:**
- `core/specialist_registry.py` — specialist metadata store
- `core/specialist_router.py` — deterministic-first routing
- `core/provenance.py` — Feynman evidence lineage
- `core/scoring.py` — metrics-first quality scoring
- `core/scale_decision.py` — task complexity classification
- `skills/systematic-debugging/SKILL.md`
- `skills/verification-before-completion/SKILL.md`
- `skills/research-workflow/SKILL.md`
- `tests/test_specialist_system.py` — integration tests
- `data/specialists/` — specialist registry data directory

**Modified files:**
- `data/sqlite/schema.sql` — added `provenance` table

## Next Steps (Future)

1. **Adapters/** — harness-specific formatting for Claude, Cursor, OpenCode, Codex
2. **More specialists** — extract additional useful specialists from wshobson/agents
3. **Provenance visualization** — timeline view of evidence chains
4. **Cross-repo provenance** — track decisions across repositories
5. **Performance profiling integration** — connect to actual profiler output
6. **Security scanner integration** — real semgrep/taint analysis results
