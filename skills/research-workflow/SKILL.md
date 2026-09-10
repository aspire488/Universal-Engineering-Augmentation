# Research Workflow

**Domain:** research | **Verification:** standard | **Evidence Required:** yes

## Purpose

Clean-room discovery before generating solutions. Gather evidence, then reason.
This skill enforces a research-first methodology that prevents solving the
wrong problem.

## Workflow

### 1. Understand the Problem
- What is actually being asked?
- What are the constraints?
- What has been tried before?
- **Evidence:** problem statement with constraints

### 2. Gather Evidence
- Search codebase for existing patterns
- Check documentation for known solutions
- Look for similar problems that were solved
- **Evidence:** evidence catalog with sources

### 3. Analyze Options
- List possible approaches
- Evaluate each against constraints
- Identify trade-offs
- **Evidence:** options matrix with scoring

### 4. Recommend
- Select best option based on evidence
- Explain why other options were rejected
- Identify risks and mitigations
- **Evidence:** recommendation with rationale

### 5. Implement (if authorized)
- Follow the recommended approach
- Collect evidence during implementation
- Verify against original requirements
- **Evidence:** implementation + verification results

## Rules

- NEVER generate a solution without understanding the problem first
- NEVER skip evidence gathering — "I think" is not evidence
- ALWAYS consider at least 2-3 alternatives
- ALWAYS document why alternatives were rejected
- ALWAYS verify the solution matches the original requirements

## Deterministic Tools

| Tool | Purpose |
|------|---------|
| tree-sitter | Find existing patterns in codebase |
| grep | Search for similar problems |
| Git log | Find how similar issues were resolved |
| Dependency analysis | Understand impact of changes |

## When to Use

- Before implementing any non-trivial feature
- When multiple valid approaches exist
- When the problem is unclear or ambiguous
- When previous attempts have failed
- When architectural decisions are needed

## When NOT to Use

- For trivial, well-understood changes
- When the solution is already determined
- For bug fixes where root cause is clear
- For formatting/style changes
