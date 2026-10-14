---
paths:
  - "**/*.yml"
  - "**/*.yaml"
  - "**/*.json"
  - "**/*.toml"
---
# Config files

Adds config hygiene to [core-principles](core-principles.md) and
[architecture-boundaries](architecture-boundaries.md); it does not restate them.

- Never commit secrets (tokens, passwords, private keys). Reference them from the environment or a
  secret store, and commit an example file with placeholders instead.
- Validate the config against a schema when the program loads it, and fail fast naming the bad
  key. Add a new key with a safe default so existing files keep working.
- Change config additively: never rename, remove or repurpose a key without a migration path.
- Keep environment-specific values (hosts, ports, paths, credentials) in per-environment files or
  variables, not in the shared base file.
- Quote YAML values that could be misparsed (`"no"`, `"1.10"`, `"0755"`, strings with `:` or `#`).
- Never duplicate a key or copy a block between files; use anchors, includes or one shared file.
- Commit lockfiles, and never hand-edit them; regenerate them with the tool.
- Shared packages use no wildcard or floating dependency versions (`*`, `latest`).
- Declare a dependency on another package in the same workspace through the workspace mechanism,
  not by copying code or a relative path.

## Prefer

- State a key's meaning in its name or an adjacent comment (units, allowed values, default). In
  JSON, where comments are not allowed, document keys in the schema.
- Keep keys grouped consistently within a file, and one concern per file.
