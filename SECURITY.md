# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in Universal Engineering Augmentation, please report it responsibly.

**Do not publicly disclose exploitable vulnerabilities before coordination.**

To report a vulnerability:

1. Use [GitHub Private Security Reporting](https://github.com/aspire488/Universal-Engineering-Augmentation/security/advisories/new) to submit a report
2. Include a description of the vulnerability, affected components, and potential impact
3. Allow time for assessment and remediation before public disclosure

## Security Expectations

### No Secrets in Code

- Never commit API keys, tokens, passwords, or credentials
- Use environment variables or secure vaults for sensitive configuration
- Event logs store metadata only — no source code, secrets, or credentials

### No Private Data in Public Releases

- Private project paths must not appear in public code
- KIO-specific implementation or data must not enter the public repository
- Generated/runtime artifacts (SQLite databases, worktrees) are gitignored

### Event Log Privacy

The event logging system records:
- Event types and timestamps
- Task metadata and status
- Candidate proposals and decisions

The event logging system does **not** record:
- Source code content
- Secrets or credentials
- Private project paths
- Personal information

## Scope

This security policy applies to the code published in the `aspire488/Universal-Engineering-Augmentation` repository. It does not apply to private deployments or forks that introduce additional code.
