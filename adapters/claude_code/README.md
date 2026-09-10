# Claude Code adapter

This adapter keeps Claude Code as the host agent while routing repeatable engineering work through UEA's deterministic core.

## Hook pattern

From a Claude Code hook, invoke the UEA verification entry point from the repository root:

```bash
python -m adapters.claude_code.verify --level standard
```

The command emits JSON so the hook can place deterministic evidence into the agent context.

## Design boundary

Claude Code owns:

- user intent
- strategy
- novel implementation reasoning
- communication

UEA owns:

- structural facts
- deterministic verification
- test-quality checks
- formal/specialized evidence when triggered

The adapter contains no Claude SDK dependency and can therefore be used from local hooks, wrappers, or MCP tooling.
