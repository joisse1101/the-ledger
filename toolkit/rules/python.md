---
version: 2026-10-14
paths:
  - "**/*.py"
---
# Python

Adds Python mechanics to [core-principles](core-principles.md); it does not restate them.

- Never use a bare `except:` or `except Exception: pass`. Catch the narrowest type, and use
  `raise ... from err` to keep the cause.
- Never use a mutable default argument (`def f(x=[])`); default to `None` and create inside.
- Use `with` for files, locks, connections and temporary state, never manual open/close.
- Annotate public function signatures. Use `dataclass` or `pydantic` models for structured data
  rather than loose dicts passed across layers.
- Validate external input (request bodies, files, environment) at the boundary into typed models
  and reject bad data there.
- Keep import-time side effects out of modules: no I/O, network or config reading at import.
- Use `pathlib.Path` for paths; never build them with string concatenation or hardcode separators.
- Use parameterized queries only; never build SQL with f-strings or `%`.
- Never use `assert` for runtime validation; it is removed under `-O`. Raise a real exception.
- Web handlers stay thin, and the data layer imports no web-framework code (see
  [architecture-boundaries](architecture-boundaries.md)).
- In tests, use pytest fixtures to isolate state (temp dirs, in-memory databases); never read or
  write the real home folder.

## Prefer

- `logging` with a module logger rather than `print`, beyond a throwaway script.
- Comprehensions over `map`/`filter` with lambdas when it reads clearer.
- `enum` over magic strings for closed sets.
