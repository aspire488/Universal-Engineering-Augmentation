# Agent adapters

UEA keeps its engineering capabilities agent-neutral and exposes thin adapters for coding agents.

An adapter is responsible only for translating an agent's lifecycle/configuration into calls to the `core` package. It must not move agent-specific assumptions into `core/`.

## Current adapters

- `claude_code/` — hook-oriented integration for deterministic verification and evidence collection
- `codex/` — repository-instruction integration for deterministic verification and evidence collection

## Contract

Adapters should:

1. receive an agent event or task context;
2. select the cheapest deterministic capability that can answer it;
3. return structured evidence suitable for the agent's context;
4. leave novel reasoning and user-facing judgment to the host agent.

Adapters are optional. Installing UEA never requires a specific coding agent.
