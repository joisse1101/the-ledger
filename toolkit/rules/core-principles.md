# Core principles

Language-agnostic. These apply to all code; technology rules add mechanics, not new principles.

- KISS, DRY, YAGNI: build the simplest thing that works; do not add features, options or
  abstractions before a second real use needs them; extract repeated logic once it is real.
- Single responsibility and layer isolation: one responsibility per unit. Business logic never knows about HTTP, database drivers or UI.
- Keep pure logic apart from I/O so it can be tested directly.
- Fail fast at boundaries: validate input where it enters and reject bad data with a clear error.
- Never swallow an error. Handle a failure at the layer that can act on it; otherwise let it
  propagate with context. No empty catch blocks, no silent defaults that hide a failure.
- Operations are idempotent: running one twice leaves the same result as once.
- Behavior is deterministic. No hidden global state, and tests never touch real user state
  (real home folders, databases, credentials).
- Configuration is data. Never hardcode environment values (hosts, paths, ports, keys).
- Evolve schemas and APIs additively and backward-compatibly. Never remove or repurpose a field
  without a migration path.
- Log at boundaries and on failure, with enough context to diagnose. Never log secrets or
  personal data.
- Run the project's build and type-check before calling a change done.
