# Evidence folder

`audit.py --init` creates `<repo>/code-audit/<timestamp>/` in the repository it was launched in, plus
`<repo>/code-audit/.gitignore` (`*`) so git ignores the whole folder. It is excluded from the audit's
scope and from the tamper check. Agents read these files by absolute path.

| File | Written by | Contents |
|---|---|---|
| `scope.json` | `--init` | `mode` (`diff` or `full`), `base_branch`, `base_ref`, `notice`, `repo`, `files` (repo-relative, forward slashes) |
| `snapshot.json` | `--init` | pre-audit repository state for the tamper check; ignore it |
| `phase0.json` | `--phase 0` | `gate` (`pass` or `fail`), `gate_errors`, `findings`, `tools` |
| `gitleaks.json`, `semgrep.json`, `jscpd.json`, `trivy.json` | `--phase 1` | normalized findings for that tool, filtered to the scope |
| `*.raw.json`, `jscpd-raw/` | `--phase 1` | the tool's own output, for detail |
| `summary.json` | `--phase 1` | `phase0_gate`, `phase0_tools`, `phase1_tools`, severity `counts` |
| `verify.json` | `--verify` | `ok` and the list of `changes` |
| `agent-sec-checker.json`, `agent-arch-checker.json` | the agents' `Stop` hook (`--save-agent`) | each reviewer's JSON reply |
| `report.md` | `--report` | the final triage report, built from all the files above |

## Tool status

Each entry in `tools` / `phase1_tools` is one of:

- `{"status": "ran", "findings": N, ...}`
- `{"status": "skipped", "reason": "not installed (<install hint>)"}`
- `{"status": "failed", "reason": "..."}`: timed out, crashed or produced unparseable output. A failed
  tool is not a clean tool; report it as failed.

A language with no files in scope has no entry at all.

## Normalized finding

```json
{"tool": "semgrep", "rule": "python.lang.security.audit.dangerous-exec", "severity": "Critical",
 "file": "api/app.py", "line": 42, "message": "..."}
```

`file` is repo-relative with forward slashes; `line` is 0 when the tool gives none (for example a
dependency vulnerability in a lockfile). `severity` is the scanner baseline (see `severity.md`).
