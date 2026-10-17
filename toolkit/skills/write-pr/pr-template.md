# PR body template

Fill every section below, then delete the `<!-- -->` comments before opening the PR. Keep the
emoji headings exactly as written.

```markdown
## 📌 Summary
<!-- What this PR does and why it is needed. Lead with the why; the diff already shows the what. -->

## 🔗 Related Issues / Tickets
<!-- OMIT THIS WHOLE SECTION unless a commit message or the branch name references an issue or ticket
     (Closes #123, Fixes PROJ-456). Never invent one. -->

## 🛠 Type of Change
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 💥 Breaking change (fix or feature causing existing functionality to fail)
- [ ] ♻️ Refactoring / Technical Debt (no logical/functional changes)
- [ ] 📚 Documentation / Comments
- [ ] 🧪 Tests (adding missing or updated tests)

## 📝 Changes Made
<!-- One bullet per commit in this PR: the commit subject, copied from `git log`. -->
-

## 🧪 How Has This Been Tested?
<!-- List the tests this PR adds or changes under the first box. -->
- [ ] Automated Unit / Integration Tests passed
- [ ] Manual testing completed

### Author Verification
<!-- What the author ran and saw, one bullet per check. Never state a result no source records. -->
- **Label:** command or input, then the observed result

### How to Test This PR
<!-- Steps for a reviewer, numbered, each command in a fenced block. See verification.md. -->
1. Fetch and check out this branch.
```

## Ticking rules

- **Type of Change**: `feat` ticks New feature; `fix` ticks Bug fix; `refactor`, `perf` and `style`
  tick Refactoring; `docs` ticks Documentation; `test` ticks Tests. A `chore` group touching only docs
  or specs ticks Documentation, otherwise nothing. Tick Breaking change when any commit subject has
  `!` after the type or any commit body has a `BREAKING CHANGE` footer. Several boxes may be ticked.
- **Automated**: tick when the group adds or changes a test file, and list those files and the test
  names under the box. The user has said to assume the tests were run.
- **Author Verification**: bullets come from the matching OpenSpec `tasks.md` and, where it has none,
  from the user's answer; `verification.md` says how. A bullet reports no result its source lacks.
  Quote a count only when a source records it. With no bullets, write `- None recorded.`
- **Manual**: tick only when at least one Author Verification bullet is a manual check: a command run
  or behavior observed by hand, not the repository's test command. Otherwise leave it unticked.
- **How to Test This PR**: steps follow `verification.md`. Delete the subsection if none survive.
- No visual-proof section. Do not add one.
