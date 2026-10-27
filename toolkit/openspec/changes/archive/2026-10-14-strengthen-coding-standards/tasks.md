## 1. Readability (one commit)

- [x] 1.1 Add the readability principle as one line to `toolkit/rules/core-principles.md`; verify the file stays under 2048 bytes (`wc -c`) and `cd api; python check_docs.py` passes
- [x] 1.2 Add a "Readability" section to `toolkit/skills/coding-standards/SKILL.md` listing cryptic names, nested ternaries, dense one-liners needing decoding, functions doing several jobs and comments restating the code, placed with the rule-breaking findings; remove "Prefer clear code over clever code" from its "Prefer" list; verify the file stays under 4096 bytes and `python check_docs.py` passes

## 2. Contracts, correlation and logging (one commit)

- [x] 2.1 Extend the contract bullet in `toolkit/rules/architecture-boundaries.md` with the sync mechanisms (OpenAPI, shared schema, generated types) and "never change a payload shape on one side only"; verify the wording is one bullet
- [x] 2.2 Add one line to `architecture-boundaries.md` requiring a correlation ID from the client through every backend hop, present in logs on that path; verify the core pair stays under 4096 bytes
- [x] 2.3 Extend the logging line in `toolkit/rules/core-principles.md` to ask for structured (key/value or JSON) logs; verify the file stays under 2048 bytes and `python check_docs.py` passes

## 3. Dependency hygiene (one commit)

- [x] 3.1 Confirm `toolkit/rules/config-files.md` `paths:` is unchanged (`yml`, `yaml`, `json`, `toml`); add lines for committed lockfiles (merged with the existing lockfile line), no wildcard or floating versions in shared packages, and workspace dependencies declared through the workspace mechanism; verify the file stays under 3072 bytes and `python check_docs.py` passes

## 4. Docs and wrap-up

- [x] 4.1 Update `wiki/Coding-Standards.md` where it restates any changed rule, and verify `cd api; python check_docs.py` reports no problems
- [x] 4.2 Run `openspec validate strengthen-coding-standards` and verify it passes, then run `cd api; pytest` and verify the suite is green
