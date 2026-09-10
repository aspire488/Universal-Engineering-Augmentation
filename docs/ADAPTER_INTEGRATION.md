# Agent adapter integration

UEA is intentionally split into an agent-neutral core and thin host-agent adapters.

| Host | Integration surface | Deterministic entrypoint | Core dependency on host |
|---|---|---|---|
| Claude Code | `adapters/claude_code/` | `python -m adapters.claude_code.verify` | none |
| Codex | `adapters/codex/` + repository `AGENTS.md` policy | `python -m core.verification` | none |

## Integration rule

Adapters translate lifecycle/configuration into UEA calls. They must not import host-agent SDKs into `core/`.

## Verification contract

Every adapter should return or expose structured evidence containing:

- verification level
- individual checks
- pass/fail/skipped counts
- duration
- overall success

This makes the same deterministic evidence usable by different coding agents without changing the engineering engine.

## Why this matters

The project is not an OpenCode plugin with a few extra tools. OpenCode was the reference implementation; the reusable unit is the engineering capability layer itself.
