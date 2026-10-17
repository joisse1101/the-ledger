# Guidelines for a good PR

Read this while grouping commits and writing titles and bodies.

## Rule 1: Keep scope small and focused

- A PR solves one issue or implements one feature.
- Aim for under 200-400 changed lines. Large PRs are hard to review and prone to bugs. Past about
  300 lines review quality drops sharply, so split into stacked or smaller PRs.
- Never combine refactoring or formatting with new feature logic in one PR.

## Rule 2: Descriptive titles and summaries

- Title in Conventional Commits form, lowercase and imperative, no trailing period:
  `feat(auth): add oauth2 authentication flow`, `fix(cart): prevent negative item quantity on checkout`.
- Explain why the change was made. The diff already shows what changed.

## Rule 3: Self-review and verification

- Check the diff for accidental files (logs, `.env`, temp files) and debug output before opening.
- Say which tests were added or run, and whether manual testing was done.

## Rule 4: Clean commit history

- No vague commits (`fix bug`, `updates`, `wip`). Each commit is a logically complete step.
- Squash fixups and temporary commits before review.

## Hard rules

- Automated CI (formatting, lint, static analysis, type checks, tests) must pass; a PR with failing
  tests cannot merge.
- Never commit API keys, `.env` files, credentials, build artifacts or system files such as `.DS_Store`.
- One logical unit of work per PR. Refactoring and a new feature go in separate PRs.
- No direct commits to `main` or production branches: every change goes through a feature or bugfix
  branch and a PR with at least one human approval.

## Best practices

- Branch names are `type/short-description` (`feat/add-user-auth`, `fix/checkout-crash`).
- Read your own diff on the platform before asking for review: debug logging, commented-out code,
  unintended files.
- Give the reasoning behind architectural decisions in the description.
