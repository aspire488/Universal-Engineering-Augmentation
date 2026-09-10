# CLI integration

UEA exposes a stable verification command after installation:

```bash
uea-verify . --level minimal
uea-verify . --level standard
uea-verify . --level strict
```

The command writes structured JSON containing the selected level, individual checks, pass/fail/skipped counts, elapsed time, and overall success.

This is the lowest-common-denominator integration surface for coding agents that can execute a repository command. Claude Code and Codex adapters can use it without importing an agent SDK.

## Exit status

- `0` — all executed checks passed
- `1` — at least one executed check failed

The output is evidence, not an LLM-generated opinion.
