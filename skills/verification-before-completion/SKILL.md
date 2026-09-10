# Verification Before Completion

**Domain:** code_quality | **Verification:** full | **Evidence Required:** yes

## Purpose

No silent failures. Every code change must pass verification before being
declared complete. This skill enforces a verification checklist that prevents
"it works on my machine" syndrome.

## Workflow

### 1. Pre-Change Verification
Before making any changes:
- Run existing tests to establish baseline
- Document current state
- **Evidence:** baseline test results

### 2. During-Change Verification
After each significant edit:
- Syntax check (py_compile / tsc)
- Type check (mypy / tsc --noEmit)
- Targeted test run
- **Evidence:** incremental verification results

### 3. Post-Change Verification
After all changes are complete:
- Full test suite
- Type checking
- Security scan (if applicable)
- Complexity check
- **Evidence:** full verification results

### 4. Impact Verification
Before committing:
- Run impact analysis on all changed files
- Check for regressions
- Verify no unintended side effects
- **Evidence:** impact analysis results

### 5. Final Verification
Before declaring "done":
- All verification tiers pass
- No new warnings introduced
- Documentation updated (if applicable)
- Provenance recorded
- **Evidence:** complete verification chain

## Verification Tiers

| Tier | Checks | When to Use |
|------|--------|-------------|
| minimal | syntax only | Trivial edits |
| standard | syntax + typecheck + tests | Most changes |
| strict | standard + integration + structural | Shared code |
| security | standard + semgrep | Auth/crypto/network |
| full | all checks | Architecture changes |

## Rules

- NEVER declare "done" without running verification
- NEVER skip verification because "it's a small change"
- NEVER assume tests pass without running them
- ALWAYS establish a baseline before making changes
- ALWAYS run the appropriate verification tier
- ALWAYS record verification results

## Evidence Chain

Every verification run produces:
1. What was checked (tool + configuration)
2. What passed/failed (detailed results)
3. What was skipped (and why)
4. Duration and timestamp
5. Git state at time of verification

## When to Escalate

- If verification fails at any tier → stop, fix, re-verify
- If security scan finds issues → escalate to security specialist
- If integration tests fail → may need architecture review
- If mutation testing reveals weak tests → improve tests first
