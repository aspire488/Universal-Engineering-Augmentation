# Systematic Debugging

**Domain:** debugging | **Verification:** strict | **Evidence Required:** yes

## Purpose

Never guess. Always verify root cause before fixing. This skill enforces a
rigorous debugging methodology that produces evidence at every step.

## Workflow

### 1. Reproduce
- Run the failing test/command
- Capture exact error output
- Document reproduction steps
- **Evidence:** `test_output.txt` or console capture

### 2. Isolate
- Narrow scope: which file, which function, which line?
- Use tree-sitter to map the call graph
- Use grep to find all callers
- **Evidence:** call graph analysis, caller list

### 3. Hypothesize
- Generate 2-3 hypotheses for root cause
- Rank by likelihood
- Design a test for the top hypothesis
- **Evidence:** hypothesis list with rationale

### 4. Test Hypothesis
- Add targeted print/logging
- Write a minimal reproduction test
- Use Z3/SAT to verify logic constraints
- **Evidence:** test output, SAT model

### 5. Fix
- Make the minimal change that fixes root cause
- NOT the symptom — the root cause
- One guard in shared function > guard in every caller
- **Evidence:** git diff showing minimal change

### 6. Verify
- Run the full test suite
- Run mutation testing to confirm test quality
- Run security scan if applicable
- **Evidence:** verification results

### 7. Document
- Record provenance: what was found, what was fixed, what evidence exists
- Log to event database
- **Evidence:** provenance record

## Rules

- NEVER fix a symptom without understanding root cause
- NEVER apply a fix without reproducing the bug first
- NEVER skip the hypothesis step — "try things" is not debugging
- ALWAYS verify the fix doesn't break other things
- ALWAYS log the evidence chain

## Deterministic Tools

| Tool | When to Use |
|------|-------------|
| tree-sitter | Map call graph, find all callers |
| grep | Find all references to broken code |
| Z3/SAT | Verify logic constraints |
| pytest | Reproduce and verify fixes |
| mutation testing | Confirm test quality |

## When NOT to Use

- Trivial typos (just fix them)
- Formatting-only changes
- When the bug is already fully understood and the fix is obvious
- Documentation-only changes
