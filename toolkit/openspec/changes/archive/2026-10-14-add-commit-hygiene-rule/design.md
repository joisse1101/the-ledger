## Context

The commit gate in `toolkit/commands/opsx/apply.md` (step 6, "Pending Commits") and
`archive.md` (step 7) controls only *when* a commit happens. See proposal.md - Why. The toolkit has
two delivery mechanisms: description-routed skills, which Claude may skip, and rules, which load on
their own. The last toolkit change (`3322b7e`) scoped every rule to source-code file types so
sessions that never touch code do not pay for them. `toolkit/README.md` states "Every rule here is
scoped". A path-scoped rule loads only after a matching file is read or edited, which is the wrong
trigger for commits.

## Goals / Non-Goals

**Goals:**
- Keep commits small enough to review, in sessions that edit code, generate assets, clean up files
  or edit only docs.
- Cost little context, and nothing when no commit is made.

**Non-Goals:**
- A `/commit` command or skill that splits an already-large working tree. Possible follow-up.
- Enforcing the rule mechanically with a git hook or the docs check. This is guidance to Claude.
- Changing the approval stop in apply and archive.

## Decisions

**Rule, not skill.** A skill fires only when its description matches, so the failure being fixed
(Claude batching work) could recur whenever it is not loaded. A rule is present when Claude decides
what to stage. *Alternative:* skill only (cheaper, skippable); rule plus a split-commits skill
(deferred as a follow-up).

**Unscoped, not code-scoped.** Commit discipline attaches to the act of committing, not to file
types. A code-scoped rule would be absent for a generated PNG, a file cleanup or a docs-only
session, which are exactly the commits that grow unnoticed. The cost is a small always-loaded
rule, capped at 2 KB. This is a deliberate exception to the "every rule is scoped" line in the
README, which is reworded. *Alternative:* extend `paths:` to cover `png`, `md` and so on; rejected
because deletes and renames have no matching extension and the list would never be complete.

**Phrased as "when about to commit".** Outside a git repository, or in a session that never
commits, the rule asks for nothing. Installation scope decides which repositories see it: global
install covers all of them, `-Scope project` limits it.

**Count concerns, not files.** A flat file limit blocks legitimate bulk commits (a 40-file
deletion) while letting a 4-file tangle through. Deletions, renames, regenerated or binary assets,
lockfiles and mechanical format-only changes are each one concern. A hand-written change over about
200 lines or 5 files, or across more than one layer, is split. The numbers are triggers for judgment
and are approximate on purpose.

**Docs, specs and tests ride with their change.** The repo requires wiki updates in the same PR as a
behavior change (root `CLAUDE.md`). Putting them in a trailing commit would recreate a catch-all
commit, so the rule keeps them with the change they describe.

**Non-interactive partial staging.** Interactive git (`git add -p`) is not supported in the Claude
Code shell. The rule asks for explicit paths and, when a file mixes concerns, a non-interactive
method such as applying a prepared patch to the index, or splitting the edit.

**Spec lands in `toolkit-coding-standards`.** It already owns the rules layer. No new capability
is created, and the existing "Core floor is code-scoped" requirement stays true because it names
the two core rules specifically.

**Message format follows the repo, not generic Conventional Commits advice.** History uses
lowercase subjects (`feat: scope code rules to just code`), so the rule says lowercase.

**Claude never commits unprompted; a typed word or a question answer confirms.** Existing apply
and archive already stop before committing, but a session outside them has no such rule, and a plain
"yes" is easy to over-read ("looks good", "yes that works"). A word the user must
type is unambiguous, cannot be satisfied by a tool result, and takes one short reply. AskUserQuestion
stays as the alternative because it is already used by `opsx:archive` and gives a click. The word is
a deliberateness gate, not a secret, so Claude states it in each prompt. The word is never the same
as in the previous prompt: a constant word becomes a reflex typed without reading the diff, and a
stale word from an earlier prompt must not confirm a later commit, so only the most recent prompt's
word counts. Claude picks any common word; no list is kept in the rule, which saves context but
leaves variety to Claude. After `/clear` or compaction the previous word is unknown and any word is
fine. Confirmation is per commit.
*Alternatives:* plain "yes" (ambiguous); a fixed word (becomes a reflex); a word list in the rule (more bytes,
better variety, rejected for now). A direct "commit this" still stages first, so the gate has no bypass.

## Risks / Trade-offs

- [Always-loaded rule adds context in every session] -> Capped at 2 KB and phrased as inert
  without a commit.
- [Approximate thresholds are argued around by Claude] -> The one-concern rule is primary; the
  numbers are only a tripwire to split earlier.
- [Splitting every concern slows `opsx:apply`, with more approval stops] -> Intended: the user
  reviews smaller diffs. Revisit the thresholds if the stops become noise.
- [Claude reuses the same few words, or forgets the previous one] -> Accepted; the rule only needs
  consecutive prompts to differ, and a missed check costs a repeated word, not a wrong commit.
- [Rule is not enforced by tooling] -> Accepted for now; a hook or `/commit` command is a possible
  follow-up if the rule is ignored in practice.
- [Existing installs show `differs` for the edited commands] -> Existing installer behavior; the
  user passes `-Force` to update.
