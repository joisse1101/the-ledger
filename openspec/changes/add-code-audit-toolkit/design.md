## Context

`toolkit/` today holds skills only. `Install-Skills.ps1` copies each `toolkit/skills/<name>/` folder into `~/.claude/skills/` (or `<project>/.claude/skills/`), decides "differs" with a SHA-256 over every file's relative path and content, and reads destinations from `targets.json` (`{ "claude-code": { "global": "~/.claude/skills", "project": ".claude/skills" } }`). Agents and commands are single `.md` files, not folders. See proposal.md for motivation.

Host facts that shape the design: the repo is developed on Windows with PowerShell, only `semgrep` is installed locally, and the other scanners are not. Audited repos here are Python (`api/`) and TypeScript (`web/`).

## Goals / Non-Goals

**Goals:**
- One `/code-audit` entry point; deterministic evidence first, subagents second.
- Same behavior on Windows, macOS and Linux.
- Installer handles skills, agents and commands with one code path and the existing drift logic.

**Non-Goals:**
- Installing or version-managing the scanners themselves.
- Auto-fixing findings.
- CI integration or SARIF export.
- Supporting tools other than Claude Code (the data-driven `targets.json` stays open to it later).

## Decisions

### D1. Engine is one stdlib-only Python script inside the skill
`toolkit/skills/code-audit/scripts/audit.py` does stack detection, scope resolution, tool execution, skipping, normalization and the Phase 0 gate. It is installed as part of the skill folder, so the command and agents call `~/.claude/skills/code-audit/scripts/audit.py` (or the project equivalent).
- *Why:* the toolkit is cross-platform and a skill folder must be self-contained. One Python file avoids a bash and PowerShell pair that drift apart, and avoids needing `jq`.
- *Alternatives:* `run-linter.sh` (breaks on pure PowerShell, needs jq); a bash and PowerShell pair (double maintenance); a separate `toolkit/scripts/` install target (one more location to drift).
- The command must locate the script whether installed globally or per project; it checks the project path first, then the global one.

### D2. Command and agents are thin; the skill holds the logic
`commands/code-audit.md` only sequences: run `audit.py --phase 0`, stop on a gate failure, run `audit.py --phase 1`, spawn the two agents, merge. `agents/sec-checker.md` and `agents/arch-checker.md` hold the review prompts. `skills/code-audit/SKILL.md` documents the evidence format and report format so they are defined once, and reference files carry the severity mapping.
- *Why:* behavior changes then touch one place, and the skill alone is still usable if someone installs only skills.

### D3. Evidence contract: per-run JSON outside the repo
`audit.py` creates an evidence folder under the OS temp directory (`<tmp>/code-audit/<repo-name>-<timestamp>/`, path printed and passed to the agents) and writes `scope.json` (mode, base ref, file list), `phase0.json`, one normalized file per tool (`gitleaks.json`, `semgrep.json`, `jscpd.json`, `trivy.json`) and `summary.json` listing each tool as `ran`, `skipped` (reason) or `failed`. Each finding is normalized to `{tool, rule, severity, file, line, message}`. Raw tool output is kept next to it for agents that need detail.
- *Why:* agents read compact, uniform evidence instead of four tool formats. Keeping it outside the repo means the audit writes nothing into the repo, and there is no `.gitignore` to manage.
- Tools that insist on writing a report file (jscpd) are pointed at this folder.

### D4. Scope: diff against `main`, `--full` for everything
`audit.py` resolves the file list with `git diff --name-only <merge-base of main and HEAD>` plus uncommitted and untracked files; `--full` uses `git ls-files`. Scanners get the file list where they accept one; otherwise their findings are filtered to it after the run.
- *Why:* fast pre-PR feedback and less LLM input. Filtering post-hoc keeps behavior correct for tools that only scan directories.
- If `main` does not exist, fall back to `master`, then to `--full` with a notice.

### D5. Phase 0 gate semantics
Per detected stack: Python (Ruff, mypy), TypeScript/JavaScript (tsc `--noEmit`, ESLint), Rust (cargo clippy). A **syntax or type error** is a gate failure (non-zero exit from `audit.py --phase 0`, `gate: "fail"` in `phase0.json`); lint rule violations are findings only. Ruff syntax errors (E9) and parse errors count as gate failures; other Ruff rules do not. A missing tool is `skipped`, not a failure.
- *Why:* hard-stopping on style would block the whole audit over cosmetics and waste the point of the later phases.
- *Trade-off:* without mypy or tsc installed the gate is weaker; the report says so via the skipped list.

### D6. Severity baseline, agent adjustment recorded
Normalization maps each tool's levels to Critical, Medium or Low (for example gitleaks hits and semgrep ERROR to Critical; semgrep WARNING and Ruff errors to Medium; INFO, style and duplication to Low), documented in a skill reference file. Agents return findings with an optional `adjusted_from` and `reason`; the command merges them and shows both. Agents may not add severity changes without a reason.
- *Why:* keeps ratings anchored in evidence while allowing judgment where data flow clarifies impact.

### D7. Installer: kinds as data, one copy path
`targets.json` gains per-kind destinations:
```
"claude-code": {
  "skills":   { "global": "~/.claude/skills",   "project": ".claude/skills" },
  "agents":   { "global": "~/.claude/agents",   "project": ".claude/agents" },
  "commands": { "global": "~/.claude/commands", "project": ".claude/commands" }
}
```
Source locations are `toolkit/skills/<name>/` (folder), `toolkit/agents/<name>.md` and `toolkit/commands/<name>.md` (file). The existing hash function is generalized to hash either a folder or a single file; state, `-List`, `-Force` and `-Uninstall` apply to every kind. A `-Kind skills|agents|commands` parameter restricts the action; `-Skill` is kept for compatibility and `-Name` is added for any kind (the script keeps its filename, `Install-Skills.ps1`, to avoid churn in docs and habits).
- *Why:* extending the data file and one function keeps the safety guarantees identical across kinds.
- *Alternatives:* a second installer script (duplicated logic); a plugin manifest (vendor-specific, rejected earlier by the spec).
- Names must be unique within a kind only. If a name exists as both skill and command, `-Name` without `-Kind` acts on both.

### D9. Read-only enforcement in layers
No single layer is airtight, so each covers a gap in the others. Preventive layers come first, a detective layer last.
1. **Subagent tool allowlist (hard):** `sec-checker.md` and `arch-checker.md` declare `tools: Read, Grep, Glob` in frontmatter. No Edit, Write, Bash or Task, so they cannot modify files or run commands at all. They read the evidence folder by absolute path.
2. **Subagent blocking hook (hard):** the same frontmatter declares a `PreToolUse` hook, scoped to that agent, that exits with a block for any tool outside the allowlist or any path outside the repo and evidence folder. It is defence in depth in case the allowlist is loosened by a later edit.
3. **Main-session limits:** the command's `allowed-tools` pre-approves only `audit.py` and the agent launch. This reduces prompts but does not by itself deny Edit or Write in the main session. The command therefore does its own work only through `audit.py` and the two agents, and never edits. Whether a command or skill can also *deny* tools for its own run is verified in a spike (task 3.6) before relying on it.
4. **Scanners in report-only mode:** `audit.py` builds every tool's command line from a fixed table with no auto-fix flags (no `ruff --fix`, `eslint --fix`, `semgrep --autofix`, `cargo clippy --fix`), and the unit tests assert that no fix flag appears in any generated command.
5. **Tamper check (detective):** before running anything `audit.py` snapshots `git status --porcelain=v1 -z`, `git rev-parse HEAD`, and a content hash for every in-scope file and every untracked file. After the agents finish, `audit.py --verify` compares. Any difference makes the audit fail with the changed paths, and the report is headed "AUDIT INVALID" rather than shown as clean.

Settings-level `permissions.deny` rules would be the strongest main-session block, but the installer must not modify `settings.json` (see the `toolkit-skills` spec). They are documented in the README as an optional, manual hardening step and are not installed.
- *Why layered:* the allowlist stops agents by construction, the hook stops mistakes in future edits, the fixed command table stops tools mutating files, and the tamper check catches anything that slipped through, including from the main session.
- *Alternatives:* prompt instructions only (rejected: not a blocker); running the whole audit in a throwaway `git worktree` (strong isolation but slower, and needs the toolchain in the worktree; kept as a possible later option).

### D8. Remove `toolkit-hello`
`code-audit` is the first real content, which satisfies the README's own "delete once real skills exist" note. The install path is exercised by the real skill, agents and command.

## Risks / Trade-offs

- [Scanners absent on most machines, so audits are thin] → The report always lists skipped tools with an install hint; the README lists the tools.
- [Tool output formats change between versions] → Normalizers are tolerant, treat unparseable output as `failed` with the raw file kept, and never crash the audit.
- [Agents hallucinate beyond the evidence] → They are told to cite scanner rule or file and line, are given only the evidence plus flagged files, and findings without a citation are dropped by the command.
- [Windows quirks: path separators, `npx` and `.cmd` shims] → Use `shutil.which` and `subprocess` with argument lists, never shell strings; tested on Windows first.
- [Main session could still edit if it ignores the command] → The tamper check fails the audit loudly, and the spike (task 3.6) looks for a real deny mechanism; the residual risk is documented, not hidden.
- [Hook or allowlist syntax differs by Claude Code version] → Tasks verify that a deliberately malicious agent prompt is actually blocked, on the installed version.
- [Installer now writes outside `skills/`] → Still limited to the three folders and never `settings.json` or hooks; the spec states this explicitly.
- [Agent name collisions with a user's own `sec-checker`] → Covered by the existing differ-and-skip behavior; nothing is overwritten without `-Force`.
- [`jscpd` and `trivy` are slow on `--full`] → Per-tool timeouts, with a timeout recorded as `failed` rather than hanging the audit.

## Migration Plan

1. Land the installer and `targets.json` changes with existing skills still installing identically.
2. Add the skill, agents and command; delete `toolkit-hello`.
3. Users re-run the installer; anyone who installed `toolkit-hello` can remove it with `-Uninstall -Name toolkit-hello` before it leaves the toolkit, or delete it by hand (uninstall only removes toolkit items, so a leftover copy stays and is harmless).
4. Rollback: revert the change and run the installer with `-Uninstall`.

## Open Questions

- Which exact Ruff and ESLint rule sets count as syntax and type errors for the gate can be tuned after the first real runs without changing specs.
