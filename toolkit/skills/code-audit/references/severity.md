# Severity

Every finding starts with a baseline from its scanner, mapped to three levels:

- **Critical (blocker):** fix before merge.
- **Medium (refactor):** fix soon.
- **Low (tech debt):** track it.

## Baseline mapping (implemented in `audit.py: map_severity`)

| Tool | Level | Severity |
|---|---|---|
| gitleaks | any hit | Critical |
| semgrep | ERROR | Critical |
| semgrep | WARNING | Medium |
| semgrep | INFO | Low |
| trivy | CRITICAL, HIGH | Critical |
| trivy | MEDIUM | Medium |
| trivy | LOW, UNKNOWN | Low |
| jscpd | duplicate block | Low |
| ruff | rule families F, E9, B, S, PLE | Medium |
| ruff | everything else (style) | Low |
| eslint | error | Medium |
| eslint | warning | Low |
| clippy | warning | Low |
| mypy, tsc, clippy error, any syntax error | | Critical, and stops the audit in Phase 0 |

## Adjusting a severity

A reviewer agent MAY raise or lower a finding's severity when the code context justifies it, for
example a semgrep ERROR on a code path that never receives user input, or a duplicate block that sits
on an authentication path.

Every adjustment MUST carry `adjusted_from` (the baseline) and a one-line `reason`. An adjustment with
no reason is ignored and the baseline stands. The report shows the original severity, the new severity
and the reason.
