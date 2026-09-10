# Agent integration guide

The recommended integration stack is:

```text
host agent
   │
   ├── structural question ──► UEA deterministic analysis
   ├── verification request ─► uea-verify
   └── novel/ambiguous work ─► host-agent reasoning
```

## Claude Code

Use the hook-oriented adapter in `adapters/claude_code/` or invoke `uea-verify` directly.

## Codex

Use repository instructions to prefer UEA evidence for structural and verification questions. The adapter in `adapters/codex/` documents the policy.

## Other agents

Any agent capable of executing a repository command can use:

```bash
uea-verify . --level standard
```

This keeps the capability layer reusable across tools instead of creating separate implementations of the same engineering checks.
