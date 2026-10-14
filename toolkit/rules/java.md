---
version: 2026-10-14
paths:
  - "**/*.java"
---
# Java

Adds Java mechanics to [core-principles](core-principles.md); it does not restate them.

- Never catch `Exception` or `Throwable` broadly, and never leave a catch block empty. Catch the
  narrowest type that can be handled; otherwise wrap in a domain exception and keep the cause.
- Use unchecked exceptions for programming errors and checked ones only where callers can recover.
- Close resources with try-with-resources, never in `finally` by hand.
- Never return `null` where an empty collection or an `Optional` fits. Use `Optional` for return
  values only, never for fields or parameters.
- Validate at the boundary with `Objects.requireNonNull` or Bean Validation, and reject early.
- Make classes and fields `final` and immutable by default; use records for plain data. Never
  expose a mutable internal collection; return an unmodifiable copy.
- Inject dependencies through the constructor. Never use field injection, static mutable state or
  a service locator.
- Keep controllers thin: no business logic or persistence code in them. Domain and repository
  classes never import web-layer types (see [architecture-boundaries](architecture-boundaries.md)).
- Use parameterized queries only; never build SQL or other queries by string concatenation.
- Never compare strings or boxed values with `==`; use `equals`, and override `hashCode` with it.
- In tests, inject a clock and a random source instead of reading the system's.

## Prefer

- Name tests for the behavior (`returnsEmptyWhenNoMatch`), one behavior per test.
- `var` only where the type is obvious from the right-hand side.
