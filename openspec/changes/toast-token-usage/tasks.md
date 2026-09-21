## 1. Confirm the hook payload

- [ ] 1.1 Capture one real hook payload: temporarily make the installed copy (`~/.claude/hooks/Send-ClaudeToast.ps1`) write the raw stdin to a scratch file, trigger a real `Stop` event, then revert the temporary line. Verify the captured JSON contains `transcript_path`, `session_id`, and `cwd`, and that the installed copy is back to matching the repo copy. If `transcript_path` is missing, derive `~/.claude/projects/<sanitized cwd>/<session_id>.jsonl` (every non-alphanumeric character becomes `-`) as the design describes, and update `design.md` accordingly.

## 2. Context lookup in `Send-ClaudeToast.ps1`

- [ ] 2.1 Add a lookup function that opens the transcript with `FileShare.ReadWrite`, reads a 256 KB tail window (doubling until a real turn is found or the file start is reached), drops the first line when the read did not begin at byte 0, and walks lines from the end using the raw-line regex rules in the design (assistant, not sidechain, not `<synthetic>`, non-zero total). It returns the total tokens or `$null`, and any failure inside it resolves to `$null` via `try/catch`. Verify against the real local transcript `c2cf6150-07ea-4320-885a-cfb7ada6539b.jsonl`, whose newest line is an all-zero `<synthetic>` error turn: the function must return 429,973 (not 0), matching `claude_context.py`'s result once that exists, and it must not throw on a missing path.
- [ ] 2.2 Add the humanising function (exact below 1,000, nearest thousand with `k` up to but below 1,000,000, one decimal with `M` above), using the same rounding boundary as the gauge (`live-context-gauge` task 1.2). Verify by running it inline for 742, 80618, 1234567, and a value just below 1,000,000: outputs must be `742`, `81k`, `1.2M`, and not `1000k`.

## 3. Toast integration

- [ ] 3.1 Read `transcript_path` from the stdin JSON and, when the lookup returns a value, add a third `New-BTText` (`Context <n>`) to the binding; otherwise leave the binding as it is today. Verify with the README's Test 2 style command: piping `{cwd, transcript_path}` for a real transcript shows a three-line toast, and piping only `{cwd}` shows the original two-line toast with no error.
- [ ] 3.2 Verify the degrade paths each leave a normal two-line toast and exit code 0: a nonexistent `transcript_path`, an empty transcript, and a transcript with no usage-bearing assistant lines. Check `$LASTEXITCODE` after each run.
- [ ] 3.3 Verify live-fire behavior in a real session: let a `Stop` and a `Notification` event fire, confirm both toasts show the third line, and compare the number to the transcript's latest real turn. Confirm clicking the toast still focuses or opens the repo's VS Code window. Record in `design.md`'s Risks whether the number was ever one turn stale.

## 4. Documentation and rollout

- [ ] 4.1 Update `hooks/README.md`: the script's description, a new test that pipes a real `transcript_path` and expects the `Context` line, a note that the existing Test 2 (cwd only) exercises the no-token path, and that existing installs need one re-run of `Install-ClaudeHooks.ps1`. Verify by following the README's own steps on this machine and getting the documented results.
- [ ] 4.2 Re-run `hooks/Install-ClaudeHooks.ps1` to refresh the installed copy. Verify `hooks/scripts/Send-ClaudeToast.ps1` and `~/.claude/hooks/Send-ClaudeToast.ps1` are identical (`diff` reports no differences), and `openspec validate toast-token-usage --strict` still reports valid.
