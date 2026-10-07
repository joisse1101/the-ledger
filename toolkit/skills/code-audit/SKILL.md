---
name: code-audit
description: Read-only code audit engine and report format. Runs linters, type checkers and security scanners (gitleaks, semgrep, jscpd, trivy) over a git diff or the whole repo, writes structured JSON evidence into the repo's own git-ignored code-audit/ folder, and defines how subagent findings are merged into a Critical/Medium/Low triage report. Used by the /code-audit command and the sec-checker and arch-checker agents.
---

# code-audit

The deterministic half of `/code-audit`. The slash command sequences the steps and the two reviewer
agents add judgment; this skill holds the engine and the formats they share.

**The audit never modifies the audited repository.** The engine runs every tool in report-only mode,
writes only to `code-audit/<run>/` at the root of the repository it was launched in (self-ignored by
git), never touches a path outside that repository, and can prove afterwards that the rest of the
repository is unchanged.

## Engine

`scripts/audit.py` (Python 3, standard library only; works on Windows, macOS and Linux). Run it with
`python` (or `python3`) from inside the repository being audited. Never pass `--repo`: the engine audits the
repository that contains the current directory and refuses any other.

| Step | Command | Exit codes |
|---|---|---|
| Scope, snapshot, evidence folder | `audit.py --init [--full]` | 0 ok, 3 nothing to audit |
| Phase 0: linters and type checkers | `audit.py --phase 0 --evidence <dir>` | 0 pass, 2 syntax or type error |
| Phase 1: security and health scanners | `audit.py --phase 1 --evidence <dir>` | 0 |
| Tamper check | `audit.py --verify --evidence <dir>` | 0 clean, 4 repository changed |
| Save the final report | `audit.py --save-report --evidence <dir>` (report on stdin) | 0 |

`--init` prints one JSON line containing the `evidence` folder path. Pass that path to every later step
and to the agents.

Scope defaults to files changed against `main` (then `master`, then the whole repo with a notice) plus
uncommitted and untracked files. `--full` audits every tracked file.

## Reference files (read only when needed)

- `references/evidence.md`: the files in the evidence folder and the normalized finding shape.
- `references/severity.md`: how each tool's levels map to Critical, Medium and Low, and the rules for
  adjusting one.
- `references/report.md`: the agent output format and the final triage report layout.

## Tools

Optional, never installed by the audit; a missing tool is recorded as skipped with an install hint.

| Phase | Tool | Runs when |
|---|---|---|
| 0 | ruff, mypy | Python files in scope |
| 0 | tsc, eslint | TypeScript or JavaScript files in scope |
| 0 | cargo clippy | Rust files in scope |
| 1 | gitleaks, semgrep, jscpd, trivy | always |
