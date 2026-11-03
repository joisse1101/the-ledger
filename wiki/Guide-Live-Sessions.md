# Guide: Live sessions

See the Claude Code sessions running now, answer a session's prompt from the dashboard, let a session approve plain prompts on its own, and spot sessions that should be compacted.
A [live session](Glossary.md#live-session) is a session whose Claude Code process is running.

## See running sessions

1. Open **Sessions** in the top bar. The page is titled "Live Sessions". On a phone the tab is called Live.
2. Read one row per running session. The columns include Project, Name, Title, Status, Kind, PID, Context, Compact, Decision and Session ID.
3. Read **Context** as how many tokens the session's latest request sent.
4. Keep **Auto-refresh** on to update the list about every 2 seconds. Turn it off to freeze the list.
5. Check the "Last refreshed" time beside it.
6. If nothing is running the page says "No live sessions. Start a Claude Code session to see it here."

## Spot sessions that need compacting

[Compact](Glossary.md#compact) means summarising a long conversation to free space.

1. Look at the **Compact** column, or the badge on a phone card.
2. Read "Should compact" as a hint and "Needs compact" as a stronger one.
3. Read a muted badge as an idle session, which is not growing right now.
4. Know that the dashboard only shows the badge. It has no control that compacts a session.

## Answer a prompt from the dashboard

A [pending decision](Glossary.md#pending-decision) is a prompt a session is blocked on. This needs the [relay hook](Glossary.md#relay-hook) installed. See [Getting started](Guide-Getting-Started.md).

1. Look for a badge in the **Decision** column. It reads "Needs decision" followed by a tool name, or "Asking a question".
2. Click the session's row. A control panel opens below the list, headed by the session's title.
3. For a permission prompt, read the tool name and its input.
4. Click **Approve** to allow it, or **Deny** to refuse it.
5. After **Deny**, type an optional reason, then click **Confirm deny**. Click **Back** to change your mind.
6. For a question, tick or pick an option for each question. Choose **Other** to type your own answer.
7. Click **Send answer**. It stays disabled until every question has an answer.
8. Read "Answer sent." when it worked.
9. If you see "This session already moved on", the prompt was answered somewhere else first. The terminal and the dashboard both work, and the first answer wins.
10. If the panel says "Nothing is waiting on you", no prompt is pending, or the relay hook is not installed.

The panel also has **Open repo window**, which opens or focuses that session's repository in your editor on the PC. Click **Close** (the X) to close the panel.

The panel opens by itself when a session starts waiting on you.

## Turn on auto-approve

[Auto-approve](Glossary.md#auto-approve) answers "allow" to plain permission prompts for one session. It never answers questions or plan approvals, and it skips commands that look dangerous.

1. Wait until the dashboard has seen at least one relayed prompt. Until then the switch is hidden.
2. Open the session's panel as above.
3. Flip the **Auto-approve** switch beside the title. It works only in a browser on the PC that runs the Ledger.
4. Read the "Auto-approve" column or card badge to see which sessions have it on.
5. Read "Last auto-approved" in the panel to see what was approved for you.
6. Expect it to switch off by itself after a backend restart.

## Remote mode

The Remote mode switch and the **QR code** button sit above the list. See [Remote access](Guide-Remote-Access.md).

## Checked and unchecked

- Checked: column headers, badge texts, button names, switch labels and messages above against `LiveList.tsx`, `LiveSessionPanel.tsx`, `LiveControl.tsx`, `DecisionPrompt.tsx` and `AutoApproveControl.tsx`.
- Unchecked: the panel opening by itself, read from `LiveSessionsPage.tsx` only and not seen running.
- Unchecked: the thresholds for the two compact badges. Take them from [Glossary](Glossary.md#compact).
- Unchecked: which columns a phone card hides.

## More detail

- [Frontend: Sessions](Frontend-Sessions.md) explains the page.
- [Live sessions and prompts](Backend-Live-Sessions-And-Prompts.md) explains how the backend relays prompts.
- `openspec/specs/remote-session-control/spec.md` and `openspec/specs/web-dashboard/spec.md` hold the requirements.
