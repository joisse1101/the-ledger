# Agent output and report format

## What a reviewer agent returns

One fenced `json` block and nothing else of substance. Prose outside the block is ignored.

```json
{
  "findings": [
    {
      "severity": "Critical",
      "file": "api/db.py",
      "line": 88,
      "source": "semgrep:python.lang.security.audit.formatted-sql-query",
      "message": "User-controlled `name` reaches a SQL string built with an f-string.",
      "fix": "Use a parameterized query: cursor.execute('... WHERE name = ?', (name,)).",
      "principle": null,
      "adjusted_from": null,
      "reason": null
    }
  ],
  "dismissed": [
    {"source": "semgrep:rule-id", "file": "api/x.py", "line": 12,
     "reason": "Value is a module constant, never user input."}
  ]
}
```

Rules:

- `source` is either `<tool>:<rule>` (a scanner finding the agent confirmed or raised) or
  `review:<file>:<line>` (the agent's own finding from reading the file). **A finding with no usable
  `source`, file or line is dropped by the command.**
- `principle` is set by the architecture agent: `KISS`, `YAGNI` or `DRY`. `fix` is a concrete
  refactor, not "consider simplifying".
- `adjusted_from` and `reason` are set only when the agent changes a baseline severity.
- `dismissed` lists scanner findings judged to be false positives, each with a one-line reason.
  Dismissed findings leave the triage and appear in their own section.

## The final report

```
# Code audit: <repo> (<diff vs main | full>, <N> files)

[ AUDIT INVALID banner when --verify failed: lists every changed path, and no clean result is shown ]

## Critical (blockers)
| Location | Source | Finding | Suggested fix |
## Medium (refactor)
| ... same columns ... |
## Low (tech debt)
| ... same columns ... |

## Dismissed as false positives
- <source> <file>:<line>: <reason>

## Severity adjustments
- <file>:<line> <source>: <from> -> <to>: <reason>

## Skipped or failed tools
- <tool>: <reason and install hint>

## Scope
<mode>, base <ref>, <N> files; evidence at <folder>
```

- A group with no findings is written as "none".
- A clean audit says so explicitly and still prints the scope and skipped tools.
- Phase 0 lint findings and Phase 1 scanner findings the agents did not review are included at their
  baseline severity.
- Skipped tools are always listed, because a skipped scanner means less was checked.
