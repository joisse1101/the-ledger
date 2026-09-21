## Context

See proposal.md for motivation. Current state and constraints:

- `hooks/scripts/Send-ClaudeToast.ps1` reads the hook's JSON payload from stdin but uses only `cwd`. It builds a BurntToast with two text elements (title, body) and a protocol-activation click action, then exits. The repo copy and the installed copy in `~/.claude/hooks/` are byte-identical.
- The hook payload is documented to include `transcript_path` and `session_id` alongside `cwd`. That is expected but not yet observed in this install.
- `hooks/` is a standalone utility shared as a folder to other machines, so the script can't import `claude_context.py` or depend on the app's venv. It runs under `powershell.exe` (Windows PowerShell 5.1) and already pays BurntToast's module-import cost on every fire.
- Claude Code keeps the transcript open for appending while the session runs. Transcripts reach about 10 MB, with individual lines of several KB.
- The number to show is the `live-context-gauge` definition of context: `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` on the latest real main-thread assistant turn. See that change's design (Decision 3).

## Goals / Non-Goals

**Goals:**
- One extra toast line, `Context 394k`, that is cheap (milliseconds) and can't make the toast fail or arrive late.
- The same number the dashboard gauge would show for the same session.

**Non-Goals:**
- No fallback derivation of the transcript path from `session_id` + `cwd` unless the payload check (see Risks) shows `transcript_path` is missing.
- No Pester or other automated PowerShell test setup. `hooks/` has none today and is verified by the README's manual tests.
- No shared code with the Python side. Only the rule is shared, not the implementation.

## Decisions

**1. Only the script changes, and it adds a third text element.** `Send-ClaudeToast.ps1` computes the context line and appends a third `New-BTText` to the existing binding. `-Title` and `-BodyTemplate` keep their meaning, so `settings.json` and the installer stay untouched, and both hook events get the line for free. Windows toasts show a title plus two body lines, so a third text element fits.
*Alternative:* append the number to the body string. Rejected: it makes long repo names wrap, and the separate line reads more clearly at a glance.

**2. Read the transcript from the tail, in PowerShell.** Open `transcript_path` with `FileShare.ReadWrite` (the file is being appended to), read the last 256 KB, decode UTF-8, and drop the first line unless the read began at byte 0 (it's likely cut mid-record). Walk lines from the end. If no real turn is found, double the window until one is or the start of the file is reached. Most fires will need only the first window, since the last real turn is usually within the final few lines.
*Alternatives:* `Get-Content -Tail` (slow on 10 MB files in 5.1); shelling out to Python (not available on shared machines, and adds process-start latency).

**3. Pull the four numbers out of the raw line with regexes, not `ConvertFrom-Json`.** A candidate line must contain `"type":"assistant"`, must not contain `"isSidechain":true` or `"model":"<synthetic>"`, and must yield non-zero `"input_tokens":N`, `"cache_read_input_tokens":N` and `"cache_creation_input_tokens":N` (the leading quote keeps `input_tokens` from matching inside `cache_creation_input_tokens`). The first match in a line is the top-level `usage` object, given the observed key order. Transcript lines can be several KB, and `ConvertFrom-Json` in 5.1 is slow and size-limited on large inputs.
*Trade-off:* regexes tie the script to the current field spellings, but the JSON parse would too, and a miss degrades to no line (Decision 5).

**4. Same rule as the gauge, stated in both places.** Latest line that is an assistant turn, not a sidechain, not `<synthetic>`, with a non-zero total. Skipping synthetic and zero-usage lines matters: an API-error turn appears as an all-zero line and would otherwise show `Context 0`. No de-duplication by message id is needed here, since only the last qualifying line is used.

**5. Never delay or break the toast.** The lookup is wrapped in `try/catch` and returns `$null` on any problem: missing `transcript_path`, missing file, no qualifying line, malformed data. `$null` means the third text element is simply not added, giving today's toast. The lookup runs once, reads once, and has no retries or waits.

**6. Compact number format.** Under 1,000: the exact number. From 1,000 up to but below 1M: rounded to the nearest thousand with `k` (`80,618` becomes `81k`). At 1M and above: one decimal with `M` (`1.2M`). The dashboard's gauge should use the same humanising so the two agree on sight.

**7. Verification is manual, via the README.** Add a test that pipes `{cwd, transcript_path}` (pointing at a real transcript) into the script and expects the third line; the existing Test 2 (only `cwd`) doubles as the no-token check. The first task before writing any code is to capture one real hook payload and confirm `transcript_path` is present.

## Risks / Trade-offs

- [`transcript_path` might be absent from the payload in this install] → Verify first by dumping stdin from a real hook fire. If it's missing, derive `~/.claude/projects/<sanitized cwd>/<session_id>.jsonl` (every non-alphanumeric character becomes `-`), the same way `claude_context.py` does, and update this design.
- [The Stop hook may fire before the last assistant line is flushed, making the number one turn stale] → Accepted. Not worth a wait-and-retry that would delay the toast. To check, compare the toast against the transcript after a real Stop.
- [The rule lives in two implementations (PowerShell and `claude_context.py`) and could drift] → Both are a few lines; each design points at the other, and if either changes, the other should be reviewed.
- [Assumes one `iterations` entry per turn, so the top-level usage equals the final request's usage] → Sampled turns had one iteration; not checked exhaustively across all transcripts. If multi-iteration turns turn out to exist, the figure could be off for those turns only.
- [Regex extraction depends on JSON key spelling] → Any mismatch omits the line rather than showing a wrong number, because a missing field means no match.
- [Existing installs won't see the change until the installer is re-run] → One re-run of `Install-ClaudeHooks.ps1` copies the new script over the installed one (it is safe to re-run). Mention this in the README.
