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
<!-- List the tests this PR adds or changes. Manual steps only from the OpenSpec tasks.md. -->
- [ ] Automated Unit / Integration Tests passed
- [ ] Manual testing completed (describe steps below)

**Manual Test Steps:**
1.
```

## Ticking rules

- **Type of Change**: `feat` ticks New feature; `fix` ticks Bug fix; `refactor`, `perf` and `style`
  tick Refactoring; `docs` ticks Documentation; `test` ticks Tests. A `chore` group touching only docs
  or specs ticks Documentation, otherwise nothing. Tick Breaking change when any commit subject has
  `!` after the type or any commit body has a `BREAKING CHANGE` footer. Several boxes may be ticked.
- **Automated**: tick when the group adds or changes a test file, and list those files and the test
  names under the box. The user has said to assume the tests were run.
- **Manual**: tick only when the matching OpenSpec `tasks.md` records a manual step or result for this
  group, and copy it into Manual Test Steps. Otherwise leave it unticked and delete the steps list.
- No visual-proof section. Do not add one.
