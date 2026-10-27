## Context

See proposal.md for motivation. The standards are layered files under `toolkit/` (spec:
`toolkit-coding-standards`). `api/check_docs.py` enforces the size budgets and `paths:` scoping.
Current sizes: `core-principles.md` 1531 B of 2048, `architecture-boundaries.md` 1014 B (the two
core rules together 2545 B of 4096), `config-files.md` 1337 B of 3072, `SKILL.md` 2333 B of 4096.
The core rules load for source-code files only; `config-files` loads for `yml`, `yaml`, `json` and
`toml`. `config-files` already says "never hand-edit generated files (lockfiles)", and
`architecture-boundaries` already says a cross-boundary contract lives in one shared or generated
definition. This change tightens those lines rather than adding parallel ones.

## Goals / Non-Goals

**Goals:**
- Readability is stated where code is generated (always-on) and checked where it is reviewed
  (blocking), so neither moment is silent.
- Each addition is one line and the budgets still pass with headroom.

**Non-Goals:**
- No new rule file, no new `paths:` globs, no change to `api/check_docs.py`.
- No tooling to enforce readability, correlation IDs or lockfiles; these remain guidance and
  review criteria.
- `requirements.txt` and `pom.xml` are not brought into `config-files` scope.

## Decisions

**Readability is a rule only for concrete smells.** The existing spec says readability-only
guidance is style. Making all of readability a rule would turn a subjective judgment into a
blocker. So the review skill's "Readability" section lists checkable smells (cryptic names, nested
ternaries, dense one-liners that need decoding, functions doing several jobs, comments that
restate the code) and reports them with rule-breaking findings; subjective judgments stay in
"Prefer". The spec requirement is modified to say so. Alternative considered: keep readability as
style and only reword it. Rejected: the user asked for it to be unconditional, and a suggestion
can be dropped from a review.

**The core principle is one line, in `core-principles`, not a new section.** Core files hold rules
only, and this fits that: "Write code to be read by a person first: descriptive names, one job per
function, no clever construct that needs decoding." Alternative: put it in `architecture-boundaries`.
Rejected: it is not about structure across layers.

**Structured logging extends the existing logging line.** `core-principles` already has the
"log at boundaries and on failure" line; add "as structured key/value or JSON, not free-form
strings" there. A second logging line would split one topic across two lines.

**Correlation IDs go in `architecture-boundaries`, not core.** They only make sense on a request
path that crosses client and backend, which is that file's subject. Putting them in `core-principles`
would load the rule for standalone scripts where it does not apply.

**Contract sync tightens the existing line.** The existing contract bullet gains the mechanisms
(OpenAPI, shared schema, generated types) and "never change a payload shape on one side only",
instead of a second bullet.

**Dependency hygiene lives in `config-files`.** It already holds the lockfile line. Because its
globs cover `json` and `toml`, it loads for `package.json`, `package-lock.json` and
`pyproject.toml`. Alternative: add `**/requirements*.txt` and `**/pom.xml` to its `paths:`.
Rejected for now: the spec lists the exact extensions and requires no extension in two rules, so
widening is its own decision.

## Risks / Trade-offs

- [Always-on cost grows on every code file] → one line per addition; projected core-principles
  about 1.9 KB and the core pair about 3.3 KB, under both limits. If a line pushes a budget, shorten
  the wording before raising a limit.
- [Readability is partly subjective, so a blocking tier can cause review churn] → only concrete
  smells block; anything judgment-based stays a suggestion.
- [Dependency rule does not load for `requirements.txt` or `pom.xml`] → accepted and recorded as a
  non-goal; the lines are worded generically so they read correctly if the scope widens later.
- [Correlation-ID rule is guidance with no enforcement] → acceptable; the toolkit ships rules, not
  middleware. A project that wants enforcement adds it itself.
