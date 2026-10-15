---
metadata:
  version: "1.0.0"
  last_updated: "2026-10-14"
paths:
  - "**/*.py"
  - "**/*.java"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.ps1"
  - "**/*.sh"
  - "**/*.bat"
---
# Architecture boundaries

Structure across frontend, backend and shared code. Applies to code in every project.

- A backend module never imports frontend code, and a frontend module never imports backend code.
  Share through a shared package or generated definitions.
- A data or domain layer never imports web-framework code (request/response types, routers,
  middleware). Frameworks depend on it, not the reverse.
- A contract that crosses a boundary (for example client types mirroring server JSON) lives in
  one shared or generated definition (OpenAPI, a shared schema, generated types). Change both
  sides together; never change a payload shape on one side only.
- A request carries a correlation ID from the client through every backend hop, and logs on that
  path include it.
- Enforce authorization on the server. Hiding a control in the UI is not security.
- Validate configuration files against a schema at startup and fail fast on a mismatch. Keep
  environment-specific values and secrets out of code and out of committed config.
