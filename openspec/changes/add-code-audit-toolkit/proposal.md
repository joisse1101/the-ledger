## Why

There is no repeatable way to audit a branch for quality, security and architecture problems before a PR. Running linters, scanners and an LLM review by hand is slow, and an LLM reading raw code with no evidence invents findings. A single `/code-audit` command that runs deterministic tools first and hands only their JSON evidence to focused subagents gives fast, grounded feedback. The toolkit can only install skills today, so it cannot ship the command and agents this needs.

## What Changes

- Add a `/code-audit` command that runs two phases in one entry point:
  - **Phase 0 (quality gate):** detect the stack, run linters and type checkers (Ruff, mypy, ESLint, tsc, Clippy), and hard-stop only on syntax or type errors. Lint and style findings go into the report instead of stopping the run.
  - **Phase 1 (security and health):** run gitleaks, semgrep, jscpd and trivy, writing structured JSON to a per-run evidence folder, `code-audit/<run>/` in the audited repo (git-ignored). Then spawn `sec-checker` (OWASP and data-flow review, false-positive filtering) and `arch-checker` (KISS, YAGNI, DRY refactors) over that evidence.
  - **Report:** one triage table of Critical (blockers), Medium (refactor) and Low (tech debt). Scanners set baseline severity; subagents may adjust it with a one-line reason.
- The audit is strictly read-only toward the audited repository, enforced by layered hard blockers rather than prompt instructions: subagents get a read-only tool allowlist and a blocking hook, scanners run in report-only mode, the audit writes only inside its own git-ignored `code-audit/` folder and only ever audits the repo it is launched in, and a before/after tamper check fails the audit if any repo file changed.
- Default scope is files changed against `main`; `--full` scans the whole repo.
- A scanner that is not installed is reported as skipped, never as a failure.
- Add a stdlib-only Python engine, `toolkit/skills/code-audit/scripts/audit.py`, shipped inside the `code-audit` skill so the skill folder stays self-contained.
- Add `toolkit/commands/code-audit.md`, `toolkit/agents/sec-checker.md` and `toolkit/agents/arch-checker.md`.
- Extend the installer to also copy `toolkit/agents/` and `toolkit/commands/`, with the destinations declared in `targets.json`, keeping the no-silent-overwrite, `-List` and `-Uninstall` behavior for all three kinds.
- Remove the `toolkit-hello` sample skill; `code-audit` becomes the shipped content that exercises the install path.
- Update `toolkit/README.md`, `CLAUDE.md` and `wiki/Repository-Layout.md` to describe the wider toolkit.

## Capabilities

### New Capabilities
- `code-audit`: the `/code-audit` workflow, covering phases, scan scope, evidence files, missing-tool handling, subagent roles, severity rules and the triage report.

### Modified Capabilities
- `toolkit-skills`: the toolkit now holds agents and commands as well as skills; the installer copies all three kinds; the scope limit widens from "only the skills folder" to "only Claude Code's skills, agents and commands folders"; the sample-skill scenario changes because `toolkit-hello` is removed.

## Impact

- **New files:** `toolkit/skills/code-audit/` (SKILL.md, `scripts/audit.py`, reference files), `toolkit/commands/code-audit.md`, `toolkit/agents/{sec-checker,arch-checker}.md`.
- **Changed files:** `toolkit/install/Install-Skills.ps1`, `toolkit/install/targets.json`, `toolkit/README.md`, `CLAUDE.md`, `wiki/Repository-Layout.md`, `openspec/specs/toolkit-skills/spec.md` (via delta).
- **Removed:** `toolkit/skills/toolkit-hello/`.
- **Dependencies:** none are added to the repo. Scanners (gitleaks, semgrep, jscpd, trivy) and linters are optional, user-installed, and detected at run time. Python 3 is needed only to run `audit.py`.
- **Writes by the audit:** only inside `code-audit/` at the root of the audited repo (self-ignored by git, excluded from scope and the tamper check). Nothing outside the working directory is read or written. The installer now writes to `~/.claude/agents/` and `~/.claude/commands/` (or the project `.claude/` equivalents), and still never touches `settings.json` or hooks.
