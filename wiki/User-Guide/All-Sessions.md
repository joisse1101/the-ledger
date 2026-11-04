# Guide: All sessions

Find any past or present Claude Code session, read what it did and delete a transcript you no longer want.
A session is one conversation with Claude Code. See [Glossary](Glossary.md#session).

## Search

1. Open **Manage Sessions** in the top bar. The page is titled "Sessions". On a phone the tab is called Sessions.
2. Click the box labelled "Search sessions". Its hint reads "Search session ID, last message, or prompt".
3. Type text. The list updates a moment after you stop typing.

## Filter

1. Click **Project**, **Version**, **Branch** or **Worktree** above the list.
2. Tick one or more values. A number on the button counts what you picked.
3. Combine filters. A session must match all of them.
4. Read "No values yet" as a filter with nothing to offer.
5. Read "No sessions match the current filters." when nothing matches.

## Sort

1. Click a column header to sort by it. Click it again to reverse the order.
2. On a phone, use the **Sort by** menu and the up or down arrow button instead, because cards have no headers.
3. The list starts with the most recently updated session first.

## Read the list

- Columns include Project, Title, Updated, Started, Messages, Cost, Context, Model, OpenSpec, Version, Branch, Worktree, Session ID and Live.
- A **Live** badge marks a session that is running now.
- A `*` beside a cost marks an estimate. Hover it for what it leaves out.
- Below the list, "Showing N of M" tells how many you see. Click **Load more** for the next page.

## Open a session

1. Click a row. A detail window opens over the list.
2. Read the recap: the title, the last message from Claude (or the first prompt) and figures such as Started, Last updated, Messages and Cost.
3. Read "Current context" and the "Tokens per response" chart. Hover or click a bar for what filled it.
4. Open **All responses** for a per-response table.
5. Read "What filled the context" to see which tools added the most.
6. Click **Close** (the X) when done. Click **Retry** if it says it couldn't load.

## Delete a session

Only a browser on the PC that runs the Ledger shows this control. A live session cannot be deleted.

1. Open the session.
2. Click **Delete this session**.
3. Read "Delete this session transcript? This cannot be undone."
4. Click **Confirm delete**, or **Cancel** to keep it.

## Checked and unchecked

- Checked: every name above against `SessionsPage.tsx`, `AllList.tsx`, `FilterMultiselect.tsx` and `SessionDialog.tsx`.
- Unchecked: not clicked through in a running browser.
- Unchecked: that a live session shows the note "This session is still live and can't be deleted." It is in the source and not seen running.

## More detail

- [Frontend: Sessions](Frontend-Sessions.md) explains how the page is built.
- `openspec/specs/web-dashboard/spec.md` holds the requirements.
