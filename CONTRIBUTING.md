# Contributing to Universal Engineering Augmentation

Thank you for your interest in contributing. This document explains how to get started, what we expect, and how to add capabilities or agent adapters.

## Project Purpose

Universal Engineering Augmentation provides deterministic engineering capabilities that coding agents can use alongside LLM reasoning. The core principle: **coding agents should not use an LLM for work that can be performed deterministically.**

## Architecture

The project has two layers:

1. **Core** (`core/`) — Agent-neutral deterministic capabilities. No core module requires any specific coding agent.
2. **Adapters** — Agent-specific integrations (e.g., OpenCode reference adapter). These bridge the core to specific agents.

**OpenCode is the first/reference adapter.** The core must remain agent-neutral.

## Development Setup

```bash
git clone https://github.com/aspire488/Universal-Engineering-Augmentation.git
cd Universal-Engineering-Augmentation
pip install -r requirements.txt
pip install pytest  # for running tests
```

## Running Tests

```bash
# Full verification suite (16 checks)
python scripts/verify_all.py

# Unit and integration tests
pytest tests/ -v
```

## Running Verification

The verification suite checks all core modules:

```bash
python scripts/verify_all.py
```

This should always pass before submitting a change.

## Adding a Capability

To add a new deterministic capability to the core:

1. Create a new module in `core/` with clear, deterministic behavior
2. Add comprehensive docstrings explaining what the module does
3. Add unit tests in `tests/`
4. Update the verification suite in `scripts/verify_all.py` if applicable
5. Update `docs/RELEASE_MANIFEST.md` with the new file
6. Update `requirements.txt` if new dependencies are needed
7. Ensure the module is agent-neutral — it must not require any specific coding agent

## Adding an Agent Adapter

To add support for a new coding agent:

1. Create an adapter directory (e.g., `adapters/claude-code/`)
2. Implement the adapter interface that bridges the agent to the core augmentation layer
3. Document the adapter in `docs/`
4. Ensure the core remains unmodified — adapters consume the core, not the other way around

## Coding Expectations

- **Deterministic-first:** If a function can be implemented deterministically, it should be. LLM calls are for strategy and ambiguity only.
- **Clear docstrings:** Every public function should explain what it does, its parameters, and return values.
- **Type hints:** Use type hints for function signatures.
- **Error handling:** Handle failures gracefully. Don't silently swallow exceptions.
- **No secrets:** Never commit credentials, API keys, tokens, or private paths.
- **No KIO material:** This is a public, agent-neutral project. Do not add KIO-specific implementation or data.
- **Minimal dependencies:** Only add dependencies that are genuinely needed. Prefer stdlib.

## Security Expectations

- Never commit secrets, credentials, or API keys
- Never include private project paths (e.g., `C:\Users\...`)
- Event logs store metadata only — no source code or secrets
- If you discover a security vulnerability, see [SECURITY.md](SECURITY.md)

## Pull Request Expectations

- PRs should target `main`
- Include a clear description of what changed and why
- Include test results if applicable
- Run `python scripts/verify_all.py` before submitting
- Ensure no private or KIO-specific material is included
- Check: "Does this change preserve the agent-neutral core architecture?"

## Issue Reporting

Use the issue templates for:
- **Bug reports** — Include reproduction steps, environment, and verification results
- **Feature requests** — Explain the problem, proposed solution, and why deterministic infrastructure is appropriate

## Testing Requirements

- New core modules should have unit tests
- The verification suite must pass
- No regressions in existing tests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
