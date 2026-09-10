# Codex adapter

This adapter integrates UEA with Codex through repository-local instructions while keeping the engineering engine independent of Codex.

## Repository instruction

Add the following policy to a repository's `AGENTS.md` when UEA is installed:

```text
## Universal Engineering Augmentation

Before making a non-trivial change, use UEA deterministic evidence when available.

Prefer:
- structural analysis for symbol/import questions
- impact analysis before cross-file changes
- minimal verification after small edits
- standard verification before completion
- strict/security verification for high-risk changes

Do not ask the model to re-derive structural facts that UEA can answer deterministically.
Do not claim LLM/token savings unless host instrumentation measures them.
```

## Direct verification

```bash
python -m core.verification . standard
```

The adapter is deliberately file/CLI based rather than tied to a Codex SDK. This keeps the same capability usable from Codex, CI, local scripts, or another coding agent.
