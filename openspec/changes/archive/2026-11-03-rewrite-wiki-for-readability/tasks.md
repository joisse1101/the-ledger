# Tasks

Every group ends with `cd api; python check_docs.py` passing. Run it from `api/` with `api\.venv\Scripts\python.exe`.

## 1. Rules and glossary

- [x] 1.1 Add the readability rules to "Documentation" in `wiki/Coding-Standards.md` (purpose first, one header per topic, one idea per bullet, define terms, mark known/assumed/unchecked) and verify the section lists each rule from the spec delta (result: manual read of the "Documentation" section against the spec delta -> all 5 rules listed beside the link and size rules)
- [x] 1.2 Create `wiki/Glossary.md` defining the terms used across pages (session, live session, pending decision, auto-approve, Remote mode, relay hook, compact, gateway, access token, history store), taking each meaning from the current pages, and verify every term appears in at least two pages or is dropped (result: grep -il per term over wiki/*.md excluding Glossary.md -> each of the 9 terms appears in at least 2 pages (min 2, pending decision), none dropped; "session" is general and appears in 20+ pages)
- [x] 1.3 Link `Glossary.md` from `Home.md` and `_Sidebar.md` and verify `check_docs.py` passes (result: `python check_docs.py` from api/ (system python, worktree has no api/.venv) -> "docs check passed")

## 2. User guide

- [x] 2.1 Write `Guide-Getting-Started.md` (install, start, open the dashboard, sign in with the token) from `Setup-And-Run.md`, `openspec/specs/installer/spec.md` and `openspec/specs/app-startup/spec.md`, and verify every command in it runs as written or is marked unchecked (result: `Start-Ledger.ps1 -Help` and `Stop-Ledger.ps1 -Help` -> printed the switches used on the page; `Install-Ledger.ps1` -> not run, checked against its parameter block only; full runs of all three not done and marked unchecked on the page)
- [x] 2.2 Write `Guide-Overview.md` and `Guide-Projects.md` from `web/src/pages/OverviewPage.tsx`, `ProjectsPage.tsx` and `openspec/specs/web-dashboard/spec.md`, and verify each control name matches the source (result: control names in `Guide-Overview.md` and `Guide-Projects.md` compared by hand against `OverviewPage.tsx`, `ProjectsPage.tsx` and their components -> all matched; running app not opened, marked unchecked)
- [x] 2.3 Write `Guide-Live-Sessions.md` (see running sessions, answer a prompt, auto-approve, compact badges) from `LiveSessionsPage.tsx` and `openspec/specs/remote-session-control/spec.md`, and verify each control name matches the source (result: control names in `Guide-Live-Sessions.md` compared by hand against `LiveSessionsPage.tsx`, `LiveList.tsx`, `LiveSessionPanel.tsx`, `LiveControl.tsx`, `DecisionPrompt.tsx` and `AutoApproveControl.tsx` -> all matched; panel auto-open and compact thresholds marked unchecked)
- [x] 2.4 Write `Guide-All-Sessions.md` (search, filter, sort, open a session, delete one) from `SessionsPage.tsx` and the `web-dashboard` spec, and verify each control name matches the source (result: control names in `Guide-All-Sessions.md` compared by hand against `SessionsPage.tsx`, `AllList.tsx`, `FilterMultiselect.tsx` and `SessionDialog.tsx` -> all matched; running app not opened)
- [x] 2.5 Write `Guide-Files.md` and `Guide-Settings.md` from `FilesPage.tsx`, `SettingsPage.tsx`, `openspec/specs/file-drop/spec.md` and `openspec/specs/dashboard-settings/spec.md`, and verify each control name matches the source (result: control names in `Guide-Files.md` and `Guide-Settings.md` compared by hand against `FilesPage.tsx` and `SettingsPage.tsx` -> all matched; drop-folder location marked unchecked)
- [x] 2.6 Write `Guide-Remote-Access.md` (Remote mode, QR code, token, another device) from `Gateway.md`, `openspec/specs/network-access/spec.md` and the `web-dashboard` spec, and verify the steps against the specs (result: steps in `Guide-Remote-Access.md` compared by hand against `network-access/spec.md`, `remote-session-control/spec.md`, `RemoteModeControl.tsx` and `RemoteQrDialog.tsx` -> consistent; firewall prompt and real phone scan marked unchecked)
- [x] 2.7 Write `Guide-Widget.md` and `Guide-Notifications.md` (widget, break timer, toasts, chimes) from `Widget.md`, `Hooks.md` and the `desktop-widget`, `break-timer`, `session-chimes` and `toast-context-line` specs, and verify each statement against a spec or mark it unchecked (result: statements in `Guide-Widget.md` and `Guide-Notifications.md` compared by hand against the `desktop-widget`, `break-timer`, `session-chimes` and `toast-context-line` specs and the widget renderer files -> matched; tray names, shortcut name, sound audibility and the away idle time marked unchecked)
- [x] 2.8 End every guide page with a "More detail" link to its contributor page and spec, and verify no guide page restates a requirement (result: search for `^## More detail` in `wiki/Guide-*.md` -> 10 of 10 pages; `python api/check_docs.py` -> exit 1 with 20 problems, all orphan pages, no broken link or path; restates-no-requirement judged by reading only)

## 3. Home and sidebar

- [x] 3.1 Rewrite `Home.md` so the purpose comes first and a "User guide" section lists every `Guide-*.md` page before the contributor sections, and verify every wiki page is still listed (result: shell loop checking every `wiki/*.md` except `Home.md` and `_Sidebar.md` is linked from `Home.md` -> no page missing, including all 10 `Guide-*.md`; "User guide" section placed before the contributor sections)
- [x] 3.2 Add the "User guide" heading and every guide page to `_Sidebar.md` and verify `check_docs.py` passes (result: `python api/check_docs.py` (system python) -> "docs check passed", exit 0)

## 4. Service pages

- [x] 4.1 Rewrite `Widget.md` to the readability rules, splitting it by topic header and moving code detail under its own headers, and verify by diff that no statement of fact was dropped (result: `python api/check_docs.py` -> printed "docs check passed" (exit code not seen); `Widget.md` compared by hand against `git show HEAD:wiki/Widget.md`, no statement dropped)
- [x] 4.2 Rewrite `Gateway.md` and verify by diff that no fact was dropped (result: `python api/check_docs.py` -> printed "docs check passed" (exit code not seen); `Gateway.md` compared by hand against `git show HEAD:wiki/Gateway.md`, no fact dropped, repeated statements merged)
- [x] 4.3 Rewrite `Hooks.md` and verify by diff that no fact was dropped (result: `python api/check_docs.py` -> printed "docs check passed" (exit code not seen); `Hooks.md` compared by hand against `git show HEAD:wiki/Hooks.md`, no fact dropped)

## 5. Backend pages

- [x] 5.1 Rewrite `Backend-API-Routes.md` and `Backend-Security.md` and verify by diff that no fact was dropped (result: scratchpad cmp.py backtick-token comparison -> Backend-Security 0 of 35 tokens missing, Backend-API-Routes 6 of 193 flagged, all 6 confirmed present (table-escape `\|` and one line-wrapped command); manual statement-by-statement mapping -> no fact dropped; `python api/check_docs.py` -> docs check passed, exit=0)
- [x] 5.2 Rewrite `Backend-Data-Layer.md` and `Backend-History-Store.md` and verify by diff that no fact was dropped (result: scratchpad cmp.py backtick-token comparison -> Backend-Data-Layer 0 of 135 tokens missing, Backend-History-Store 0 of 32 missing; manual statement-by-statement mapping -> no fact dropped; `python api/check_docs.py` -> docs check passed, exit=0)
- [x] 5.3 Rewrite `Backend-Live-Sessions-And-Prompts.md` and `Backend-Overview-And-Queries.md` and verify by diff that no fact was dropped (result: scratchpad cmp.py backtick-token comparison -> Backend-Live-Sessions-And-Prompts 0 of 84 tokens missing, Backend-Overview-And-Queries 0 of 38 missing; manual statement-by-statement mapping -> no fact dropped; `python api/check_docs.py` -> docs check passed, exit=0)

## 5a. Prose rule

- [x] 5a.1 Amend the readability rules in "Documentation" in `wiki/Coding-Standards.md` so that explanations, reasons and purpose lines are written as short paragraphs, and bullets are used only for real lists, steps and parallel items, and verify the section still lists each rule from the spec delta (result: `python api/check_docs.py` -> docs check passed, exit=0; manual comparison -> Documentation section still lists purpose first, one header per topic, one idea per bullet (inside the new prose-vs-bullets rule), define terms and mark certainty, next to the link and size rules)

## 6. Frontend pages

- [x] 6.1 Rewrite `Frontend-Sessions.md`, splitting its single bullet into topic headers (Live, All, session detail, delete, chart) with one idea per bullet, and verify by diff that no fact was dropped (result: `cmp6.py` -> Frontend-Sessions: 0 missing tokens (66 checked), 0 numbers, 0 bold phrases; python `check_docs.py` -> docs check passed, exit=0; hand mapping of every HEAD statement -> none removed)
- [x] 6.2 Rewrite `Frontend-Overview.md`, `Frontend-Projects.md` and `Frontend-Files.md` and verify by diff that no fact was dropped (result: `cmp6.py` -> Overview 0 of 30 tokens missing, Projects 0 of 37, Files 0 of 20, plus 0 numbers and 0 bold phrases missing on all three; `check_docs.py` -> docs check passed, exit=0; hand mapping -> none removed)
- [x] 6.3 Rewrite `Frontend-Api-Layer.md`, `Frontend-Shell-And-Theme.md` and `Frontend-Shared-Components.md` and verify by diff that no fact was dropped (result: `cmp6.py` -> Api-Layer 0 of 78 tokens missing, Shell-And-Theme 0 of 70, Shared-Components 0 of 70, plus 0 numbers and 0 bold phrases missing on all three; `check_docs.py` -> docs check passed, exit=0; hand mapping -> none removed)

## 7. Remaining pages

- [x] 7.1 Rewrite `Setup-And-Run.md`, `Testing.md` and `Repository-Layout.md` and verify by diff that no fact was dropped (result: cmp8.py token/fence/word diff of HEAD vs working tree -> no fact missing on Setup-And-Run, Testing, Repository-Layout, only rephrasings; python api/check_docs.py -> docs check passed, exit=0)
- [x] 7.2 Rewrite `Alert-Tiering-Ideas.md`, marking what is decided, assumed and unchecked, and verify by diff that no fact was dropped (result: cmp8.py token/fence/word diff of HEAD vs working tree -> no fact missing, only rephrasings; python api/check_docs.py -> docs check passed, exit=0; labels decided/known/assumed/unchecked mapped by hand per section)

## 8. Integration check

- [x] 8.1 Run `cd api; python check_docs.py` and verify it passes for the whole wiki (result: `python api/check_docs.py` -> "docs check passed", exit=0)
- [x] 8.2 Open `Home.md` and follow each link in the "User guide" section and verify none is broken or an orphan (result: checked by hand; 10 User guide links in `wiki/Home.md` -> all 10 target files exist and all 10 are listed in `wiki/_Sidebar.md`; no broken links, no orphans)

## 9. Prose pass on committed pages

- [x] 9.1 Reread the ten `Guide-*.md` pages and turn bullets that carry an explanation, reason or purpose into short paragraphs, keeping numbered steps and real lists, and verify by diff that no fact was dropped (result: git show HEAD:wiki/Guide-*.md vs working copy token comparison (inline code, links, headers, fenced lines, words of 4+ letters) -> 0 missing and 0 added tokens on all 10 pages; git diff read -> only 3 pages changed, bullets to paragraphs)
- [x] 9.2 Do the same for `Widget.md`, `Gateway.md` and `Hooks.md`, and verify by diff that no fact was dropped (result: git show HEAD vs working token comparison on Widget.md, Gateway.md, Hooks.md -> 0 missing tokens beyond merged repeats "each" and "entry", 0 missing inline tokens, links or fenced lines; hand mapping of every statement -> no fact dropped)
- [x] 9.3 Do the same for the six `Backend-*.md` pages, and verify by diff that no fact was dropped (result: git show HEAD vs working token comparison on the 6 Backend-*.md pages -> 0 missing inline code, links or fenced lines, only merged-repeat words missing; hand mapping of every statement -> no fact dropped)
- [x] 9.4 Do the same for `Home.md`, `Glossary.md` and `_Sidebar.md` where it applies, and verify `check_docs.py` passes (result: git show HEAD vs working token comparison on Home.md, Glossary.md, _Sidebar.md -> 0 missing, 0 added; _Sidebar.md unchanged as it is only a link list; python api/check_docs.py -> docs check passed, exit=0)

## Workflow follow-up

- Review each group's commit separately, per the one-concern-per-commit rule.
- Archive the change once the review requirements are satisfied.
